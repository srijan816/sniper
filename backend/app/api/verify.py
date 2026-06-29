"""Verification endpoint using SigLIP 2 + DINOv2 ensemble similarity."""
from fastapi import APIRouter, Depends, HTTPException

from app.core.config import get_settings
from app.models.schemas import VerifyThreatRequest, VerifyThreatResponse
from app.services.threat_intelligence import enrich_threat_with_explanation
from app.services.threat_store import create_or_get_discovered_threat
from app.services.vector_store import get_asset_phash
from app.services.vision import combined_similarity, compute_phash, download_bytes, phash_hamming_distance
from app.workers.vectorize import ensure_asset_vectorized
from app.api.deps import get_current_client_id

router = APIRouter()


@router.post("/verify-threat", response_model=VerifyThreatResponse)
async def verify_threat(data: VerifyThreatRequest, client_id: str = Depends(get_current_client_id)):
    """Verify threat candidate with pHash fast-path + SigLIP2/DINOv2 ensemble."""
    from app.core.database import get_supabase_client
    db = get_supabase_client()
    if db is None:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")

    asset_res = db.table("assets").select("id,original_filename,storage_url").eq("id", data.asset_id).eq("client_id", client_id).limit(1).execute()
    asset_rows = asset_res.data or []
    if not asset_rows:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset = asset_rows[0]

    settings = get_settings()
    try:
        ensure_asset_vectorized(data.asset_id)
        asset_phash = get_asset_phash(data.asset_id)
        asset_bytes = download_bytes(asset["storage_url"])
        candidate_bytes = download_bytes(data.candidate_image_url)
        candidate_phash = compute_phash(candidate_bytes)

        if asset_phash:
            distance = phash_hamming_distance(asset_phash, candidate_phash)
            if distance <= int(settings.phash_distance_threshold):
                similarity = max(settings.similarity_threshold, 1.0 - (distance / 64.0))
                threat_id, created = create_or_get_discovered_threat(
                    asset_id=data.asset_id,
                    infringing_url=data.candidate_listing_url,
                    host_domain=data.host_domain,
                    similarity_score=similarity,
                    client_id=client_id,
                )
                if created:
                    enrich_threat_with_explanation(
                        threat_id,
                        asset_name=asset.get("original_filename") or "Protected asset",
                        infringing_url=data.candidate_listing_url,
                        host_domain=data.host_domain,
                        similarity_score=similarity,
                        phash_distance=distance,
                    )
                return VerifyThreatResponse(is_threat=True, similarity_score=similarity, threat_id=threat_id)

        breakdown = combined_similarity(asset_bytes, candidate_bytes, asset_phash=asset_phash)
        similarity = breakdown.combined
        is_threat = similarity >= settings.similarity_threshold
        if not is_threat:
            return VerifyThreatResponse(is_threat=False, similarity_score=similarity, threat_id=None)

        threat_id, created = create_or_get_discovered_threat(
            asset_id=data.asset_id,
            infringing_url=data.candidate_listing_url,
            host_domain=data.host_domain,
            similarity_score=similarity,
            client_id=client_id,
        )
        if created:
            enrich_threat_with_explanation(
                threat_id,
                asset_name=asset.get("original_filename") or "Protected asset",
                infringing_url=data.candidate_listing_url,
                host_domain=data.host_domain,
                similarity_score=similarity,
                siglip_score=breakdown.siglip,
                dinov2_score=breakdown.dinov2,
                phash_distance=breakdown.phash_distance,
            )
        return VerifyThreatResponse(is_threat=True, similarity_score=similarity, threat_id=threat_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to persist verified threat: {exc}") from exc
