"""Research workers — sequential AI-Q queue with poll/apply loop."""
from __future__ import annotations

import logging

from app.celery_app import celery_app
from app.core.database import get_supabase_client
from app.services.research_apply import apply_research_report
from app.services.research_queue import (
    clear_active_job,
    enqueue_defaults,
    get_active_job,
    get_report,
    pop_next_topic,
    save_report,
    set_active_job,
    start_topic,
)
from app.services.research_service import fetch_report, get_job_status, research_for_brand
from app.services.research_topics import TOPICS_BY_KEY

logger = logging.getLogger(__name__)


def _db():
    db = get_supabase_client()
    if db is None:
        raise RuntimeError("Supabase is not configured.")
    return db


def _complete_active(job_id: str, report: str) -> dict:
    active = get_active_job() or {}
    topic_key = active.get("topic_key", "unknown")
    save_report(topic_key, report, job_id=job_id, status="completed")
    apply_result = apply_research_report(topic_key, report, job_id)
    clear_active_job()
    logger.info("Research completed: topic=%s job_id=%s", topic_key, job_id)
    return {"status": "completed", "topic_key": topic_key, "job_id": job_id, "apply": apply_result}


def _fail_active(reason: str) -> dict:
    active = get_active_job() or {}
    topic_key = active.get("topic_key")
    job_id = active.get("aiq_job_id")
    if topic_key and job_id:
        save_report(topic_key, f"FAILED: {reason}", job_id=job_id, status="failed")
    clear_active_job()
    return {"status": "failed", "topic_key": topic_key, "reason": reason}


def _start_next_queued() -> dict | None:
    next_key = pop_next_topic()
    if not next_key:
        return None
    topic = TOPICS_BY_KEY[next_key]
    started = start_topic(topic)
    return {"status": "started", "topic_key": next_key, "aiq_job_id": started.get("aiq_job_id")}


@celery_app.task(name="app.workers.research.research_queue_tick")
def research_queue_tick():
    """
    Poll loop hook — runs every 2 minutes via Celery beat.
    1. Poll active AI-Q job if any
    2. On completion: save report, apply findings, start next queued topic
    3. If idle and queue non-empty: start next topic
    """
    active = get_active_job()

    if active:
        job_id = active.get("aiq_job_id")
        if not job_id:
            _fail_active("missing aiq_job_id")
            nxt = _start_next_queued()
            return {"action": "failed_and_advanced", "next": nxt}

        status = get_job_status(job_id)
        if not status:
            return {"action": "poll_skipped", "reason": "status_unavailable", "active": active}

        if status.get("report_ready"):
            report = fetch_report(job_id)
            if report:
                result = _complete_active(job_id, report)
                nxt = _start_next_queued()
                return {"action": "completed", "result": result, "next": nxt}
            _fail_active("report_ready but empty")
            nxt = _start_next_queued()
            return {"action": "failed_empty_report", "next": nxt}

        if status.get("terminal"):
            error = status.get("error") or status.get("status") or "terminal without report"
            _fail_active(str(error))
            nxt = _start_next_queued()
            return {"action": "failed_terminal", "error": error, "next": nxt}

        return {
            "action": "polling",
            "topic_key": active.get("topic_key"),
            "aiq_job_id": job_id,
            "aiq_status": status.get("status"),
        }

    # No active job — start next from queue if pending
    nxt = _start_next_queued()
    if nxt:
        return {"action": "started", **nxt}
    return {"action": "idle", "queue_empty": True}


@celery_app.task(name="app.workers.research.seed_research_queue")
def seed_research_queue():
    """Seed default pipeline topics (skips already-completed)."""
    added = enqueue_defaults(skip_completed=True)
    return {"added": added}


@celery_app.task(name="app.workers.research.adopt_research_job")
def adopt_research_job(topic_key: str, aiq_job_id: str):
    """Adopt an externally submitted AI-Q job into the pipeline tracker."""
    from app.services.research_queue import adopt_external_job

    payload = adopt_external_job(topic_key, aiq_job_id)
    return {"status": "adopted", "active": payload}


@celery_app.task(name="app.workers.research.run_brand_research")
def run_brand_research(client_id: str, product_category: str = "consumer goods"):
    """Brand-specific research (separate from pipeline queue — uses blocking poll)."""
    rows = _db().table("clients").select("id,company_name,brand_research").eq("id", client_id).limit(1).execute().data or []
    if not rows:
        raise RuntimeError(f"Client {client_id} not found.")
    client = rows[0]
    brand_name = client.get("company_name") or "Unknown brand"

    if client.get("brand_research"):
        return {"client_id": client_id, "status": "skipped", "reason": "already_researched"}

    result = research_for_brand(brand_name, product_category)
    if not result:
        return {"client_id": client_id, "status": "failed", "reason": "research_unavailable"}

    try:
        _db().table("clients").update({"brand_research": result}).eq("id", client_id).execute()
    except Exception as exc:
        logger.warning("Could not persist brand_research: %s", exc)
        return {"client_id": client_id, "status": "completed_unpersisted", "result": result}

    return {"client_id": client_id, "status": "completed", "job_id": result.get("job_id")}
