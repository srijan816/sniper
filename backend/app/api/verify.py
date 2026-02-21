"""Verification endpoint (Supabase-backed insert for high-confidence threats)."""
from datetime import datetime
import random
import uuid

from fastapi import APIRouter, HTTPException

from app.core.database import get_supabase_client
from app.models.schemas import VerifyThreatRequest, VerifyThreatResponse

router = APIRouter()


def _db():
    db = get_supabase_client()
    if db is None:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")
    return db


@router.post("/verify-threat", response_model=VerifyThreatResponse)
async def verify_threat(data: VerifyThreatRequest):
    """
    Module 3: Verification & Audit Engine.
    TODO: replace mock scoring with SigLIP similarity scoring.
    """
    mock_score = round(random.uniform(0.88, 0.99), 4)
    is_threat = mock_score >= 0.95

    if not is_threat:
        return VerifyThreatResponse(is_threat=False, similarity_score=mock_score, threat_id=None)

    threat_id = str(uuid.uuid4())
    try:
        db = _db()
        threat_row = {
            "id": threat_id,
            "asset_id": data.asset_id,
            "infringing_url": data.candidate_listing_url,
            "host_domain": data.host_domain,
            "similarity_score": mock_score,
            "status": "DISCOVERED",
            "discovered_at": datetime.utcnow().isoformat(),
        }
        db.table("threats").insert(threat_row).execute()
        db.table("audit_logs").insert(
            {
                "threat_id": threat_id,
                "old_status": None,
                "new_status": "DISCOVERED",
                "changed_by": "SYSTEM",
            }
        ).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to persist verified threat: {exc}") from exc

    return VerifyThreatResponse(is_threat=True, similarity_score=mock_score, threat_id=threat_id)
