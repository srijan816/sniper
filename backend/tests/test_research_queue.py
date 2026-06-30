"""Tests for sequential research queue."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.research_queue import (
    clear_active_job,
    enqueue_topic,
    get_active_job,
    list_queue,
    queue_status,
    save_report,
)


@pytest.fixture(autouse=True)
def clean_redis_queue():
    """Clear queue keys before each test."""
    import app.services.research_queue as rq

    rq._use_file = False
    mock_redis = MagicMock()
    store: dict[str, str] = {}
    lists: dict[str, list] = {"sniperip:research:queue": []}

    def get(key):
        return store.get(key)

    def set_(key, val):
        store[key] = val

    def delete(key):
        store.pop(key, None)

    def lrange(key, start, end):
        return lists.get(key, [])[start : end + 1 if end >= 0 else None]

    def rpush(key, val):
        lists.setdefault(key, []).append(val)

    def lpop(key):
        q = lists.get(key, [])
        return q.pop(0) if q else None

    def llen(key):
        return len(lists.get(key, []))

    mock_redis.get.side_effect = get
    mock_redis.set.side_effect = set_
    mock_redis.delete.side_effect = delete
    mock_redis.lrange.side_effect = lrange
    mock_redis.rpush.side_effect = rpush
    mock_redis.lpop.side_effect = lpop
    mock_redis.llen.side_effect = llen
    mock_redis.ping.return_value = True

    with patch("app.services.research_queue._redis", return_value=mock_redis):
        clear_active_job()
        yield mock_redis


def test_enqueue_and_status():
    assert enqueue_topic("discovery-multisource") is True
    assert enqueue_topic("discovery-multisource") is False  # duplicate
    assert "discovery-multisource" in list_queue()
    status = queue_status()
    assert status["queue_length"] == 1


def test_save_report():
    save_report("vision-ensemble", "Test report body", job_id="job-123")
    status = queue_status()
    assert "vision-ensemble" in status["completed"]
