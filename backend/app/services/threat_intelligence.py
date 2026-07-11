"""Post-discovery intelligence: AI explanations and enrichment."""
from __future__ import annotations

import logging
from typing import Optional

from app.core.database import get_supabase_client
from app.services.minimax_service import generate_threat_explanation

logger = logging.getLogger(__name__)


def _db():
    db = get_supabase_client()
    if db is None:
        raise RuntimeError("Supabase is not configured.")
    return db


def enrich_threat_with_explanation(
    threat_id: str,
    *,
    asset_name: str,
    infringing_url: str,
    host_domain: str,
    similarity_score: float,
    siglip_score: float | None = None,
    dinov2_score: float | None = None,
    phash_distance: int | None = None,
    listing_price: float | None = None,
) -> Optional[str]:
    """Generate and persist ai_explanation for a threat. Returns explanation text."""
    explanation = generate_threat_explanation(
        asset_name=asset_name,
        infringing_url=infringing_url,
        host_domain=host_domain,
        similarity_score=similarity_score,
        siglip_score=siglip_score,
        dinov2_score=dinov2_score,
        phash_distance=phash_distance,
        listing_price=listing_price,
    )
    if not explanation:
        return None

    try:
        _db().table("threats").update({"ai_explanation": explanation}).eq("id", threat_id).execute()
    except Exception as exc:
        logger.warning("Failed to persist ai_explanation for %s: %s", threat_id, exc)
        return explanation

    return explanation
