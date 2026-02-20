"""Takedown execution API — Module 4"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import TakedownCreate, TakedownResponse, DLQEntry
from typing import List
from datetime import datetime
import uuid

router = APIRouter()

# In-memory stores
_mock_takedowns = {}
_mock_dlq = {}


def _seed_demo_takedowns():
    """Seed demo takedowns and DLQ entries"""
    _mock_takedowns["td-demo-001"] = {
        "id": "td-demo-001",
        "threat_id": "threat-demo-004",
        "platform": "shopify",
        "case_number": "DMCA-2024-SHP-001",
        "status": "CONFIRMED",
        "retry_count": 0,
        "submitted_at": datetime.now().isoformat(),
        "completed_at": datetime.now().isoformat(),
        "created_at": datetime.now().isoformat(),
    }
    # A failed takedown in DLQ
    _mock_takedowns["td-demo-002"] = {
        "id": "td-demo-002",
        "threat_id": "threat-demo-002",
        "platform": "shopify",
        "case_number": None,
        "status": "FAILED",
        "retry_count": 5,
        "submitted_at": datetime.now().isoformat(),
        "completed_at": None,
        "created_at": datetime.now().isoformat(),
    }
    _mock_dlq["dlq-demo-001"] = {
        "id": "dlq-demo-001",
        "takedown_id": "td-demo-002",
        "error_reason": "Timeout on Submit button — Turnstile CAPTCHA blocked after 5 retries",
        "stack_trace": 'playwright._impl._errors.TimeoutError: Timeout 30000ms exceeded.\n  at Page.click("#submit-dmca-btn")\n  at ShopifyDMCA.submit_form(shopify_rpa.py:142)\n  at TakedownWorker.execute(takedown.py:87)',
        "resolved": False,
        "resolved_at": None,
        "failed_at": datetime.now().isoformat(),
    }


_seed_demo_takedowns()


@router.post("/submit", response_model=TakedownResponse)
async def submit_takedown(data: TakedownCreate):
    """Queue a takedown request — triggers Celery worker in production"""
    td_id = str(uuid.uuid4())
    takedown = {
        "id": td_id,
        "threat_id": data.threat_id,
        "platform": data.platform,
        "case_number": None,
        "status": "PENDING",
        "retry_count": 0,
        "submitted_at": None,
        "completed_at": None,
        "created_at": datetime.now().isoformat(),
    }
    _mock_takedowns[td_id] = takedown
    # In production: takedown_task.delay(td_id)
    return takedown


@router.get("/{takedown_id}", response_model=TakedownResponse)
async def get_takedown(takedown_id: str):
    if takedown_id not in _mock_takedowns:
        raise HTTPException(status_code=404, detail="Takedown not found")
    return _mock_takedowns[takedown_id]


@router.get("/", response_model=List[TakedownResponse])
async def list_takedowns(threat_id: str = None):
    tds = list(_mock_takedowns.values())
    if threat_id:
        tds = [t for t in tds if t["threat_id"] == threat_id]
    return tds
