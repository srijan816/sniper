"""Sequential research queue — one AI-Q job at a time (Redis with file fallback)."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.core.config import get_settings
from app.services.research_topics import PIPELINE_TOPICS, TOPICS_BY_KEY, ResearchTopic

logger = logging.getLogger(__name__)

REDIS_ACTIVE = "sniperip:research:active"
REDIS_QUEUE = "sniperip:research:queue"
REDIS_REPORT_PREFIX = "sniperip:research:report:"

FILE_STATE = Path(__file__).resolve().parents[2] / ".research-queue-state.json"


class _FileBackend:
    def __init__(self):
        self._data: dict[str, Any] = {"active": None, "queue": [], "reports": {}}
        self._load()

    def _load(self):
        if FILE_STATE.exists():
            try:
                self._data = json.loads(FILE_STATE.read_text(encoding="utf-8"))
            except Exception:
                pass

    def _save(self):
        FILE_STATE.parent.mkdir(parents=True, exist_ok=True)
        FILE_STATE.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def get_active(self) -> Optional[dict]:
        return self._data.get("active")

    def set_active(self, payload: Optional[dict]):
        self._data["active"] = payload
        self._save()

    def list_queue(self) -> list[str]:
        return list(self._data.get("queue") or [])

    def enqueue(self, key: str, front: bool):
        q = self._data.setdefault("queue", [])
        if front:
            q.insert(0, key)
        else:
            q.append(key)
        self._save()

    def pop(self) -> Optional[str]:
        q = self._data.get("queue") or []
        if not q:
            return None
        val = q.pop(0)
        self._data["queue"] = q
        self._save()
        return val

    def save_report(self, key: str, payload: dict):
        self._data.setdefault("reports", {})[key] = payload
        self._save()

    def get_report(self, key: str) -> Optional[dict]:
        return (self._data.get("reports") or {}).get(key)


_file_backend: _FileBackend | None = None
_use_file = False


def _get_file_backend() -> _FileBackend:
    global _file_backend
    if _file_backend is None:
        _file_backend = _FileBackend()
    return _file_backend


def _redis():
    import redis

    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)


def _using_file() -> bool:
    global _use_file
    if _use_file:
        return True
    try:
        _redis().ping()
        return False
    except Exception:
        _use_file = True
        logger.info("Redis unavailable — using file-backed research queue at %s", FILE_STATE)
        return True


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_active_job() -> Optional[dict[str, Any]]:
    try:
        if _using_file():
            return _get_file_backend().get_active()
        raw = _redis().get(REDIS_ACTIVE)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.warning("Failed to read active research job: %s", exc)
        return None


def set_active_job(payload: dict[str, Any]) -> None:
    if _using_file():
        _get_file_backend().set_active(payload)
        return
    _redis().set(REDIS_ACTIVE, json.dumps(payload))


def clear_active_job() -> None:
    if _using_file():
        _get_file_backend().set_active(None)
        return
    _redis().delete(REDIS_ACTIVE)


def queue_length() -> int:
    if _using_file():
        return len(_get_file_backend().list_queue())
    return int(_redis().llen(REDIS_QUEUE))


def list_queue() -> list[str]:
    if _using_file():
        return _get_file_backend().list_queue()
    return _redis().lrange(REDIS_QUEUE, 0, -1) or []


def enqueue_topic(topic_key: str, *, front: bool = False) -> bool:
    if topic_key not in TOPICS_BY_KEY:
        raise ValueError(f"Unknown research topic: {topic_key}")
    if topic_key in list_queue():
        return False
    active = get_active_job()
    if active and active.get("topic_key") == topic_key:
        return False
    if _using_file():
        _get_file_backend().enqueue(topic_key, front)
    elif front:
        _redis().lpush(REDIS_QUEUE, topic_key)
    else:
        _redis().rpush(REDIS_QUEUE, topic_key)
    return True


def enqueue_defaults(skip_completed: bool = True) -> list[str]:
    added: list[str] = []
    active = get_active_job()
    active_key = (active or {}).get("topic_key")
    for topic in PIPELINE_TOPICS:
        if skip_completed and get_report(topic.key):
            continue
        if active_key == topic.key:
            continue
        if enqueue_topic(topic.key):
            added.append(topic.key)
    return added


def pop_next_topic() -> Optional[str]:
    if _using_file():
        return _get_file_backend().pop()
    return _redis().lpop(REDIS_QUEUE) or None


def save_report(topic_key: str, report: str, *, job_id: str, status: str = "completed") -> dict[str, Any]:
    payload = {
        "topic_key": topic_key,
        "job_id": job_id,
        "status": status,
        "report": report,
        "saved_at": _utcnow(),
        "applied": False,
    }
    if _using_file():
        _get_file_backend().save_report(topic_key, payload)
    else:
        _redis().set(f"{REDIS_REPORT_PREFIX}{topic_key}", json.dumps(payload))
    return payload


def get_report(topic_key: str) -> Optional[dict[str, Any]]:
    if _using_file():
        return _get_file_backend().get_report(topic_key)
    raw = _redis().get(f"{REDIS_REPORT_PREFIX}{topic_key}")
    return json.loads(raw) if raw else None


def mark_report_applied(topic_key: str) -> None:
    data = get_report(topic_key)
    if not data:
        return
    data["applied"] = True
    data["applied_at"] = _utcnow()
    if _using_file():
        _get_file_backend().save_report(topic_key, data)
    else:
        _redis().set(f"{REDIS_REPORT_PREFIX}{topic_key}", json.dumps(data))


def queue_status() -> dict[str, Any]:
    active = get_active_job()
    reports = {}
    for topic in PIPELINE_TOPICS:
        rep = get_report(topic.key)
        if rep:
            reports[topic.key] = {
                "status": rep.get("status"),
                "applied": rep.get("applied"),
                "saved_at": rep.get("saved_at"),
                "job_id": rep.get("job_id"),
                "report_preview": (rep.get("report") or "")[:200],
            }
    return {
        "active": active,
        "queued": list_queue(),
        "queue_length": queue_length(),
        "completed": reports,
        "topics": [{"key": t.key, "title": t.title} for t in PIPELINE_TOPICS],
        "backend": "file" if _using_file() else "redis",
        "state_file": str(FILE_STATE) if _using_file() else None,
    }


def _assert_no_active_job() -> None:
    active = get_active_job()
    if active:
        raise RuntimeError(
            f"Research job already active: topic={active.get('topic_key')} "
            f"job_id={active.get('aiq_job_id')}"
        )


def adopt_external_job(topic_key: str, job_id: str) -> dict[str, Any]:
    if topic_key not in TOPICS_BY_KEY:
        raise ValueError(f"Unknown topic: {topic_key}")
    _assert_no_active_job()
    payload = {
        "id": str(uuid.uuid4()),
        "topic_key": topic_key,
        "aiq_job_id": job_id,
        "status": "running",
        "started_at": _utcnow(),
        "adopted": True,
    }
    set_active_job(payload)
    return payload


def start_topic(topic: ResearchTopic) -> dict[str, Any]:
    from app.services.research_service import submit_research

    _assert_no_active_job()
    job_id = submit_research(topic.query, depth=topic.depth, agent_type=topic.agent_type)
    if not job_id:
        raise RuntimeError(f"Failed to submit research for topic {topic.key}")

    payload = {
        "id": str(uuid.uuid4()),
        "topic_key": topic.key,
        "title": topic.title,
        "aiq_job_id": job_id,
        "status": "running",
        "started_at": _utcnow(),
    }
    set_active_job(payload)
    logger.info("Research started: topic=%s job_id=%s", topic.key, job_id)
    return payload
