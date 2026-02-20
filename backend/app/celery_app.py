"""Celery application configuration"""
from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "sniperip",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.discovery",
        "app.workers.vectorize",
        "app.workers.takedown",
        "app.workers.notifications",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Retry policy
    task_default_retry_delay=60,
    task_max_retries=5,
    # Beat schedule for periodic discovery
    beat_schedule={
        "run-discovery-all-clients": {
            "task": "app.workers.discovery.run_discovery_all",
            "schedule": 3600.0,  # Every hour
        },
    },
)
