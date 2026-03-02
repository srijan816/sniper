"""Client API routes (Supabase-backed)."""
from datetime import datetime
import os
import re
import uuid
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile, Depends

from app.core.config import get_settings
from app.core.database import get_supabase_client
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
    allowed = {"company_name", "legal_contact_name", "legal_contact_email", "whitelist_domains"}
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
            public_url = storage.get_public_url(path)
            if isinstance(public_url, dict):
                loa_document_url = public_url.get("publicUrl") or public_url.get("public_url") or path
            else:
                loa_document_url = str(public_url)
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
    """Get expanded analytics for a client — real data only."""
    from datetime import datetime, timezone
    from collections import defaultdict

    try:
        db = _db()
        client_res = db.table("clients").select("*").eq("id", client_id).limit(1).execute()
        if not (client_res.data or []):
            raise HTTPException(status_code=404, detail="Client not found")
        client = client_res.data[0]
        aov = float(client.get("average_product_price") or 120.0)

        # Threats
        threats_res = db.table("threats").select("id,status,discovered_at,asset_id").eq("client_id", client_id).execute()
        threats = threats_res.data or []

        now = datetime.now(timezone.utc)
        current_month = now.month
        current_year = now.year

        def _in_month(ts_str: str | None) -> bool:
            if not ts_str:
                return False
            try:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                return dt.month == current_month and dt.year == current_year
            except Exception:
                return False

        removed_statuses = {"REMOVED", "TAKEDOWN_CONFIRMED"}
        found_total = len(threats)
        found_month = sum(1 for t in threats if _in_month(t.get("discovered_at")))
        removed_total = sum(1 for t in threats if (t.get("status") or "") in removed_statuses)
        removed_month = sum(1 for t in threats if (t.get("status") or "") in removed_statuses and _in_month(t.get("discovered_at")))

        # Takedowns for timing
        try:
            td_res = db.table("takedown_requests").select("status,completed_at,platform").execute()
            takedowns = td_res.data or []
        except Exception:
            try:
                td_res = db.table("takedowns").select("status,completed_at,platform").execute()
                takedowns = td_res.data or []
            except Exception:
                takedowns = []

        td_completed = [td for td in takedowns if td.get("status") in {"CONFIRMED", "SUBMITTED", "COMPLETED"}]
        td_month = [td for td in td_completed if _in_month(td.get("completed_at"))]

        # Average time to takedown (hours)
        avg_time = None
        # (simplified - would need created_at too for full calculation)

        # Platforms breakdown
        platforms: dict = defaultdict(lambda: {"threats": 0, "takedowns": 0})
        for td in takedowns:
            p = (td.get("platform") or "other").lower()
            platforms[p]["takedowns"] += 1

        # Monthly trend (last 6 months)
        monthly_trend = []
        for i in range(5, -1, -1):
            m = (now.month - i - 1) % 12 + 1
            y = now.year if (now.month - i) > 0 else now.year - 1
            label = datetime(y, m, 1).strftime("%b")
            t_count = sum(1 for t in threats if _in_month_year(t.get("discovered_at"), m, y))
            r_count = sum(1 for t in threats if (t.get("status") or "") in removed_statuses and _in_month_year(t.get("discovered_at"), m, y))
            monthly_trend.append({"month": label, "found": t_count, "removed": r_count})

        # Bad actors
        try:
            ba_res = db.table("bad_actor_signals").select("id").execute()
            bad_actors = len(ba_res.data or [])
        except Exception:
            bad_actors = 0

        rev_protected = removed_total * aov

        return ClientAnalytics(
            threats_found_this_month=found_month,
            threats_removed_this_month=removed_month,
            estimated_revenue_protected=rev_protected,
            average_order_value=aov,
            threats_discovered_total=found_total,
            takedowns_completed_total=len(td_completed),
            takedowns_completed_this_month=len(td_month),
            average_time_to_takedown_hours=avg_time,
            bad_actors_identified=bad_actors,
            platforms_breakdown=dict(platforms),
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
        patch["slack_webhook_url"] = data.slack_webhook_url or None
    if data.webhook_url is not None:
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
