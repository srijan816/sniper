"""AI-Q deep research integration for pipeline intelligence."""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def submit_research(query: str, *, depth: str = "deeper", agent_type: str = "deep_researcher") -> Optional[str]:
    """Submit async research job; returns job_id or None."""
    settings = get_settings()
    if not settings.aiq_api_token or not settings.aiq_base_url:
        return None

    url = f"{settings.aiq_base_url.rstrip('/')}/v1/jobs/async/submit"
    headers = {
        "Authorization": f"Bearer {settings.aiq_api_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "agent_type": agent_type,
        "input": query,
        "research_depth": depth,
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("job_id")
    except Exception as exc:
        logger.warning("Research submit failed: %s", exc)
        return None


def poll_research_report(job_id: str, *, timeout_seconds: int = 1200, poll_interval: int = 15) -> Optional[str]:
    """Poll until report is ready or timeout. Returns report text."""
    settings = get_settings()
    if not settings.aiq_api_token or not settings.aiq_base_url:
        return None

    base = settings.aiq_base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {settings.aiq_api_token}"}
    status_url = f"{base}/v1/jobs/async/job/{job_id}"
    report_url = f"{base}/v1/jobs/async/job/{job_id}/report"

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with httpx.Client(timeout=30.0) as client:
                status_resp = client.get(status_url, headers=headers)
                status_resp.raise_for_status()
                status_data = status_resp.json()
                if status_data.get("report_ready") or status_data.get("terminal"):
                    report_resp = client.get(report_url, headers=headers)
                    if report_resp.status_code == 200:
                        report_data = report_resp.json()
                        if isinstance(report_data, dict):
                            return report_data.get("report") or report_data.get("content") or str(report_data)
                        return str(report_data)
                    if status_data.get("status") == "failed":
                        logger.warning("Research job %s failed: %s", job_id, status_data.get("error"))
                        return None
                wait = int(status_data.get("poll_after_seconds") or poll_interval)
        except Exception as exc:
            logger.debug("Research poll error for %s: %s", job_id, exc)
            wait = poll_interval
        time.sleep(max(5, wait))

    logger.warning("Research job %s timed out after %ss", job_id, timeout_seconds)
    return None


def research_for_brand(brand_name: str, product_category: str = "consumer goods") -> Optional[dict[str, Any]]:
    """
    Run medium-depth research on counterfeit channels for a brand.
    Intended for onboarding / discovery tuning — not called on every scan.
    """
    query = (
        f"For the D2C brand '{brand_name}' selling {product_category}: "
        "where do counterfeit listings most commonly appear (Shopify, Amazon, Meta, TikTok, Temu, AliExpress)? "
        "What search keywords and image-search strategies work best? "
        "Return a short JSON-friendly summary with: top_platforms (list), keyword_queries (list), "
        "risk_signals (list), recommended_scan_frequency."
    )
    job_id = submit_research(query, depth="standard", agent_type="shallow_researcher")
    if not job_id:
        return None
    report = poll_research_report(job_id, timeout_seconds=900)
    if not report:
        return None
    return {"brand": brand_name, "job_id": job_id, "report": report}
