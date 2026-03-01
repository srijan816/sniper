"""SerpApi Google Lens integration for discovery."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Iterable, List, Sequence
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryCandidate:
    listing_url: str
    image_url: str | None
    host_domain: str
    seller_name: str | None = None
    listing_title: str | None = None
    listing_price: float | None = None


def _domain(url: str) -> str:
    return (urlparse(url).netloc or "").lower().strip()


def _is_whitelisted(candidate_domain: str, whitelist_domains: Sequence[str]) -> bool:
    domain = candidate_domain.lower()
    for whitelisted in whitelist_domains:
        normalized = whitelisted.lower().strip()
        if not normalized:
            continue
        if domain == normalized or domain.endswith(f".{normalized}"):
            return True
    return False


def search_google_lens(image_url: str) -> List[DiscoveryCandidate]:
    settings = get_settings()
    if not settings.serpapi_key:
        raise RuntimeError("SERPAPI_KEY is required for discovery.")

    params = {
        "engine": settings.serpapi_engine,
        "url": image_url,
        "api_key": settings.serpapi_key,
    }

    max_retries = 3
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=90.0) as client:
                response = client.get("https://serpapi.com/search.json", params=params)
                if response.status_code in (429, 500, 502, 503, 504):
                    wait = 2 ** attempt
                    logger.warning("SerpApi attempt %d/%d got %d — retrying in %ds", attempt + 1, max_retries, response.status_code, wait)
                    time.sleep(wait)
                    last_exc = httpx.HTTPStatusError(f"HTTP {response.status_code}", request=response.request, response=response)
                    continue
                response.raise_for_status()
                payload = response.json()
                break
        except httpx.TimeoutException as exc:
            wait = 2 ** attempt
            logger.warning("SerpApi attempt %d/%d timed out — retrying in %ds", attempt + 1, max_retries, wait)
            time.sleep(wait)
            last_exc = exc
    else:
        raise RuntimeError(f"SerpApi failed after {max_retries} attempts") from last_exc

    candidates: list[DiscoveryCandidate] = []
    for key in ("visual_matches", "inline_images"):
        items = payload.get(key) or []
        if not isinstance(items, list):
            continue
        for item in items:
            link = item.get("link") or item.get("url")
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
                    seller_name=item.get("source"),
                    listing_title=item.get("title"),
                )
            )
    return candidates


def filter_whitelisted(
    candidates: Iterable[DiscoveryCandidate],
    whitelist_domains: Sequence[str],
) -> List[DiscoveryCandidate]:
    return [c for c in candidates if not _is_whitelisted(c.host_domain, whitelist_domains)]
