"""Admin dashboard API (partially Supabase-backed)."""
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException

from app.core.database import get_supabase_client
from app.models.schemas import AdminMetrics, CostMetrics, DLQEntry

router = APIRouter()


def _db():
    db = get_supabase_client()
    if db is None:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")
    return db


def _table_missing(exc: Exception) -> bool:
    message = str(exc)
    return "PGRST205" in message or "Could not find the table" in message


def _with_table(candidates, fn):
    last_error = None
    for table_name in candidates:
        try:
            return fn(table_name)
        except Exception as exc:
            if _table_missing(exc):
                last_error = exc
                continue
            raise
    raise HTTPException(status_code=500, detail=f"Required table not found: {last_error}")


@router.get("/metrics", response_model=AdminMetrics)
async def get_admin_metrics():
    """Global admin metrics — MRR, clients, threats."""
    try:
        db = _db()
        clients = db.table("clients").select("subscription_tier").execute().data or []
        threats = db.table("threats").select("status").execute().data or []
        dlq = _with_table(("dead_letter_queue", "dlq"), lambda table: db.table(table).select("id").execute()).data or []

        tier_prices = {
            "FREE": 0.0,
            "STARTER": 99.0,
            "GROWTH": 500.0,
            "AGENCY": 1500.0,
        }

        total_mrr = sum(tier_prices.get((client.get("subscription_tier") or "FREE").upper(), 0.0) for client in clients)
        total_discovered = len(threats)
        total_removed = len([t for t in threats if (t.get("status") or "").upper() in {"REMOVED", "TAKEDOWN_CONFIRMED"}])
        pending = len(
            [
                t
                for t in threats
                if (t.get("status") or "").upper() in {"DISCOVERED", "PENDING_APPROVAL", "APPROVED", "TAKEDOWN_SUBMITTED"}
            ]
        )

        return AdminMetrics(
            total_mrr=total_mrr,
            active_clients=len(clients),
            total_threats_discovered=total_discovered,
            total_threats_removed=total_removed,
            threats_pending=pending,
            dlq_count=len(dlq),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load admin metrics: {exc}") from exc


@router.get("/costs", response_model=CostMetrics)
async def get_cost_metrics():
    """Cost metrics placeholder until cost telemetry table is implemented."""
    return CostMetrics(
        serpapi_credits_used=0,
        serpapi_credits_limit=10000,
        hf_compute_hours=0.0,
        zenrows_bandwidth_mb=0.0,
    )


def _map_dlq(row: dict) -> dict:
    return {
        "id": row.get("id"),
        "takedown_id": row.get("takedown_id"),
        "error_reason": row.get("error_reason") or "Unknown error",
        "stack_trace": row.get("error_reason"),
        "resolved": False,
        "resolved_at": None,
        "failed_at": row.get("failed_at") or datetime.utcnow().isoformat(),
    }


@router.get("/dlq", response_model=List[DLQEntry])
async def get_dead_letter_queue():
    """Dead letter queue (unresolved failed RPA tasks)."""
    try:
        res = _with_table(
            ("dead_letter_queue", "dlq"),
            lambda table: _db().table(table).select("*").order("failed_at", desc=True).execute(),
        )
        return [_map_dlq(row) for row in (res.data or [])]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load DLQ: {exc}") from exc


@router.post("/dlq/{dlq_id}/retry")
async def retry_dlq_entry(dlq_id: str):
    """Re-run a failed takedown from DLQ by resetting request and removing DLQ row."""
    try:
        db = _db()
        rows = _with_table(
            ("dead_letter_queue", "dlq"),
            lambda table: db.table(table).select("*").eq("id", dlq_id).limit(1).execute(),
        ).data or []
        if not rows:
            raise HTTPException(status_code=404, detail="DLQ entry not found")
        entry = rows[0]
        takedown_id = entry.get("takedown_id")
        if takedown_id:
            _with_table(
                ("takedown_requests", "takedowns"),
                lambda table: db.table(table).update({"status": "PENDING", "retry_count": 0}).eq("id", takedown_id).execute(),
            )
        _with_table(("dead_letter_queue", "dlq"), lambda table: db.table(table).delete().eq("id", dlq_id).execute())
        return {"status": "requeued", "takedown_id": takedown_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to retry DLQ entry: {exc}") from exc


@router.post("/dlq/{dlq_id}/dismiss")
async def dismiss_dlq_entry(dlq_id: str):
    """Dismiss a DLQ entry by removing it from queue."""
    try:
        res = _with_table(("dead_letter_queue", "dlq"), lambda table: _db().table(table).delete().eq("id", dlq_id).execute())
        if not (res.data or []):
            raise HTTPException(status_code=404, detail="DLQ entry not found")
        return {"status": "dismissed"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to dismiss DLQ entry: {exc}") from exc
