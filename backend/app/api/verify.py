"""Verification endpoint using real embedding similarity (SigLIP + pgvector)."""
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.core.database import get_supabase_client
from app.models.schemas import VerifyThreatRequest, VerifyThreatResponse
from app.workers.vectorize import similarity_for_candidate

router = APIRouter()


def _db():
    db = get_supabase_client()
    if db is None:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")
    return db


@router.post("/verify-threat", response_model=VerifyThreatResponse)
async def verify_threat(data: VerifyThreatRequest):
    """Module 3: verify threat candidate with real cosine similarity."""
    settings = get_settings()
    similarity = similarity_for_candidate(data.asset_id, data.candidate_image_url)
    is_threat = similarity >= settings.similarity_threshold

    if not is_threat:
        return VerifyThreatResponse(is_threat=False, similarity_score=similarity, threat_id=None)

    threat_id = str(uuid.uuid4())
    try:
        db = _db()
        existing = (
            db.table("threats")
            .select("id")
            .eq("asset_id", data.asset_id)
            .eq("infringing_url", data.candidate_listing_url)
            .limit(1)
            .execute()
            .data
            or []
        )
        if existing:
            return VerifyThreatResponse(is_threat=True, similarity_score=similarity, threat_id=existing[0]["id"])

        threat_row = {
            "id": threat_id,
            "asset_id": data.asset_id,
            "infringing_url": data.candidate_listing_url,
            "host_domain": data.host_domain,
            "similarity_score": similarity,
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

    return VerifyThreatResponse(is_threat=True, similarity_score=similarity, threat_id=threat_id)
