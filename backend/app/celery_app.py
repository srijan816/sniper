"""Celery application configuration"""
from celery import Celery

from app.core.config import get_settings
from app.core.logging_config import configure_logging, init_sentry
from app.core.metrics import register_celery_metrics

configure_logging()
init_sentry()
register_celery_metrics()

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
        "app.workers.monitoring",
        "app.workers.research",
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
    task_default_queue="default",
    task_routes={
        "app.workers.discovery.run_discovery_tick": {"queue": "discovery"},
        "app.workers.discovery.run_discovery_all": {"queue": "discovery"},
        "app.workers.discovery.run_discovery_for_client": {"queue": "discovery"},
        "app.workers.vectorize.vectorize_asset_task": {"queue": "vectorize"},
        "app.workers.takedown.execute_takedown_task": {"queue": "takedown"},
        "app.workers.notifications.send_upgrade_email": {"queue": "notifications"},
        "app.workers.notifications.send_threat_digest": {"queue": "notifications"},
        "app.workers.notifications.send_slack_alert": {"queue": "notifications"},
        "app.workers.notifications.send_takedown_confirmation": {"queue": "notifications"},
        "app.workers.research.run_brand_research": {"queue": "default"},
        "app.workers.research.research_queue_tick": {"queue": "default"},
        "app.workers.research.seed_research_queue": {"queue": "default"},
    },
    # Retry policy
    task_default_retry_delay=60,
    task_max_retries=5,
    # Beat schedule: rotate through clients one-by-one every 15 min to smooth load
    beat_schedule={
        "run-discovery-tick": {
            "task": "app.workers.discovery.run_discovery_tick",
            "schedule": 900.0,  # 15 minutes — processes one client per tick
        },
        "check-takedown-persistence": {
            "task": "app.workers.monitoring.check_takedown_persistence",
            "schedule": 86400.0,  # daily — poll completed takedowns for reinstatement
        },
        "research-queue-tick": {
            "task": "app.workers.research.research_queue_tick",
            "schedule": float(settings.research_poll_interval_seconds or 120),
        },
    },
)
