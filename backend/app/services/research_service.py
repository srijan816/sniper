"""Research service — AI-Q API client (submit, poll, fetch)."""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "Authorization": f"Bearer {settings.aiq_api_token}",
        "Content-Type": "application/json",
    }


def _base_url() -> str:
    return get_settings().aiq_base_url.rstrip("/")


def is_configured() -> bool:
    s = get_settings()
    return bool(s.aiq_api_token and s.aiq_base_url)


def submit_research(query: str, *, depth: str = "deeper", agent_type: str = "deep_researcher") -> Optional[str]:
    """Submit async research job; returns job_id or None."""
    if not is_configured():
        return None

    url = f"{_base_url()}/v1/jobs/async/submit"
    payload = {"agent_type": agent_type, "input": query, "research_depth": depth}
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=_headers(), json=payload)
            response.raise_for_status()
            return response.json().get("job_id")
    except Exception as exc:
        logger.warning("Research submit failed: %s", exc)
        return None


def get_job_status(job_id: str) -> Optional[dict[str, Any]]:
    if not is_configured():
        return None
    url = f"{_base_url()}/v1/jobs/async/job/{job_id}"
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers={"Authorization": _headers()["Authorization"]})
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        logger.warning("Research status check failed for %s: %s", job_id, exc)
        return None


def fetch_report(job_id: str) -> Optional[str]:
    if not is_configured():
        return None
    url = f"{_base_url()}/v1/jobs/async/job/{job_id}/report"
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.get(url, headers={"Authorization": _headers()["Authorization"]})
            if response.status_code != 200:
                return None
            data = response.json()
            if isinstance(data, dict):
                return data.get("report") or data.get("content") or data.get("markdown") or str(data)
            return str(data)
    except Exception as exc:
        logger.warning("Research report fetch failed for %s: %s", job_id, exc)
        return None


def poll_research_report(job_id: str, *, timeout_seconds: int = 1200, poll_interval: int = 15) -> Optional[str]:
    """Blocking poll until report ready (for brand research one-shots)."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        status = get_job_status(job_id)
        if not status:
            time.sleep(poll_interval)
            continue
        if status.get("report_ready"):
            return fetch_report(job_id)
        if status.get("terminal") and not status.get("report_ready"):
            logger.warning("Research job %s ended without report: %s", job_id, status.get("error"))
            return None
        wait = int(status.get("poll_after_seconds") or poll_interval)
        time.sleep(max(5, wait))
    logger.warning("Research job %s timed out after %ss", job_id, timeout_seconds)
    return None


def research_for_brand(brand_name: str, product_category: str = "consumer goods") -> Optional[dict[str, Any]]:
    query = (
        f"For the D2C brand '{brand_name}' selling {product_category}: "
        "where do counterfeit listings most commonly appear? "
        "Return JSON-friendly summary: top_platforms, keyword_queries, risk_signals, recommended_scan_frequency."
    )
    job_id = submit_research(query, depth="standard", agent_type="shallow_researcher")
    if not job_id:
        return None
    report = poll_research_report(job_id, timeout_seconds=900)
    if not report:
        return None
    return {"brand": brand_name, "job_id": job_id, "report": report}
