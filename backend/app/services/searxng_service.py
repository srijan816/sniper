"""SearXNG discovery integration.

Free, self-hosted alternative to SerpApi for sourcing candidate listings. Reuses
the shared SearXNG instance (reachable at ``settings.searxng_url``). Returns the
same ``DiscoveryCandidate`` shape as the SerpApi sources, so the downstream
matching/threat pipeline is unchanged — candidate images are still verified by
the SigLIP+DINOv2+pHash ensemble (which is the actual counterfeit decision).

Lanes:
- image search (``categories=images``): visual candidates by brand/product text
- web search: listing pages (Bing works without a proxy from datacenter IPs)
- marketplace search: ``site:<host>`` targeted web search per configured marketplace
"""
from __future__ import annotations

import logging
from typing import List, Sequence
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.services.serpapi_service import DiscoveryCandidate

logger = logging.getLogger(__name__)


def _domain(url: str) -> str:
    return (urlparse(url).netloc or "").lower().strip()


def _query(params: dict) -> dict:
    settings = get_settings()
    base = (settings.searxng_url or "").rstrip("/")
    if not base:
        return {}
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{base}/search", params={**params, "format": "json", "safesearch": 0})
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:  # network/engine errors must not break discovery
        logger.warning("SearXNG query failed (q=%r): %s", params.get("q"), exc)
        return {}


def _candidates_from_results(results: list, *, limit: int) -> List[DiscoveryCandidate]:
    out: list[DiscoveryCandidate] = []
    for item in results[:limit]:
        link = item.get("url") or item.get("source")
        if not link:
            continue
        host = _domain(link)
        if not host:
            continue
        out.append(
            DiscoveryCandidate(
                listing_url=link,
                image_url=item.get("img_src") or item.get("thumbnail_src") or item.get("thumbnail"),
                host_domain=host,
                seller_name=item.get("source"),
                listing_title=item.get("title"),
            )
        )
    return out


def search_searxng_images(query: str, *, limit: int = 30) -> List[DiscoveryCandidate]:
    settings = get_settings()
    payload = _query({"q": query, "categories": "images", "engines": settings.searxng_image_engines})
    return _candidates_from_results(payload.get("results") or [], limit=limit)


def search_searxng_web(query: str, *, limit: int = 20) -> List[DiscoveryCandidate]:
    settings = get_settings()
    payload = _query({"q": query, "engines": settings.searxng_engines})
    return _candidates_from_results(payload.get("results") or [], limit=limit)


def search_searxng_marketplaces(query: str, marketplaces: Sequence[str], *, per_site: int = 10) -> List[DiscoveryCandidate]:
    out: list[DiscoveryCandidate] = []
    for site in marketplaces:
        site = site.strip()
        if not site:
            continue
        out.extend(search_searxng_web(f"site:{site} {query}", limit=per_site))
    return out
