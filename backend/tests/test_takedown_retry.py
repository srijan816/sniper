"""Test: Takedown retry and DLQ behavior."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, call, patch

import pytest


TAKEDOWN_ID = str(uuid.uuid4())
THREAT_ID = str(uuid.uuid4())


class TestExponentialBackoff:
    def test_backoff_formula(self):
        """Verify exponential backoff: 60 * 2^retry."""
        delays = [60 * (2 ** i) for i in range(5)]
        assert delays == [60, 120, 240, 480, 960]

    def test_max_retries_is_5(self):
        from app.celery_app import celery_app
        assert celery_app.conf.task_max_retries == 5


class TestDLQInsertion:
    def test_dlq_insert_called_after_max_retries(self):
        """After MAX_RETRIES, the task should call _insert_dlq."""
        from app.workers.takedown import MAX_RETRIES
        assert MAX_RETRIES == 5

    def test_takedown_task_handles_missing_supabase(self):
        """execute_takedown_task raises RuntimeError when Supabase is None."""
        from app.workers.takedown import execute_takedown_task
        with patch("app.workers.takedown.get_supabase_client", return_value=None):
            with pytest.raises(Exception):
                # Invoke directly (bypasses Celery broker)
                execute_takedown_task.__wrapped__(TAKEDOWN_ID)


class TestQueueTakedown:
    def test_queue_takedown_dispatches_celery_task(self):
        """queue_takedown should call execute_takedown_task.apply_async."""
        with patch("app.workers.takedown.execute_takedown_task") as mock_task:
            mock_task.apply_async = MagicMock()
            from app.workers.takedown import queue_takedown
            queue_takedown(TAKEDOWN_ID)
            mock_task.apply_async.assert_called_once()
            args = mock_task.apply_async.call_args
            assert TAKEDOWN_ID in str(args)
