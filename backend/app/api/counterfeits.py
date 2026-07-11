"""Counterfeits wall (admin-only).

Read-only endpoint that surfaces threats which a human has already reviewed
(approved or actioned) — never raw automated discoveries. Requires an admin
bearer token (it exposes cross-client asset images and enforcement actions, so
it is not public). Each item pairs the brand's original asset image with the
infringing listing image + similarity.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_admin_user
from app.core.database import get_supabase_client
from app.services.storage_util import to_public_url

logger = logging.getLogger(__name__)

router = APIRouter()

# Only statuses that a human has reviewed/actioned are ever shown publicly.
PUBLIC_STATUSES = ["APPROVED", "CONFIRMED", "TAKEDOWN_SUBMITTED", "TAKEDOWN_CONFIRMED", "REMOVED"]


@router.get("")
def list_counterfeits(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: str = Depends(get_admin_user),
) -> dict:
    db = get_supabase_client()
    if db is None:
        return {"success": True, "data": [], "meta": {"total": 0, "note": "database unavailable"}}

    try:
        res = (
            db.table("threats")
            .select("id,asset_id,infringing_url,infringing_image_url,host_domain,"
                    "seller_name,listing_title,similarity_score,status,discovered_at")
            .in_("status", PUBLIC_STATUSES)
            .order("discovered_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        threats = res.data or []
    except Exception as exc:
        logger.warning("counterfeits query failed: %s", exc)
        return {"success": True, "data": [], "meta": {"total": 0}}

    # Resolve original images for the referenced assets.
    asset_ids = list({t["asset_id"] for t in threats if t.get("asset_id")})
    originals: dict[str, str] = {}
    if asset_ids:
        try:
            ares = db.table("assets").select("id,storage_url,thumbnail_url").in_("id", asset_ids).execute()
            for a in ares.data or []:
                originals[a["id"]] = to_public_url(a.get("thumbnail_url") or a.get("storage_url") or "")
        except Exception as exc:
            logger.warning("counterfeits asset lookup failed: %s", exc)

    items = [
        {
            "id": t["id"],
            "original_image": originals.get(t.get("asset_id")),
            "infringing_image": t.get("infringing_image_url"),
            "listing_url": t.get("infringing_url"),
            "marketplace": t.get("host_domain"),
            "seller": t.get("seller_name"),
            "title": t.get("listing_title"),
            "similarity": t.get("similarity_score"),
            "status": t.get("status"),
            "detected_at": t.get("discovered_at"),
        }
        for t in threats
    ]
    return {
        "success": True,
        "data": items,
        "meta": {
            "count": len(items),
            "offset": offset,
            "disclaimer": "Automated image-similarity matches reviewed before listing. "
                          "Similarity is an indicator, not a legal determination.",
        },
    }
