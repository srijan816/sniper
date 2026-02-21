"""Celery notification tasks."""
from app.celery_app import celery_app
from app.services.notification_service import (
    send_slack_alert as send_slack_alert_service,
    send_threat_digest as send_threat_digest_service,
    send_takedown_confirmation as send_takedown_confirmation_service,
    send_upgrade_email as send_upgrade_email_service,
)


@celery_app.task(name="app.workers.notifications.send_upgrade_email")
def send_upgrade_email(client_email: str, client_name: str):
    send_upgrade_email_service(client_email, client_name)
    return {"status": "sent", "to": client_email}


@celery_app.task(name="app.workers.notifications.send_threat_digest")
def send_threat_digest(client_email: str, threats_count: int, revenue_protected: float):
    send_threat_digest_service(client_email, threats_count, revenue_protected)
    return {"status": "sent", "to": client_email}


@celery_app.task(name="app.workers.notifications.send_slack_alert")
def send_slack_alert(message: str, channel: str = "admin-alerts"):
    del channel  # single webhook destination
    send_slack_alert_service(message)
    return {"status": "sent"}


@celery_app.task(name="app.workers.notifications.send_takedown_confirmation")
def send_takedown_confirmation(client_email: str, threat_url: str, platform: str, case_number: str):
    send_takedown_confirmation_service(client_email, threat_url, platform, case_number)
    return {"status": "sent", "to": client_email}
