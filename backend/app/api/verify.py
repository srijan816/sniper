"""Verification endpoint using real embedding similarity (SigLIP + pgvector)."""
from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.models.schemas import VerifyThreatRequest, VerifyThreatResponse
from app.services.threat_store import create_or_get_discovered_threat
from app.services.vector_store import get_asset_phash
from app.services.vision import compute_phash, download_bytes, phash_hamming_distance
from app.workers.vectorize import ensure_asset_vectorized, similarity_for_candidate_bytes

router = APIRouter()


@router.post("/verify-threat", response_model=VerifyThreatResponse)
async def verify_threat(data: VerifyThreatRequest):
    """Module 3: verify threat candidate with pHash-first + SigLIP fallback."""
    settings = get_settings()
    try:
        # Ensure phash/embedding is available for the protected asset.
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
        )
        return VerifyThreatResponse(is_threat=True, similarity_score=similarity, threat_id=threat_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to persist verified threat: {exc}") from exc
