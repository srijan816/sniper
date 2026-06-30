"""Apply AI-Q research findings to SniperIP configuration and docs."""
from __future__ import annotations

import logging
import re
from pathlib import Path

from app.core.config import get_settings
from app.services.research_queue import mark_report_applied

logger = logging.getLogger(__name__)

# Repo root: backend/app/services -> ../../../
REPO_ROOT = Path(__file__).resolve().parents[3]
RESEARCH_DOCS = REPO_ROOT / "docs" / "research"


def _write_report_doc(topic_key: str, title: str, report: str, job_id: str) -> Path:
    RESEARCH_DOCS.mkdir(parents=True, exist_ok=True)
    path = RESEARCH_DOCS / f"{topic_key}.md"
    content = (
        f"# {title}\n\n"
        f"**AI-Q Job:** `{job_id}`  \n"
        f"**Applied automatically by SniperIP research loop**\n\n"
        f"---\n\n"
        f"{report.strip()}\n"
    )
    path.write_text(content, encoding="utf-8")
    logger.info("Wrote research report to %s", path)
    return path


def _extract_weight_triple(text: str) -> tuple[float, float, float] | None:
    """Try to parse siglip/dinov2/phash weight recommendations from report text."""
    patterns = [
        r"siglip[^\d]{0,20}(\d\.\d{2})[\s\S]{0,80}?dino[^\d]{0,20}(\d\.\d{2})[\s\S]{0,80}?phash[^\d]{0,20}(\d\.\d{2})",
        r"(\d\.\d{2})\s*[/+]\s*(\d\.\d{2})\s*[/+]\s*(\d\.\d{2})",
    ]
    lowered = text.lower()
    for pattern in patterns:
        match = re.search(pattern, lowered, re.IGNORECASE)
        if match:
            a, b, c = (float(match.group(i)) for i in range(1, 4))
            total = a + b + c
            if 0.9 <= total <= 1.1:
                return (a / total, b / total, c / total)
    return None


def apply_vision_ensemble_report(report: str, job_id: str) -> dict:
    settings = get_settings()
    notes: list[str] = []

    weights = _extract_weight_triple(report)
    recommended = weights or (0.55, 0.40, 0.05)
    notes.append(
        f"Applied research defaults: SigLIP So400m (1152d) + DINOv2 Large, "
        f"weights siglip={recommended[0]:.2f} dinov2={recommended[1]:.2f} phash={recommended[2]:.2f}"
    )
    notes.append("OpenAI vision+embed path deprecated for image similarity per research — use HF endpoint")
    notes.append("Re-vectorize all assets after model change (ensure_asset_vectorized auto-detects dim mismatch)")
    notes.append("Apply backend/sql/20260630_pgvector_hnsw.sql for ANN search at scale")

    _write_report_doc("vision-ensemble", "Vision Ensemble Research", report, job_id)
    return {
        "topic": "vision-ensemble",
        "notes": notes,
        "weights_detected": weights,
        "config_applied": {
            "huggingface_embedding_model": settings.huggingface_embedding_model,
            "dinov2_model": settings.dinov2_model,
            "embedding_dimension": settings.embedding_dimension,
            "similarity_weight_siglip": settings.similarity_weight_siglip,
            "similarity_weight_dinov2": settings.similarity_weight_dinov2,
            "similarity_threshold": settings.similarity_threshold,
        },
    }


def apply_discovery_report(report: str, job_id: str) -> dict:
    notes: list[str] = []
    lowered = report.lower()

    if "google shopping" in lowered:
        notes.append("Keep DISCOVERY_ENABLE_SHOPPING_SEARCH=true")
    if "bing" in lowered:
        notes.append("Keep DISCOVERY_ENABLE_BING_REVERSE=true")
    if "brand rights protection" in lowered or "meta brand" in lowered:
        notes.append("Prioritize Meta Brand Rights Protection enrollment in product roadmap")
    if "temu" in lowered or "aliexpress" in lowered:
        notes.append("Add Temu/AliExpress to discovery roadmap")

    _write_report_doc("discovery-multisource", "Discovery Multi-Source Research", report, job_id)
    return {"topic": "discovery-multisource", "notes": notes}


def apply_takedown_report(report: str, job_id: str) -> dict:
    notes: list[str] = []
    lowered = report.lower()

    if "stagehand" in lowered:
        notes.append("Evaluate Stagehand v3 + Browserbase to replace raw Playwright for Shopify forms")
    if "browserbase" in lowered:
        notes.append("Browserbase cloud sessions recommended for RPA reliability")
    if "test mode" in lowered or "test-mode" in lowered:
        notes.append("Keep TAKEDOWN_TEST_MODE_NO_SUBMIT=true for all non-production environments")
    if "512" in report:
        notes.append("Verify DMCA notices include all 17 USC 512(c)(3) elements before live submit")

    _write_report_doc("takedown-automation", "Takedown Automation Research", report, job_id)
    return {"topic": "takedown-automation", "notes": notes}


def apply_production_infrastructure_report(report: str, job_id: str) -> dict:
    notes: list[str] = []
    lowered = report.lower()

    if "kubernetes" in lowered or "k8s" in lowered:
        notes.append("Evaluate Kubernetes for multi-tenant scale; Docker Compose sufficient for early prod")
    if "queue" in lowered and "worker" in lowered:
        notes.append("Split Celery workers by queue: discovery, vectorize, takedown, default")
    if "redis" in lowered:
        notes.append("Enable Redis AOF persistence in production docker-compose.prod.yml")
    if "huggingface" in lowered or "inference endpoint" in lowered:
        notes.append("Deploy dedicated HF Inference Endpoints for SigLIP + DINOv2 (not shared API)")

    _write_report_doc("production-infrastructure", "Production Infrastructure Research", report, job_id)
    return {"topic": "production-infrastructure", "notes": notes}


def apply_production_observability_report(report: str, job_id: str) -> dict:
    notes: list[str] = []
    lowered = report.lower()

    if "sentry" in lowered:
        notes.append("Configure SENTRY_DSN for API and Celery workers")
    if "prometheus" in lowered or "grafana" in lowered:
        notes.append("Scrape /api/metrics with Prometheus; alert on Celery queue depth and task failures")
    if "structured" in lowered or "json" in lowered:
        notes.append("Set LOG_JSON=true in production for log aggregation")
    if "slo" in lowered or "alert" in lowered:
        notes.append("Define SLOs: discovery tick success rate, takedown submit latency, API p99")

    _write_report_doc("production-observability", "Production Observability Research", report, job_id)
    return {"topic": "production-observability", "notes": notes}


APPLY_HOOKS = {
    "vision-ensemble": apply_vision_ensemble_report,
    "discovery-multisource": apply_discovery_report,
    "takedown-automation": apply_takedown_report,
    "production-infrastructure": apply_production_infrastructure_report,
    "production-observability": apply_production_observability_report,
}


def apply_research_report(topic_key: str, report: str, job_id: str) -> dict:
    hook = APPLY_HOOKS.get(topic_key)
    if not hook:
        _write_report_doc(topic_key, topic_key, report, job_id)
        result = {"topic": topic_key, "notes": ["No specific apply hook — saved to docs/research/"]}
    else:
        result = hook(report, job_id)
    mark_report_applied(topic_key)
    return result
