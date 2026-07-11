"""eBay Browse API discovery (free, official).

Uses the OAuth client-credentials flow, then the Browse API to find listings by
keyword and by image (``search_by_image``, base64). eBay is a major counterfeit
venue, is well indexed, and the API is free — a far better marketplace source
than scraping (which eBay blocks). Returns the same ``DiscoveryCandidate`` shape
as the other providers. Pairs with eBay VeRO as the takedown channel.

Configure ``EBAY_CLIENT_ID`` / ``EBAY_CLIENT_SECRET`` (App ID / Cert ID from
developer.ebay.com). When unset, these functions no-op.
"""
from __future__ import annotations

import base64
import logging
import time
from typing import List, Optional
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.services.serpapi_service import DiscoveryCandidate

logger = logging.getLogger(__name__)

_OAUTH_SCOPE = "https://api.ebay.com/oauth/api_scope"
_token_cache: dict[str, tuple[str, float]] = {}  # key -> (token, expiry_epoch)


def _domain(url: str) -> str:
    return (urlparse(url).netloc or "").lower().strip()


def _get_token() -> Optional[str]:
    settings = get_settings()
    cid, secret = settings.ebay_client_id, settings.ebay_client_secret
    if not cid or not secret:
        return None
    cached = _token_cache.get(cid)
    if cached and cached[1] - 60 > time.time():
        return cached[0]
    basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(
                f"{settings.ebay_oauth_base}/identity/v1/oauth2/token",
                headers={"Authorization": f"Basic {basic}",
                         "Content-Type": "application/x-www-form-urlencoded"},
                data={"grant_type": "client_credentials", "scope": _OAUTH_SCOPE},
            )
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:
        logger.warning("eBay OAuth failed: %s", exc)
        return None
    token = payload.get("access_token")
    if token:
        _token_cache[cid] = (token, time.time() + int(payload.get("expires_in", 7200)))
    return token


def _headers(token: str) -> dict:
    settings = get_settings()
    return {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": settings.ebay_marketplace_id,
        "Content-Type": "application/json",
    }


def _candidates_from_summaries(items: list) -> List[DiscoveryCandidate]:
    out: list[DiscoveryCandidate] = []
    for it in items or []:
        link = it.get("itemWebUrl") or it.get("itemHref")
        if not link:
            continue
        price = (it.get("price") or {}).get("value")
        out.append(
            DiscoveryCandidate(
                listing_url=link,
                image_url=(it.get("image") or {}).get("imageUrl")
                or next(iter([(t or {}).get("imageUrl") for t in it.get("thumbnailImages", [])]), None),
                host_domain=_domain(link) or "ebay.com",
                seller_name=(it.get("seller") or {}).get("username"),
                listing_title=it.get("title"),
                listing_price=float(price) if price else None,
            )
        )
    return out


def search_ebay(query: str, *, limit: int = 25) -> List[DiscoveryCandidate]:
    token = _get_token()
    if not token:
        return []
    settings = get_settings()
    try:
        with httpx.Client(timeout=25.0) as client:
            resp = client.get(
                f"{settings.ebay_browse_base}/item_summary/search",
                headers=_headers(token),
                params={"q": query, "limit": limit},
            )
            resp.raise_for_status()
            return _candidates_from_summaries(resp.json().get("itemSummaries"))
    except Exception as exc:
        logger.warning("eBay keyword search failed (%r): %s", query, exc)
        return []


def search_ebay_by_image(image_bytes: bytes, *, limit: int = 25) -> List[DiscoveryCandidate]:
    """Visual marketplace search — eBay's own image matcher over its catalog."""
    token = _get_token()
    if not token:
        return []
    settings = get_settings()
    b64 = base64.b64encode(image_bytes).decode()
    try:
        with httpx.Client(timeout=40.0) as client:
            resp = client.post(
                f"{settings.ebay_browse_base}/item_summary/search_by_image",
                headers=_headers(token),
                params={"limit": limit},
                json={"image": b64},
            )
            resp.raise_for_status()
            return _candidates_from_summaries(resp.json().get("itemSummaries"))
    except Exception as exc:
        logger.warning("eBay search_by_image failed: %s", exc)
        return []
