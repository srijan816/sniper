"""Threat management API routes — The core HITL workflow"""
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import (
    ThreatResponse,
    ThreatStatusUpdate,
    ThreatStatus,
    AuditLogResponse,
    ActorType,
)
from typing import List, Optional
from datetime import datetime
import uuid
import os

router = APIRouter()

# In-memory stores
_mock_threats = {}
_mock_audit_logs = {}


def _demo_enabled() -> bool:
    return os.getenv("ENABLE_DEMO_DATA", "false").strip().lower() in {"1", "true", "yes", "on"}


def _write_audit_log(threat_id: str, old_status: str, new_status: str, changed_by: str, metadata: dict = None):
    """CRITICAL: Write immutable audit log entry for 512(f) compliance"""
    log_id = str(uuid.uuid4())
    _mock_audit_logs[log_id] = {
        "id": log_id,
        "threat_id": threat_id,
        "old_status": old_status,
        "new_status": new_status,
        "changed_by": changed_by,
        "metadata": metadata or {},
        "changed_at": datetime.now().isoformat(),
    }
    return log_id


def _seed_demo_threats():
    """Seed demo threats for the onboarding 'Aha!' moment"""
    demos = [
        {
            "id": "threat-demo-001",
            "asset_id": "asset-demo-001",
            "client_id": "demo-client-001",
            "infringing_url": "https://fakeshop.example.com/premium-sneaker-v2-replica",
            "infringing_image_url": "https://via.placeholder.com/400x400/ff4444/ffffff?text=Counterfeit+1",
            "host_domain": "fakeshop.example.com",
            "seller_name": "CheapKickz Store",
            "listing_title": "Premium Sneaker V2 - Best Quality Replica",
            "listing_price": 39.99,
            "similarity_score": 0.97,
            "status": "PENDING_APPROVAL",
            "discovered_at": datetime.now().isoformat(),
            "resolved_at": None,
        },
        {
            "id": "threat-demo-002",
            "asset_id": "asset-demo-001",
            "client_id": "demo-client-001",
            "infringing_url": "https://counterfeit-mall.example.com/sneaker-deal",
            "infringing_image_url": "https://via.placeholder.com/400x400/ff6600/ffffff?text=Counterfeit+2",
            "host_domain": "counterfeit-mall.example.com",
            "seller_name": "BargainFootwear",
            "listing_title": "Designer Sneaker V2 Factory Direct",
            "listing_price": 24.99,
            "similarity_score": 0.96,
            "status": "PENDING_APPROVAL",
            "discovered_at": datetime.now().isoformat(),
            "resolved_at": None,
        },
        {
            "id": "threat-demo-003",
            "asset_id": "asset-demo-002",
            "client_id": "demo-client-001",
            "infringing_url": "https://shopee.example.com/knockoff-bag-limited",
            "infringing_image_url": "https://via.placeholder.com/400x400/cc00cc/ffffff?text=Counterfeit+3",
            "host_domain": "shopee.example.com",
            "seller_name": "LuxBagDeals",
            "listing_title": "Limited Edition Bag - Same Factory!",
            "listing_price": 55.00,
            "similarity_score": 0.95,
            "status": "DISCOVERED",
            "discovered_at": datetime.now().isoformat(),
            "resolved_at": None,
        },
        {
            "id": "threat-demo-004",
            "asset_id": "asset-demo-001",
            "client_id": "demo-client-001",
            "infringing_url": "https://wish-deals.example.com/sneaker-cheap",
            "infringing_image_url": "https://via.placeholder.com/400x400/0066ff/ffffff?text=Resolved",
            "host_domain": "wish-deals.example.com",
            "seller_name": "FlashDeals99",
            "listing_title": "Branded Sneaker Lookalike",
            "listing_price": 15.99,
            "similarity_score": 0.98,
            "status": "REMOVED",
            "discovered_at": datetime.now().isoformat(),
            "resolved_at": datetime.now().isoformat(),
        },
    ]
    for d in demos:
        _mock_threats[d["id"]] = d
        _write_audit_log(d["id"], None, "DISCOVERED", "SYSTEM", {"source": "demo_seed"})
        if d["status"] == "PENDING_APPROVAL":
            _write_audit_log(d["id"], "DISCOVERED", "PENDING_APPROVAL", "SYSTEM")
        elif d["status"] == "REMOVED":
            _write_audit_log(d["id"], None, "DISCOVERED", "SYSTEM")
            _write_audit_log(d["id"], "DISCOVERED", "APPROVED", "CLIENT_USER")
            _write_audit_log(d["id"], "APPROVED", "TAKEDOWN_SUBMITTED", "SYSTEM")
            _write_audit_log(d["id"], "TAKEDOWN_SUBMITTED", "REMOVED", "SYSTEM")


