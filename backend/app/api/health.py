"""Health check endpoint with real dependency probing."""
import logging
import time

from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger(__name__)


def _probe_redis() -> dict:
    start = time.monotonic()
    try:
        from app.core.config import get_settings
        import redis
        settings = get_settings()
        r = redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
        r.ping()
        return {"status": "ok", "latency_ms": round((time.monotonic() - start) * 1000, 1)}
    except Exception as exc:
        logger.warning("Health probe: Redis unavailable: %s", exc)
        return {"status": "error", "error": str(exc)}


def _probe_supabase() -> dict:
    start = time.monotonic()
    try:
        from app.core.database import get_supabase_client
        db = get_supabase_client()
        if db is None:
            return {"status": "error", "error": "Supabase client not configured"}
        # Lightweight query — just check the connection
        db.table("clients").select("id").limit(1).execute()
        return {"status": "ok", "latency_ms": round((time.monotonic() - start) * 1000, 1)}
    except Exception as exc:
        logger.warning("Health probe: Supabase unavailable: %s", exc)
        return {"status": "error", "error": str(exc)}


@router.get("/health")
async def health_check():
    redis_probe = _probe_redis()
    supabase_probe = _probe_supabase()

    research_probe = _probe_research()

    all_ok = redis_probe["status"] == "ok" and supabase_probe["status"] == "ok"
    return {
        "status": "ok" if all_ok else "degraded",
        "service": "sniperip-api",
        "version": "1.0.0",
        "dependencies": {
            "redis": redis_probe,
            "supabase": supabase_probe,
            "research_queue": research_probe,
        },
    }


def _probe_research() -> dict:
    try:
        from app.services.research_queue import queue_status

        status = queue_status()
        active = status.get("active")
        return {
            "status": "ok",
            "active_topic": (active or {}).get("topic_key"),
            "active_job_id": (active or {}).get("aiq_job_id"),
            "queued_count": status.get("queue_length", 0),
            "completed_count": len(status.get("completed") or {}),
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
