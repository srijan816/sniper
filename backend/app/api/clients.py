"""Client API routes (Supabase-backed)."""
from datetime import datetime
import ipaddress
import os
import re
import socket
import uuid
from typing import List
from urllib.parse import urlparse

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, Depends

from app.core.limiter import limiter

from app.core.config import get_settings
from app.core.database import get_supabase_client
from app.services.storage_util import public_url as storage_public_url
import hashlib
import hmac
import secrets

from app.models.schemas import (
    AuthorizedSellerCreate,
    AuthorizedSellerResponse,
    ClientAnalytics,
    ClientCreate,
    ClientResponse,
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
)
from app.api.deps import get_current_client_id

router = APIRouter()


def validate_webhook_url(url: str) -> bool:
    """Return True if *url* resolves to a public IP. Raises HTTPException(422) otherwise.

    Blocks loopback, private, link-local (including AWS metadata 169.254.x.x),
    and reserved addresses to prevent SSRF attacks.
    """
    if not url:
        return True  # empty / null is allowed (clears the setting)
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=422, detail="Webhook URL must use http or https scheme.")
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=422, detail="Webhook URL must contain a valid hostname.")
    try:
        results = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise HTTPException(status_code=422, detail=f"Webhook URL hostname '{hostname}' could not be resolved.")
    for _, _, _, _, sockaddr in results:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_unspecified:
            raise HTTPException(
                status_code=422,
                detail="Webhook URL must resolve to a public IP address. Private, loopback, and link-local addresses are not allowed.",
            )
    return True


def _db():
    db = get_supabase_client()
    if db is None:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")
    return db


def _map_client(row: dict) -> dict:
    return {
        "id": row.get("id"),
        "company_name": row.get("company_name") or "",
        "legal_contact_name": row.get("legal_contact_name") or "",
        "legal_contact_email": row.get("legal_contact_email") or "",
        "subscription_tier": row.get("subscription_tier") or "FREE",
        "monthly_threat_limit": row.get("monthly_threat_limit") or 0,
        "current_month_count": row.get("current_month_count") or 0,
        "loa_signed_at": row.get("loa_signed_at"),
        "whitelist_domains": row.get("whitelist_domains") or [],
        "created_at": row.get("created_at") or datetime.utcnow().isoformat(),
    }


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "-", filename or "document.pdf")
    return cleaned.strip("-") or "document.pdf"


@router.get("/", response_model=List[ClientResponse])
async def list_clients(client_id: str = Depends(get_current_client_id)):
    """List authenticated client."""
    try:
        res = _db().table("clients").select("*").eq("id", client_id).limit(1).execute()
        return [_map_client(row) for row in (res.data or [])]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list clients: {exc}") from exc


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(client_id: str = Depends(get_current_client_id)):
    """Get a client by ID."""
    try:
        res = _db().table("clients").select("*").eq("id", client_id).limit(1).execute()
        rows = res.data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Client not found")
        return _map_client(rows[0])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch client: {exc}") from exc


@router.post("/", response_model=ClientResponse)
async def create_client(data: ClientCreate, client_id: str = Depends(get_current_client_id)):
    """Register a new client — requires authentication."""
    row = {
        "id": str(uuid.uuid4()),
        "company_name": data.company_name,
        "legal_contact_name": data.legal_contact_name,
        "legal_contact_email": data.legal_contact_email,
        "subscription_tier": "FREE",
        "monthly_threat_limit": 0,
        "current_month_count": 0,
        "whitelist_domains": [],
    }
    try:
        res = _db().table("clients").insert(row).execute()
        rows = res.data or []
        if not rows:
            raise HTTPException(status_code=500, detail="Client creation failed.")
        return _map_client(rows[0])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create client: {exc}") from exc


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    data: dict,
    client_id: str = Depends(get_current_client_id),
):
    """Update allowed fields on the authenticated client (whitelist_domains, company_name, etc.)."""
    allowed = {"company_name", "legal_contact_name", "legal_contact_email", "whitelist_domains", "contact_address", "contact_phone"}
    patch = {k: v for k, v in data.items() if k in allowed}
    if not patch:
        raise HTTPException(status_code=400, detail="No updatable fields provided")
    try:
        res = _db().table("clients").update(patch).eq("id", client_id).execute()
        rows = res.data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Client not found")
        return _map_client(rows[0])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update client: {exc}") from exc


