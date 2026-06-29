"""Brand intelligence worker — deep research via AI-Q (sequential, one job at a time)."""
from __future__ import annotations

import logging

from app.celery_app import celery_app
from app.core.database import get_supabase_client
from app.services.research_service import research_for_brand

logger = logging.getLogger(__name__)


def _db():
    db = get_supabase_client()
    if db is None:
        raise RuntimeError("Supabase is not configured.")
    return db


@celery_app.task(name="app.workers.research.run_brand_research")
def run_brand_research(client_id: str, product_category: str = "consumer goods"):
    """
    Run medium-depth AI-Q research for a brand and store results on the client record.
    Intended to run one at a time — do not fan out parallel research jobs.
    """
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
        logger.warning("Could not persist brand_research (column may be missing): %s", exc)
        return {"client_id": client_id, "status": "completed_unpersisted", "result": result}

    return {"client_id": client_id, "status": "completed", "job_id": result.get("job_id")}
