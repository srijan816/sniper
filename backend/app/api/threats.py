"""Threat management API routes (Supabase-backed)."""
from datetime import datetime
from typing import List, Optional
import uuid

from fastapi import APIRouter, HTTPException, Query, Depends

from app.core.database import get_supabase_client
from app.models.schemas import AuditLogResponse, ThreatResponse
from app.workers.takedown import queue_takedown
from app.api.deps import get_current_client_id

router = APIRouter()


def _db():
    db = get_supabase_client()
    if db is None:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")
    return db


def _fetch_asset_client_map(asset_ids: List[str]) -> dict:
    if not asset_ids:
        return {}
    res = _db().table("assets").select("id,client_id").in_("id", asset_ids).execute()
    return {row["id"]: row.get("client_id") for row in (res.data or [])}


def _map_threat(row: dict, client_id: Optional[str]) -> dict:
    return {
        "id": row.get("id"),
        "asset_id": row.get("asset_id"),
        "client_id": client_id or "unknown-client",
        "infringing_url": row.get("infringing_url") or "",
        "infringing_image_url": row.get("infringing_image_url"),
        "host_domain": row.get("host_domain") or "",
        "seller_name": row.get("seller_name"),
        "listing_title": row.get("listing_title"),
        "listing_price": row.get("listing_price"),
        "similarity_score": row.get("similarity_score") or 0.0,
        "ai_explanation": row.get("ai_explanation"),
        "status": row.get("status") or "DISCOVERED",
        "discovered_at": row.get("discovered_at") or datetime.utcnow().isoformat(),
        "resolved_at": row.get("resolved_at"),
    }


def _map_audit(row: dict) -> dict:
    return {
        "id": row.get("id"),
        "threat_id": row.get("threat_id"),
        "old_status": row.get("old_status"),
        "new_status": row.get("new_status"),
        "changed_by": row.get("changed_by") or "SYSTEM",
        "metadata": {},
        "changed_at": row.get("changed_at") or datetime.utcnow().isoformat(),
    }


def _write_audit_log(threat_id: str, old_status: Optional[str], new_status: str, changed_by: str):
    _db().table("audit_logs").insert(
        {
            "threat_id": threat_id,
            "old_status": old_status,
            "new_status": new_status,
            "changed_by": changed_by,
        }
    ).execute()


def _table_missing(exc: Exception) -> bool:
    message = str(exc)
    return "PGRST205" in message or "Could not find the table" in message


def _with_takedown_table(fn):
    last_error = None
    for table_name in ("takedown_requests", "takedowns"):
        try:
            return fn(table_name)
        except Exception as exc:
            if _table_missing(exc):
                last_error = exc
                continue
            raise
    raise HTTPException(status_code=500, detail=f"Takedown table not found: {last_error}")


def _derive_platform(host_domain: str) -> str:
    domain = (host_domain or "").lower()
    if any(name in domain for name in ("instagram.com", "facebook.com", "meta.com")):
        return "meta"
    if "amazon." in domain:
        return "amazon"
    return "shopify"


