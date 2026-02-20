"""Admin dashboard API — Module 5"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import AdminMetrics, CostMetrics, DLQEntry
from typing import List
from datetime import datetime

router = APIRouter()

# Import DLQ from takedown module
from app.api.takedown import _mock_dlq, _mock_takedowns


@router.get("/metrics", response_model=AdminMetrics)
async def get_admin_metrics():
    """Global admin metrics — MRR, clients, threats"""
    return AdminMetrics(
        total_mrr=7_599.00,  # 3 Starter ($297) + 2 Growth ($1000) + 4 Agency ($6000) + demo calc
        active_clients=12,
        total_threats_discovered=1_847,
        total_threats_removed=1_423,
        threats_pending=89,
        dlq_count=len([d for d in _mock_dlq.values() if not d.get("resolved", False)]),
    )


@router.get("/costs", response_model=CostMetrics)
async def get_cost_metrics():
    """API cost monitoring — crucial for pricing tier profitability"""
    return CostMetrics(
        serpapi_credits_used=4_230,
        serpapi_credits_limit=10_000,
        hf_compute_hours=12.4,
        zenrows_bandwidth_mb=847.2,
    )


@router.get("/dlq", response_model=List[DLQEntry])
async def get_dead_letter_queue():
    """Dead letter queue — failed RPA tasks"""
    return list(_mock_dlq.values())


@router.post("/dlq/{dlq_id}/retry")
async def retry_dlq_entry(dlq_id: str):
    """Re-run a failed takedown from the DLQ"""
    if dlq_id not in _mock_dlq:
        raise HTTPException(status_code=404, detail="DLQ entry not found")

    entry = _mock_dlq[dlq_id]

    # In production: re-queue the Celery task
    # takedown_task.delay(entry["takedown_id"])

    # Reset the takedown
    if entry["takedown_id"] in _mock_takedowns:
        _mock_takedowns[entry["takedown_id"]]["status"] = "PENDING"
        _mock_takedowns[entry["takedown_id"]]["retry_count"] = 0

    entry["resolved"] = True
    entry["resolved_at"] = datetime.now().isoformat()

    return {"status": "requeued", "takedown_id": entry["takedown_id"]}


@router.post("/dlq/{dlq_id}/dismiss")
async def dismiss_dlq_entry(dlq_id: str):
    """Dismiss a DLQ entry (won't retry)"""
    if dlq_id not in _mock_dlq:
        raise HTTPException(status_code=404, detail="DLQ entry not found")

    _mock_dlq[dlq_id]["resolved"] = True
    _mock_dlq[dlq_id]["resolved_at"] = datetime.now().isoformat()

    return {"status": "dismissed"}
