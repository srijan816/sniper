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
    if weights:
        notes.append(f"Recommended ensemble weights: siglip={weights[0]:.2f}, dinov2={weights[1]:.2f}, phash={weights[2]:.2f}")
    else:
        notes.append("Using default weights 0.45/0.35/0.20 (no explicit weights parsed from report)")

    if "siglip2" in report.lower() or "siglip 2" in report.lower():
        notes.append("Report confirms SigLIP 2 as primary encoder — matches current default model")

    if "dinov2" in report.lower():
        notes.append("Report confirms DINOv2 for structural matching — enabled in ensemble")

    if "0.92" in report or "0.93" in report:
        notes.append("Report mentions ~0.92-0.93 threshold range — review SIMILARITY_THRESHOLD env")

    _write_report_doc("vision-ensemble", "Vision Ensemble Research", report, job_id)
    return {"topic": "vision-ensemble", "notes": notes, "weights_detected": weights}


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


APPLY_HOOKS = {
    "vision-ensemble": apply_vision_ensemble_report,
    "discovery-multisource": apply_discovery_report,
    "takedown-automation": apply_takedown_report,
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
