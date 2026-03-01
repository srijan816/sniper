"""Verification endpoint using real embedding similarity (SigLIP + pgvector)."""
from fastapi import APIRouter, Depends, HTTPException

from app.core.config import get_settings
from app.models.schemas import VerifyThreatRequest, VerifyThreatResponse
from app.services.threat_store import create_or_get_discovered_threat
from app.services.vector_store import get_asset_phash
from app.services.vision import compute_phash, download_bytes, phash_hamming_distance
from app.workers.vectorize import ensure_asset_vectorized, similarity_for_candidate_bytes
from app.api.deps import get_current_client_id

router = APIRouter()


@router.post("/verify-threat", response_model=VerifyThreatResponse)
async def verify_threat(data: VerifyThreatRequest, client_id: str = Depends(get_current_client_id)):
    """Module 3: verify threat candidate with pHash-first + SigLIP fallback.
    Verified: asset must belong to the authenticated client."""
    from app.core.database import get_supabase_client
    db = get_supabase_client()
    if db is None:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")

    # Verify asset ownership before processing
    asset_res = db.table("assets").select("id").eq("id", data.asset_id).eq("client_id", client_id).limit(1).execute()
    if not (asset_res.data or []):
        raise HTTPException(status_code=404, detail="Asset not found")

    settings = get_settings()
    try:
        ensure_asset_vectorized(data.asset_id)
        asset_phash = get_asset_phash(data.asset_id)

        candidate_bytes = download_bytes(data.candidate_image_url)
        candidate_phash = compute_phash(candidate_bytes)

        similarity = 0.0
        if asset_phash:
            distance = phash_hamming_distance(asset_phash, candidate_phash)
            if distance <= int(settings.phash_distance_threshold):
                similarity = max(settings.similarity_threshold, 1.0 - (distance / 64.0))
                threat_id, _ = create_or_get_discovered_threat(
                    asset_id=data.asset_id,
                    infringing_url=data.candidate_listing_url,
                    host_domain=data.host_domain,
                    similarity_score=similarity,
                    client_id=client_id,
                )
                return VerifyThreatResponse(is_threat=True, similarity_score=similarity, threat_id=threat_id)

        similarity = similarity_for_candidate_bytes(data.asset_id, candidate_bytes)
        is_threat = similarity >= settings.similarity_threshold
        if not is_threat:
            return VerifyThreatResponse(is_threat=False, similarity_score=similarity, threat_id=None)

        threat_id, _ = create_or_get_discovered_threat(
            asset_id=data.asset_id,
            infringing_url=data.candidate_listing_url,
            host_domain=data.host_domain,
            similarity_score=similarity,
            client_id=client_id,
        )
        return VerifyThreatResponse(is_threat=True, similarity_score=similarity, threat_id=threat_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to persist verified threat: {exc}") from exc
