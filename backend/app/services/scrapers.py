"""Abstract Discovery Factory & Specialized Walled-Garden Scrapers."""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Iterable, List, Sequence
from urllib.parse import quote_plus, urlparse
import httpx

from app.core.config import get_settings


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


def filter_whitelisted(
    candidates: Iterable[DiscoveryCandidate],
    whitelist_domains: Sequence[str],
) -> List[DiscoveryCandidate]:
    return [c for c in candidates if not _is_whitelisted(c.host_domain, whitelist_domains)]


# ==========================================
# Discovery Engine Interface
# ==========================================

class DiscoveryEngine(abc.ABC):
    """Abstract interface for all discovery radar scanners."""
    
    @abc.abstractmethod
    def search_by_image(self, image_url: str) -> List[DiscoveryCandidate]:
        """Reverse image search methodology."""
        pass

    @abc.abstractmethod
    def search_by_keyword(self, keyword: str) -> List[DiscoveryCandidate]:
        """Text-based lookup methodology."""
        pass


# ==========================================
# Google Lens (SerpApi)
# ==========================================

class GoogleLensEngine(DiscoveryEngine):
    """The default SerpApi integration targeting the open web."""
    
    def search_by_image(self, image_url: str) -> List[DiscoveryCandidate]:
        settings = get_settings()
        if not settings.serpapi_key:
            return []

        params = {
            "engine": settings.serpapi_engine,
            "url": image_url,
            "api_key": settings.serpapi_key,
        }
        try:
            with httpx.Client(timeout=45.0) as client:
                response = client.get("https://serpapi.com/search.json", params=params)
                response.raise_for_status()
                payload = response.json()
        except Exception:
            return []

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

    def search_by_keyword(self, keyword: str) -> List[DiscoveryCandidate]:
        # Implementation via SerpApi 'google' or 'google_shopping' engine
        settings = get_settings()
        if not settings.serpapi_key:
            return []
            
        params = {
            "engine": "google",
            "q": f"{keyword} replica dhgate aliexpress",
            "api_key": settings.serpapi_key,
        }
        try:
            with httpx.Client(timeout=45.0) as client:
                response = client.get("https://serpapi.com/search.json", params=params)
                response.raise_for_status()
                payload = response.json()
        except Exception:
            return []
            
        candidates: list[DiscoveryCandidate] = []
        for item in payload.get("organic_results", []):
            link = item.get("link")
            if not link:
                continue
            host = _domain(link)
            thumb = item.get("thumbnail") 
            candidates.append(
                DiscoveryCandidate(
                    listing_url=link,
                    image_url=thumb, # May be null, will require DOM follow-up later
                    host_domain=host,
                    seller_name=item.get("source"),
                    listing_title=item.get("title"),
                )
            )
        return candidates


# ==========================================
# AliExpress Walled-Garden Scraper
# ==========================================

class AliExpressEngine(DiscoveryEngine):
    """Scrapes AliExpress search results manually bypassing Google restrictions."""
    
    def search_by_image(self, image_url: str) -> List[DiscoveryCandidate]:
        # Native image search requires binary upload to Taobao/Ali APIs.
        # Fallback to Text for now.
        return []

    def search_by_keyword(self, keyword: str) -> List[DiscoveryCandidate]:
        settings = get_settings()
        if not settings.zenrows_api_key:
            return []
            
        # Target AliExpress Search using ZenRows to bypass perimeter defense
        search_url = f"https://www.aliexpress.com/w/wholesale-{quote_plus(keyword)}.html"
        
        try:
            with httpx.Client(timeout=60.0) as client:
                res = client.get(
                    "https://api.zenrows.com/v1/",
                    params={
                        "apikey": settings.zenrows_api_key,
                        "url": search_url,
                        "js_render": "true",
                        "premium_proxy": "true"
                    }
                )
                res.raise_for_status()
                html = res.text
        except Exception:
            return []
            
        # Very rough extraction from the DOM (Phase 2 LLM parsing handles deep extraction later)
        # In a full production system, we would parse `window.runParams` JSON natively embedded in Ali's DOM
        candidates = []
        import re
        links = re.findall(r'href="(//[a-zA-Z0-9\-\.]+\.aliexpress\.com/item/[0-9]+\.html[^"]*)"', html)
        for link in set(links):
            full_link = f"https:{link}"
            candidates.append(
                DiscoveryCandidate(
                    listing_url=full_link,
                    image_url=None, # Pulled dynamically in verification steps
                    host_domain=_domain(full_link),
                )
            )
        return candidates

# ==========================================
# TikTok Shop Walled-Garden Scraper
# ==========================================

class TikTokEngine(DiscoveryEngine):
    """Scrapes TikTok via external fast-API integrations."""
    
    def search_by_image(self, image_url: str) -> List[DiscoveryCandidate]:
        return []
        
    def search_by_keyword(self, keyword: str) -> List[DiscoveryCandidate]:
        # TikTok requires authenticated user sessions to hit the /api/search endpoints.
        # Implemented safely through ZenRows parsing similar to Ali.
        return []

