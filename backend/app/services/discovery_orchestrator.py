"""Multi-source discovery orchestration (visual + text search)."""
from __future__ import annotations

import logging
from typing import Iterable, List, Sequence
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.services.serpapi_service import DiscoveryCandidate, filter_whitelisted, search_google_lens
from app.services.searxng_service import (
    search_searxng_images,
    search_searxng_marketplaces,
)
from app.services.ebay_service import search_ebay, search_ebay_by_image

logger = logging.getLogger(__name__)


def _domain(url: str) -> str:
    return (urlparse(url).netloc or "").lower().strip()


def _dedupe_candidates(candidates: Iterable[DiscoveryCandidate]) -> List[DiscoveryCandidate]:
    seen: set[str] = set()
    unique: list[DiscoveryCandidate] = []
    for candidate in candidates:
        key = candidate.listing_url.rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _serpapi_search(engine: str, params: dict) -> dict:
    settings = get_settings()
    if not settings.serpapi_key:
        return {}
    params = {**params, "engine": engine, "api_key": settings.serpapi_key}
    try:
        with httpx.Client(timeout=90.0) as client:
            response = client.get("https://serpapi.com/search.json", params=params)
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        logger.warning("SerpApi %s search failed: %s", engine, exc)
        return {}


def search_google_shopping(query: str, *, limit: int = 20) -> List[DiscoveryCandidate]:
    """Text-based discovery via Google Shopping — catches copycat listings without exact images."""
    payload = _serpapi_search("google_shopping", {"q": query, "num": limit})
    candidates: list[DiscoveryCandidate] = []
    for item in payload.get("shopping_results") or []:
        link = item.get("link") or item.get("product_link")
        if not link:
            continue
        host = _domain(link)
        if not host:
            continue
        candidates.append(
            DiscoveryCandidate(
                listing_url=link,
                image_url=item.get("thumbnail") or item.get("image"),
                host_domain=host,
                seller_name=item.get("source"),
                listing_title=item.get("title"),
                listing_price=_parse_price(item.get("price") or item.get("extracted_price")),
            )
        )
    return candidates


def search_bing_reverse_image(image_url: str) -> List[DiscoveryCandidate]:
    """Secondary visual source — different index than Google Lens."""
    payload = _serpapi_search("bing_reverse_image", {"image_url": image_url})
    candidates: list[DiscoveryCandidate] = []
    for key in ("related_content", "images_results", "visual_matches"):
        items = payload.get(key) or []
        if not isinstance(items, list):
            continue
        for item in items:
            link = item.get("link") or item.get("url") or item.get("source_url")
            if not link:
                continue
            host = _domain(link)
            if not host:
                continue
            thumb = item.get("thumbnail") or item.get("thumbnail_url") or item.get("image")
            candidates.append(
                DiscoveryCandidate(
                    listing_url=link,
                    image_url=thumb,
                    host_domain=host,
                    seller_name=item.get("source") or item.get("domain"),
                    listing_title=item.get("title") or item.get("name"),
                )
            )
    return candidates


def _download_image(url: str, *, max_bytes: int = 8_000_000) -> bytes | None:
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.content
            return data if data and len(data) <= max_bytes else None
    except Exception as exc:
        logger.warning("image download failed (%s): %s", url, exc)
        return None


def _parse_price(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "").replace("$", "").strip()
    try:
        return float(text.split()[0])
    except (ValueError, IndexError):
        return None


def discover_candidates_for_asset(
    *,
    image_url: str,
    brand_name: str | None,
    product_title: str | None,
    whitelist_domains: Sequence[str],
    enable_shopping: bool = True,
    enable_bing: bool = True,
) -> List[DiscoveryCandidate]:
    """
    Run multi-source discovery and return deduplicated, whitelist-filtered candidates.

    SerpApi sources (Google Lens / Bing reverse-image / Google Shopping) run only
    when ``SERPAPI_KEY`` is configured. The free SearXNG sources (image search +
    marketplace ``site:`` search) run whenever ``discovery_enable_searxng`` is set.
    All candidates are still visually verified downstream by the SigLIP+DINOv2+pHash
    ensemble, so SearXNG only needs to supply plausible candidates.
    """
    settings = get_settings()
    all_candidates: list[DiscoveryCandidate] = []

    # Brand/product text query, shared by shopping + SearXNG lanes.
    query = ""
    if brand_name:
        parts = [brand_name.strip()]
        if product_title:
            parts.append(product_title.strip())
        query = " ".join(p for p in parts if p)

    # --- Paid SerpApi sources (only when a key is configured) ---
    if settings.serpapi_key:
        try:
            all_candidates.extend(search_google_lens(image_url))
        except Exception as exc:
            logger.error("Google Lens discovery failed: %s", exc)
        if enable_bing:
            all_candidates.extend(search_bing_reverse_image(image_url))
        if enable_shopping and query:
            all_candidates.extend(search_google_shopping(query))

    # --- Free SearXNG sources (image search + marketplace site: search) ---
    if settings.discovery_enable_searxng and query:
        try:
            all_candidates.extend(search_searxng_images(query))
            marketplaces = [m.strip() for m in (settings.discovery_marketplaces or "").split(",") if m.strip()]
            if marketplaces:
                all_candidates.extend(search_searxng_marketplaces(query, marketplaces))
        except Exception as exc:
            logger.warning("SearXNG discovery failed: %s", exc)

    # --- eBay Browse API (free official marketplace source; needs credentials) ---
    if settings.discovery_enable_ebay and settings.ebay_client_id and settings.ebay_client_secret:
        try:
            if query:
                all_candidates.extend(search_ebay(query))
            img_bytes = _download_image(image_url)
            if img_bytes:
                all_candidates.extend(search_ebay_by_image(img_bytes))
        except Exception as exc:
            logger.warning("eBay discovery failed: %s", exc)

    return filter_whitelisted(_dedupe_candidates(all_candidates), whitelist_domains)
