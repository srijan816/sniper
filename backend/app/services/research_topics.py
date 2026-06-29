"""Predefined AI-Q research topics for the sequential pipeline queue."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchTopic:
    key: str
    title: str
    query: str
    depth: str = "deeper"
    agent_type: str = "deep_researcher"


# Default pipeline research queue — processed one at a time, in order.
PIPELINE_TOPICS: tuple[ResearchTopic, ...] = (
    ResearchTopic(
        key="vision-ensemble",
        title="Vision ensemble for counterfeit detection",
        query=(
            "For an automated IP protection SaaS detecting counterfeit product listings via image similarity: "
            "compare SigLIP 2 vs DINOv2 vs CLIP vs OpenAI vision+text-embedding for production in 2026. "
            "Recommend: best HuggingFace model IDs, ensemble scoring formula and weights, inference deployment "
            "(HF endpoint vs Replicate vs local GPU), latency/cost tradeoffs, pgvector dimensions, and "
            "similarity threshold calibration for false positive reduction in e-commerce."
        ),
    ),
    ResearchTopic(
        key="discovery-multisource",
        title="Multi-source discovery architecture",
        query=(
            "For a brand protection SaaS monitoring Shopify, Amazon, Meta, TikTok, eBay for D2C brands: "
            "best multi-source discovery architecture in 2026 beyond Google Lens/SerpApi alone. "
            "Compare SerpApi Google Lens, Bing reverse image, Google Shopping keyword search, Amazon Brand Registry, "
            "Meta Brand Rights Protection. Recommend orchestration, deduplication, cost control, ROI ranking."
        ),
    ),
    ResearchTopic(
        key="takedown-automation",
        title="Takedown automation reliability",
        query=(
            "For automating DMCA/copyright takedowns on Shopify (no public API), Meta IP Reporting API, "
            "Amazon Brand Registry, generic WHOIS abuse in 2026: compare Playwright RPA vs Stagehand v3 vs Browserbase. "
            "What breaks most often, self-healing strategies, 17 USC 512 notice requirements, test-mode patterns."
        ),
    ),
)

TOPICS_BY_KEY = {t.key: t for t in PIPELINE_TOPICS}