@router.get("/", response_model=List[ThreatResponse])
async def list_threats(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    client_id: str = Depends(get_current_client_id),
):
    """List threats with optional filtering."""
    try:
        db = _db()
        asset_filter = None
        if client_id:
            assets_res = db.table("assets").select("id").eq("client_id", client_id).execute()
            asset_filter = [row["id"] for row in (assets_res.data or []) if row.get("id")]
            if not asset_filter:
                return []

        query = db.table("threats").select("*").order("discovered_at", desc=True)
        if status:
            query = query.eq("status", status)
        if asset_filter is not None:
            query = query.in_("asset_id", asset_filter)
        query = query.range(offset, offset + limit - 1)

        threats_res = query.execute()
        rows = threats_res.data or []
        asset_ids = [row.get("asset_id") for row in rows if row.get("asset_id")]
        asset_map = _fetch_asset_client_map(asset_ids)
        return [_map_threat(row, asset_map.get(row.get("asset_id"))) for row in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list threats: {exc}") from exc


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def list_audit_logs(
    threat_id: Optional[str] = None,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    client_id: str = Depends(get_current_client_id),
):
    try:
        query = _db().table("audit_logs").select("*").order("changed_at", desc=True).range(offset, offset + limit - 1)
        if threat_id:
            query = query.eq("threat_id", threat_id)
        res = query.execute()
        return [_map_audit(row) for row in (res.data or [])]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list audit logs: {exc}") from exc


@router.get("/{threat_id}", response_model=ThreatResponse)
async def get_threat(threat_id: str, client_id: str = Depends(get_current_client_id)):
    try:
        db = _db()
        res = db.table("threats").select("*").eq("id", threat_id).limit(1).execute()
        rows = res.data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Threat not found")
        threat = rows[0]
        asset_map = _fetch_asset_client_map([threat.get("asset_id")] if threat.get("asset_id") else [])
        return _map_threat(threat, asset_map.get(threat.get("asset_id")))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch threat: {exc}") from exc


@router.post("/{threat_id}/approve", response_model=ThreatResponse)
async def approve_threat(threat_id: str, client_id: str = Depends(get_current_client_id)):
    """Client approves a threat for takedown — AUDIT LOGGED."""
    try:
        db = _db()
        existing = db.table("threats").select("*").eq("id", threat_id).limit(1).execute().data or []
        if not existing:
            raise HTTPException(status_code=404, detail="Threat not found")
        threat = existing[0]
        old_status = threat.get("status")
        if old_status not in {"DISCOVERED", "PENDING_APPROVAL"}:
            raise HTTPException(status_code=400, detail=f"Cannot approve threat in status {old_status}")

        updated = db.table("threats").update({"status": "APPROVED"}).eq("id", threat_id).execute().data or []
        _write_audit_log(threat_id, old_status, "APPROVED", "CLIENT_USER")

        takedown_id = str(uuid.uuid4())
        takedown_row = {
            "id": takedown_id,
            "threat_id": threat_id,
            "platform": _derive_platform(threat.get("host_domain") or ""),
            "status": "PENDING",
            "retry_count": 0,
            "submitted_at": None,
        }
        _with_takedown_table(lambda table: db.table(table).insert(takedown_row).execute())
        queue_takedown(takedown_id)

        row = updated[0] if updated else threat
        asset_map = _fetch_asset_client_map([row.get("asset_id")] if row.get("asset_id") else [])
        return _map_threat(row, asset_map.get(row.get("asset_id")))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to approve threat: {exc}") from exc


@router.post("/{threat_id}/whitelist", response_model=ThreatResponse)
async def whitelist_threat(threat_id: str, client_id: str = Depends(get_current_client_id)):
    """Client whitelists a threat (false positive) — AUDIT LOGGED."""
    try:
        db = _db()
        existing = db.table("threats").select("*").eq("id", threat_id).limit(1).execute().data or []
        if not existing:
            raise HTTPException(status_code=404, detail="Threat not found")
        threat = existing[0]
        old_status = threat.get("status")

        updated = db.table("threats").update({"status": "WHITELISTED"}).eq("id", threat_id).execute().data or []
        _write_audit_log(threat_id, old_status, "WHITELISTED", "CLIENT_USER")
        row = updated[0] if updated else threat
        asset_map = _fetch_asset_client_map([row.get("asset_id")] if row.get("asset_id") else [])
        return _map_threat(row, asset_map.get(row.get("asset_id")))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to whitelist threat: {exc}") from exc


@router.post("/{threat_id}/reject", response_model=ThreatResponse)
async def reject_threat(threat_id: str, client_id: str = Depends(get_current_client_id)):
    """Client rejects a threat — AUDIT LOGGED."""
    try:
        db = _db()
        existing = db.table("threats").select("*").eq("id", threat_id).limit(1).execute().data or []
        if not existing:
            raise HTTPException(status_code=404, detail="Threat not found")
        threat = existing[0]
        old_status = threat.get("status")

        updated = db.table("threats").update({"status": "REJECTED"}).eq("id", threat_id).execute().data or []
        _write_audit_log(threat_id, old_status, "REJECTED", "CLIENT_USER")
        row = updated[0] if updated else threat
        asset_map = _fetch_asset_client_map([row.get("asset_id")] if row.get("asset_id") else [])
        return _map_threat(row, asset_map.get(row.get("asset_id")))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to reject threat: {exc}") from exc


@router.get("/{threat_id}/audit-trail", response_model=List[AuditLogResponse])
async def get_audit_trail(threat_id: str, client_id: str = Depends(get_current_client_id)):
    """Get the complete audit trail for a threat."""
    try:
        res = _db().table("audit_logs").select("*").eq("threat_id", threat_id).order("changed_at", desc=False).execute()
        return [_map_audit(row) for row in (res.data or [])]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch audit trail: {exc}") from exc