if _demo_enabled():
    _seed_demo_threats()


@router.get("/", response_model=List[ThreatResponse])
async def list_threats(
    client_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List threats with optional filtering"""
    threats = list(_mock_threats.values())
    if client_id:
        threats = [t for t in threats if t["client_id"] == client_id]
    if status:
        threats = [t for t in threats if t["status"] == status]
    threats.sort(key=lambda t: t["discovered_at"], reverse=True)
    return threats[offset : offset + limit]


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def list_audit_logs(
    threat_id: Optional[str] = None,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    logs = list(_mock_audit_logs.values())
    if threat_id:
        logs = [log for log in logs if log["threat_id"] == threat_id]
    logs.sort(key=lambda l: l["changed_at"], reverse=True)
    return logs[offset : offset + limit]


@router.get("/{threat_id}", response_model=ThreatResponse)
async def get_threat(threat_id: str):
    if threat_id not in _mock_threats:
        raise HTTPException(status_code=404, detail="Threat not found")
    return _mock_threats[threat_id]


@router.post("/{threat_id}/approve", response_model=ThreatResponse)
async def approve_threat(threat_id: str):
    """Client approves a threat for takedown — AUDIT LOGGED"""
    if threat_id not in _mock_threats:
        raise HTTPException(status_code=404, detail="Threat not found")

    threat = _mock_threats[threat_id]
    old_status = threat["status"]

    if old_status not in ["DISCOVERED", "PENDING_APPROVAL"]:
        raise HTTPException(status_code=400, detail=f"Cannot approve threat in status {old_status}")

    threat["status"] = "APPROVED"
    _write_audit_log(threat_id, old_status, "APPROVED", "CLIENT_USER",
                     {"action": "manual_approval"})
    return threat


@router.post("/{threat_id}/whitelist", response_model=ThreatResponse)
async def whitelist_threat(threat_id: str):
    """Client whitelists a threat (false positive) — AUDIT LOGGED"""
    if threat_id not in _mock_threats:
        raise HTTPException(status_code=404, detail="Threat not found")

    threat = _mock_threats[threat_id]
    old_status = threat["status"]
    threat["status"] = "WHITELISTED"
    _write_audit_log(threat_id, old_status, "WHITELISTED", "CLIENT_USER",
                     {"action": "manual_whitelist"})
    return threat


@router.post("/{threat_id}/reject", response_model=ThreatResponse)
async def reject_threat(threat_id: str):
    """Client rejects a threat — AUDIT LOGGED"""
    if threat_id not in _mock_threats:
        raise HTTPException(status_code=404, detail="Threat not found")

    threat = _mock_threats[threat_id]
    old_status = threat["status"]
    threat["status"] = "REJECTED"
    _write_audit_log(threat_id, old_status, "REJECTED", "CLIENT_USER",
                     {"action": "manual_rejection"})
    return threat


@router.get("/{threat_id}/audit-trail", response_model=List[AuditLogResponse])
async def get_audit_trail(threat_id: str):
    """Get the complete audit trail for a threat — 512(f) compliance"""
    logs = [log for log in _mock_audit_logs.values() if log["threat_id"] == threat_id]
    logs.sort(key=lambda l: l["changed_at"])
    return logs
