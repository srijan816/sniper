"""Tests for discovery orchestrator deduplication."""
from __future__ import annotations

from app.services.discovery_orchestrator import _dedupe_candidates
from app.services.serpapi_service import DiscoveryCandidate


def test_dedupe_candidates_by_url():
    candidates = [
        DiscoveryCandidate(listing_url="https://shop.example/a", image_url="http://img/1", host_domain="shop.example"),
        DiscoveryCandidate(listing_url="https://shop.example/a/", image_url="http://img/2", host_domain="shop.example"),
        DiscoveryCandidate(listing_url="https://other.example/b", image_url="http://img/3", host_domain="other.example"),
    ]
    result = _dedupe_candidates(candidates)
    assert len(result) == 2
    assert result[0].listing_url.startswith("https://shop.example")