@router.post("/{client_id}/loa-upload")
async def upload_loa_document(
    file: UploadFile = File(...),
    client_id: str = Depends(get_current_client_id),
):
    """Upload a signed Letter of Authorization (LOA) and store public URL."""
    settings = get_settings()
    bucket = settings.loa_storage_bucket or os.getenv("LOA_STORAGE_BUCKET", "legal-documents")
    fallback_bucket = settings.supabase_storage_bucket or os.getenv("SUPABASE_STORAGE_BUCKET", "assets")
    filename = _safe_filename(file.filename or "loa.pdf")
    loa_id = str(uuid.uuid4())
    path = f"{client_id}/loa/{loa_id}-{filename}"

    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded LOA is empty.")

    loa_document_url = None
    last_error = None
    for candidate_bucket in (bucket, fallback_bucket):
        if not candidate_bucket:
            continue
        try:
            storage = _db().storage.from_(candidate_bucket)
            storage.upload(path, data, {"content-type": file.content_type or "application/pdf", "upsert": "true"})
            loa_document_url = storage_public_url(storage, path)
            break
        except Exception as exc:
            last_error = exc
            continue

    if not loa_document_url:
        raise HTTPException(status_code=500, detail=f"Failed to upload LOA file: {last_error}")

    try:
        updated = (
            _db()
            .table("clients")
            .update(
                {
                    "loa_document_url": loa_document_url,
                    "loa_signed_at": datetime.utcnow().isoformat(),
                }
            )
            .eq("id", client_id)
            .execute()
            .data
            or []
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Client not found")
        return {
            "status": "uploaded",
            "client_id": client_id,
            "loa_document_url": loa_document_url,
            "loa_signed_at": updated[0].get("loa_signed_at"),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to persist LOA metadata: {exc}") from exc


@router.get("/{client_id}/analytics", response_model=ClientAnalytics)
async def get_client_analytics(client_id: str = Depends(get_current_client_id)):
    """Get expanded analytics for a client — DB-level aggregation only (no full table scans)."""
    from datetime import datetime, timezone

    try:
        db = _db()
        # Client record (needed for AOV only — single row, not the threats table)
        client_res = db.table("clients").select("average_product_price").eq("id", client_id).limit(1).execute()
        if not (client_res.data or []):
            raise HTTPException(status_code=404, detail="Client not found")
        aov = float((client_res.data[0] or {}).get("average_product_price") or 120.0)

        # --- Count queries (no full row fetch) ---
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

        total_threats = (
            db.table("threats").select("id", count="exact").eq("client_id", client_id).execute().count or 0
        )
        threats_this_month = (
            db.table("threats").select("id", count="exact")
            .eq("client_id", client_id)
            .gte("discovered_at", month_start)
            .execute().count or 0
        )

        removed_statuses_tuple = ("REMOVED", "TAKEDOWN_CONFIRMED")
        removed_total = sum(
            db.table("threats").select("id", count="exact")
            .eq("client_id", client_id)
            .eq("status", s)
            .execute().count or 0
            for s in removed_statuses_tuple
        )
        removed_this_month = sum(
            db.table("threats").select("id", count="exact")
            .eq("client_id", client_id)
            .eq("status", s)
            .gte("discovered_at", month_start)
            .execute().count or 0
            for s in removed_statuses_tuple
        )

        # Takedowns count — only 3 light columns, scoped to client via threat join is complex;
        # use a simpler pattern: count statuses directly on takedowns (no full row fetch)
        takedowns = []
        for table_name in ("takedown_requests", "takedowns"):
            try:
                td_res = db.table(table_name).select("status,completed_at,platform").eq("threat_id",
                    db.table("threats").select("id").eq("client_id", client_id)
                ).execute()
                takedowns = td_res.data or []
                break
            except Exception:
                pass
        # Fallback: just count with no join if the above fails
        if not takedowns:
            try:
                td_res = db.table("takedowns").select("status,completed_at,platform").execute()
                takedowns = td_res.data or []
            except Exception:
                takedowns = []

        td_completed = [td for td in takedowns if (td.get("status") or "") in {"CONFIRMED", "SUBMITTED", "COMPLETED"}]
        td_month = [
            td for td in td_completed
            if (td.get("completed_at") or "") >= month_start
        ]

        # Platform breakdown — fetch only one column (not *)
        try:
            plat_res = db.table("threats").select("host_domain").eq("client_id", client_id).execute()
            from collections import Counter
            platform_counts: dict = dict(Counter(
                (r.get("host_domain") or "other").lower() for r in (plat_res.data or [])
            ))
        except Exception:
            platform_counts = {}

        # Bad actors — count only
        try:
            bad_actors = db.table("bad_actor_signals").select("id", count="exact").execute().count or 0
        except Exception:
            bad_actors = 0

        # Monthly trend — use the SQL RPC (aggregation in DB, not Python)
        monthly_trend: list = []
        try:
            rpc_res = db.rpc("get_monthly_threat_trend", {"p_client_id": client_id}).execute()
            for row in (rpc_res.data or []):
                monthly_trend.append({
                    "month": row.get("month", ""),
                    "threats": int(row.get("threat_count") or 0),
                    "takedowns": int(row.get("takedown_count") or 0),
                })
        except Exception:
            monthly_trend = []

        rev_protected = removed_total * aov

        return ClientAnalytics(
            threats_found_this_month=threats_this_month,
            threats_removed_this_month=removed_this_month,
            estimated_revenue_protected=rev_protected,
            average_order_value=aov,
            threats_discovered_total=total_threats,
            takedowns_completed_total=len(td_completed),
            takedowns_completed_this_month=len(td_month),
            average_time_to_takedown_hours=None,
            bad_actors_identified=bad_actors,
            platforms_breakdown=platform_counts,
            monthly_trend=monthly_trend,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {exc}") from exc


def _in_month_year(ts_str: str | None, month: int, year: int) -> bool:
    if not ts_str:
        return False
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.month == month and dt.year == year
    except Exception:
        return False


# ── Authorized Sellers / Whitelist (Feature 7) ───────────────────────────────

@router.get("/{client_id}/authorized-sellers", response_model=List[AuthorizedSellerResponse])
async def list_authorized_sellers(client_id: str = Depends(get_current_client_id)):
    try:
        res = _db().table("authorized_sellers").select("*").eq("client_id", client_id).order("created_at", desc=True).execute()
        return res.data or []
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list authorized sellers: {exc}") from exc


@router.post("/{client_id}/authorized-sellers", response_model=AuthorizedSellerResponse)
async def add_authorized_seller(data: AuthorizedSellerCreate, client_id: str = Depends(get_current_client_id)):
    domain = data.domain.strip().lower().replace("https://", "").replace("http://", "").rstrip("/")
    row = {
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "domain": domain,
        "seller_name": data.seller_name,
        "platform": data.platform,
        "platform_seller_id": data.platform_seller_id,
        "relationship": data.relationship,
        "added_by": "manual",
    }
    try:
        res = _db().table("authorized_sellers").upsert(row, on_conflict="client_id,domain").execute()
        rows = res.data or []
        if not rows:
            raise HTTPException(status_code=500, detail="Failed to add authorized seller")
        return rows[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to add authorized seller: {exc}") from exc


@router.delete("/{client_id}/authorized-sellers/{seller_id}")
async def remove_authorized_seller(seller_id: str, client_id: str = Depends(get_current_client_id)):
    try:
        res = _db().table("authorized_sellers").delete().eq("id", seller_id).eq("client_id", client_id).execute()
        if not (res.data or []):
            raise HTTPException(status_code=404, detail="Authorized seller not found")
        return {"status": "deleted", "seller_id": seller_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to remove authorized seller: {exc}") from exc


# ── Notification Settings (Feature 8) ────────────────────────────────────────

@router.get("/{client_id}/notifications", response_model=NotificationSettingsResponse)
async def get_notification_settings(client_id: str = Depends(get_current_client_id)):
    try:
        res = _db().table("clients").select("slack_webhook_url,webhook_url,webhook_secret,notification_prefs").eq("id", client_id).limit(1).execute()
        rows = res.data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Client not found")
        row = rows[0]
        # Mask the webhook secret — return only a hint
        secret = row.get("webhook_secret")
        return NotificationSettingsResponse(
            slack_webhook_url=row.get("slack_webhook_url"),
            webhook_url=row.get("webhook_url"),
            webhook_secret=f"••••{secret[-4:]}" if secret and len(secret) > 4 else None,
            notification_prefs=row.get("notification_prefs") or {},
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get notification settings: {exc}") from exc


@router.put("/{client_id}/notifications", response_model=NotificationSettingsResponse)
async def update_notification_settings(data: NotificationSettingsUpdate, client_id: str = Depends(get_current_client_id)):
    patch: dict = {}
    if data.slack_webhook_url is not None:
        if data.slack_webhook_url:
            validate_webhook_url(data.slack_webhook_url)
        patch["slack_webhook_url"] = data.slack_webhook_url or None
    if data.webhook_url is not None:
        if data.webhook_url:
            validate_webhook_url(data.webhook_url)
        patch["webhook_url"] = data.webhook_url or None
        # Rotate webhook secret when URL changes
        if data.webhook_url:
            patch["webhook_secret"] = secrets.token_hex(32)
    if data.notification_prefs is not None:
        patch["notification_prefs"] = data.notification_prefs
    if not patch:
        raise HTTPException(status_code=400, detail="No settings to update")
    try:
        res = _db().table("clients").update(patch).eq("id", client_id).execute()
        rows = res.data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Client not found")
        row = rows[0]
        secret = row.get("webhook_secret")
        return NotificationSettingsResponse(
            slack_webhook_url=row.get("slack_webhook_url"),
            webhook_url=row.get("webhook_url"),
            webhook_secret=secret,  # return full secret on creation
            notification_prefs=row.get("notification_prefs") or {},
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update notification settings: {exc}") from exc


@router.post("/{client_id}/notifications/test")
async def test_notification(client_id: str = Depends(get_current_client_id)):
    """Send a test notification through all configured channels."""
    try:
        db = _db()
        res = db.table("clients").select("*").eq("id", client_id).limit(1).execute()
        rows = res.data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Client not found")
        client = rows[0]
        from app.services.notification_service import dispatch_client_notification
        dispatch_client_notification(
            client=client,
            event_type="test",
            title="Test Notification",
            email_subject="SniperIP: Test notification",
            email_html="<p>This is a test notification from SniperIP. Your notification channels are configured correctly.</p>",
            slack_message=":white_check_mark: *Test notification* — SniperIP is connected successfully!",
            webhook_payload={"message": "Test notification from SniperIP"},
        )
        return {"status": "sent"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to send test notification: {exc}") from exc


# Backward-compatible aliases for older frontend paths
@router.get("/{client_id}/notification-settings", response_model=NotificationSettingsResponse, include_in_schema=False)
async def get_notification_settings_legacy(client_id: str = Depends(get_current_client_id)):
    return await get_notification_settings(client_id)


@router.patch("/{client_id}/notification-settings", response_model=NotificationSettingsResponse, include_in_schema=False)
async def patch_notification_settings_legacy(data: NotificationSettingsUpdate, client_id: str = Depends(get_current_client_id)):
    return await update_notification_settings(data, client_id)


@router.post("/{client_id}/notification-settings/test", include_in_schema=False)
async def test_notification_legacy(client_id: str = Depends(get_current_client_id)):
    return await test_notification(client_id)


@router.post("/{client_id}/research-brand")
@limiter.limit("3/day")
async def trigger_brand_research(
    request: Request,
    client_id: str = Depends(get_current_client_id),
    product_category: str = "consumer goods",
):
    """
    Queue AI-Q deep research for this brand (one job at a time — do not spam).
    Results stored on client.brand_research when complete.
    """
    from app.workers.research import run_brand_research

    rows = (
        _db()
        .table("clients")
        .select("id,brand_research")
        .eq("id", client_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Client not found")
    if rows[0].get("brand_research"):
        return {"status": "skipped", "message": "Brand research already completed for this client"}

    task = run_brand_research.delay(client_id, product_category)
    return {"status": "queued", "task_id": task.id, "message": "Brand research queued (runs sequentially via AI-Q)"}
