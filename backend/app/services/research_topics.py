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
    ResearchTopic(
        key="production-infrastructure",
        title="Production infrastructure for IP protection SaaS",
        query=(
            "For a Next.js + FastAPI + Celery + Redis + Supabase/pgvector IP protection SaaS in 2026: "
            "recommend production deployment architecture. Cover: Docker Compose vs Kubernetes vs Railway/Fly, "
            "Celery worker queue topology (discovery/vectorize/takedown split), Redis persistence and sizing, "
            "HuggingFace Inference Endpoints for SigLIP+DINOv2, Supabase scaling limits, health checks, "
            "zero-downtime deploys, secrets management, and cost estimates at 100 vs 1000 clients."
        ),
    ),
    ResearchTopic(
        key="production-observability",
        title="Production observability and alerting",
        query=(
            "For a FastAPI + Celery SaaS running counterfeit detection pipelines in 2026: "
            "compare observability stacks (Sentry + Prometheus/Grafana vs Datadog vs OpenTelemetry). "
            "Recommend: structured logging format, key Prometheus metrics (HTTP, Celery tasks, discovery latency, "
            "embedding inference latency, queue depth), SLOs and alerting rules, error budgets, "
            "on-call runbooks for takedown failures and discovery stalls."
        ),
    ),
)

TOPICS_BY_KEY = {t.key: t for t in PIPELINE_TOPICS}
