"""Client API routes (Supabase-backed)."""
from datetime import datetime
import os
import re
import uuid
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile, Depends

from app.core.config import get_settings
from app.core.database import get_supabase_client
from app.models.schemas import ClientAnalytics, ClientCreate, ClientResponse
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
    """Get lightweight analytics for a client from real tables."""
    try:
        db = _db()
        client_res = db.table("clients").select("id").eq("id", client_id).limit(1).execute()
        if not (client_res.data or []):
            raise HTTPException(status_code=404, detail="Client not found")

        assets_res = db.table("assets").select("id").eq("client_id", client_id).execute()
        asset_ids = [row["id"] for row in (assets_res.data or []) if row.get("id")]
        if not asset_ids:
            return ClientAnalytics(
                threats_found_this_month=0,
                threats_removed_this_month=0,
                estimated_revenue_protected=0.0,
                average_order_value=120.0,
            )

        threats_res = db.table("threats").select("status").in_("asset_id", asset_ids).execute()
        threats = threats_res.data or []
        found = len(threats)
        removed = len([t for t in threats if t.get("status") in {"REMOVED", "TAKEDOWN_CONFIRMED"}])
        aov = 120.0

        return ClientAnalytics(
            threats_found_this_month=found,
            threats_removed_this_month=removed,
            estimated_revenue_protected=removed * aov,
            average_order_value=aov,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {exc}") from exc
