"""Takedown execution API (Supabase-backed)."""
from datetime import datetime
from typing import List
import uuid

from fastapi import APIRouter, HTTPException, Depends

from app.core.database import get_supabase_client
from app.models.schemas import TakedownCreate, TakedownResponse
from app.workers.takedown import queue_takedown
from app.api.deps import get_current_client_id

router = APIRouter()


def _db():
    db = get_supabase_client()
    if db is None:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")
    return db


def _table_missing(exc: Exception) -> bool:
    message = str(exc)
    return "PGRST205" in message or "Could not find the table" in message


def _with_takedown_table(fn):
    last_error = None
    for table_name in ("takedown_requests", "takedowns"):
        try:
            return fn(table_name)
        except Exception as exc:  # Supabase returns runtime API errors.
            if _table_missing(exc):
                last_error = exc
                continue
            raise
    raise HTTPException(status_code=500, detail=f"Takedown table not found: {last_error}")


def _map_takedown(row: dict) -> dict:
    status = row.get("status") or "PENDING"
    submitted_at = row.get("submitted_at")
    created_at = submitted_at or datetime.utcnow().isoformat()
    completed_at = row.get("completed_at")
    if completed_at is None and status in {"CONFIRMED", "FAILED"}:
        completed_at = submitted_at

    return {
        "id": row.get("id"),
        "threat_id": row.get("threat_id"),
        "platform": row.get("platform") or "shopify",
        "case_number": row.get("case_number"),
        "status": status,
        "retry_count": row.get("retry_count") or 0,
        "submitted_at": submitted_at,
        "completed_at": completed_at,
        "created_at": created_at,
    }


@router.post("/submit", response_model=TakedownResponse)
async def submit_takedown(data: TakedownCreate):
    """Queue a takedown request."""
    row = {
        "id": str(uuid.uuid4()),
        "threat_id": data.threat_id,
        "platform": data.platform,
        "status": "PENDING",
        "retry_count": 0,
        "submitted_at": datetime.utcnow().isoformat(),
    }
    try:
        res = _with_takedown_table(lambda table: _db().table(table).insert(row).execute())
        rows = res.data or []
        if not rows:
            raise HTTPException(status_code=500, detail="Takedown creation failed.")
        try:
            queue_takedown(row["id"])
        except Exception:
            # Persisted request remains visible for manual retry if queue is unavailable.
            pass
        return _map_takedown(rows[0])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to submit takedown: {exc}") from exc


@router.get("/{takedown_id}", response_model=TakedownResponse)
async def get_takedown(takedown_id: str):
    try:
        res = _with_takedown_table(
            lambda table: _db().table(table).select("*").eq("id", takedown_id).limit(1).execute()
        )
        rows = res.data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Takedown not found")
        return _map_takedown(rows[0])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch takedown: {exc}") from exc


@router.get("/", response_model=List[TakedownResponse])
async def list_takedowns(client_id: str = Depends(get_current_client_id)):
    """List takedown requests, heavily isolated by tenant context."""
    db = _db()
    
    # Securely retrieve the list of threat IDs that belong strictly to this client_id
    threats_res = db.table("threats").select("id").eq("client_id", client_id).execute()
    threat_ids = [row["id"] for row in (threats_res.data or []) if row.get("id")]
    
    if not threat_ids:
        return []
        
    try:
        def _load_all(table_name: str):
            res = db.table(table_name).select("*").in_("threat_id", threat_ids).order("created_at", desc=True).execute()
            return [_map_takedown(row) for row in (res.data or [])]

        return _with_takedown_table(_load_all)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list takedowns: {exc}") from exc
