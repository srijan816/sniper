"""Prometheus metrics for SniperIP API and Celery workers."""
from __future__ import annotations

import time

from prometheus_client import Counter, Histogram, generate_latest

HTTP_REQUESTS = Counter(
    "sniperip_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
HTTP_LATENCY = Histogram(
    "sniperip_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
CELERY_TASKS = Counter(
    "sniperip_celery_tasks_total",
    "Celery task executions",
    ["task", "status"],
)
CELERY_TASK_LATENCY = Histogram(
    "sniperip_celery_task_duration_seconds",
    "Celery task duration",
    ["task"],
    buckets=(0.1, 0.5, 1.0, 5.0, 15.0, 60.0, 300.0, 900.0),
)


def metrics_payload() -> bytes:
    return generate_latest()


def _normalize_path(path: str) -> str:
    """Collapse UUIDs and numeric IDs to keep cardinality low."""
    import re

    path = re.sub(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "{id}",
        path,
        flags=re.IGNORECASE,
    )
    return re.sub(r"/\d+", "/{id}", path)


def record_http_request(method: str, path: str, status: int, duration_s: float) -> None:
    norm = _normalize_path(path)
    HTTP_REQUESTS.labels(method=method, path=norm, status=str(status)).inc()
    HTTP_LATENCY.labels(method=method, path=norm).observe(duration_s)


def register_celery_metrics() -> None:
    """Hook Celery signals for task-level metrics."""
    from celery.signals import task_failure, task_postrun, task_prerun

    _starts: dict[str, float] = {}

    @task_prerun.connect
    def _on_prerun(sender=None, task_id=None, task=None, **kwargs):
        name = getattr(task, "name", str(sender))
        _starts[task_id or name] = time.monotonic()

    @task_postrun.connect
    def _on_postrun(sender=None, task_id=None, task=None, state=None, **kwargs):
        name = getattr(task, "name", str(sender))
        started = _starts.pop(task_id or name, None)
        if started is not None:
            CELERY_TASK_LATENCY.labels(task=name).observe(time.monotonic() - started)
        CELERY_TASKS.labels(task=name, status=state or "SUCCESS").inc()

    @task_failure.connect
    def _on_failure(sender=None, task_id=None, **kwargs):
        name = getattr(sender, "name", str(sender))
        CELERY_TASKS.labels(task=name, status="FAILURE").inc()
