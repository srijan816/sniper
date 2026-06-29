"""Admin dashboard API (Supabase-backed, admin-only)."""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.core.database import get_supabase_client
from app.models.schemas import AdminMetrics, CostMetrics, DLQEntry
from app.workers.takedown import queue_takedown
from app.api.deps import get_admin_user

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
async def get_admin_metrics(_admin: str = Depends(get_admin_user)):
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
async def get_cost_metrics(_admin: str = Depends(get_admin_user)):
    """Cost metrics from telemetry table when available, otherwise safe defaults."""
    try:
        res = _db().table("cost_metrics").select("*").order("created_at", desc=True).limit(1).execute()
        rows = res.data or []
        if not rows:
            raise RuntimeError("No cost_metrics rows found")
        latest = rows[0]
        return CostMetrics(
            serpapi_credits_used=int(latest.get("serpapi_credits_used") or 0),
            serpapi_credits_limit=int(latest.get("serpapi_credits_limit") or 10000),
            hf_compute_hours=float(latest.get("hf_compute_hours") or 0.0),
            zenrows_bandwidth_mb=float(latest.get("zenrows_bandwidth_mb") or 0.0),
        )
    except Exception as exc:
        if _table_missing(exc):
            return CostMetrics(
                serpapi_credits_used=0,
                serpapi_credits_limit=10000,
                hf_compute_hours=0.0,
                zenrows_bandwidth_mb=0.0,
            )
        raise HTTPException(status_code=500, detail=f"Failed to load cost metrics: {exc}") from exc


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
async def get_dead_letter_queue(_admin: str = Depends(get_admin_user)):
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
async def retry_dlq_entry(dlq_id: str, _admin: str = Depends(get_admin_user)):
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
            queue_takedown(takedown_id)
        _with_table(("dead_letter_queue", "dlq"), lambda table: db.table(table).delete().eq("id", dlq_id).execute())
        return {"status": "requeued", "takedown_id": takedown_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to retry DLQ entry: {exc}") from exc


@router.post("/dlq/{dlq_id}/dismiss")
async def dismiss_dlq_entry(dlq_id: str, _admin: str = Depends(get_admin_user)):
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


@router.get("/research")
async def get_research_queue_status(_admin: str = Depends(get_admin_user)):
    """Pipeline research queue status (AI-Q sequential jobs)."""
    from app.services.research_queue import queue_status

    return queue_status()


@router.post("/research/seed")
async def seed_pipeline_research(_admin: str = Depends(get_admin_user)):
    """Seed default pipeline research topics (skips completed)."""
    from app.workers.research import seed_research_queue

    result = seed_research_queue.delay()
    return {"status": "queued", "task_id": result.id}


@router.post("/research/tick")
async def trigger_research_tick(_admin: str = Depends(get_admin_user)):
    """Manually run one research poll/apply tick."""
    from app.workers.research import research_queue_tick

    result = research_queue_tick.delay()
    return {"status": "queued", "task_id": result.id}


@router.post("/research/adopt")
async def adopt_research_job(body: dict, _admin: str = Depends(get_admin_user)):
    """Adopt an externally submitted AI-Q job into the pipeline tracker."""
    topic_key = body.get("topic_key")
    job_id = body.get("job_id")
    if not topic_key or not job_id:
        raise HTTPException(status_code=400, detail="topic_key and job_id required")
    from app.workers.research import adopt_research_job

    task = adopt_research_job.delay(topic_key, job_id)
    return {"status": "adopted", "task_id": task.id, "topic_key": topic_key, "job_id": job_id}
