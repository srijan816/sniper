"""Notification delivery (Resend + Slack)."""
from __future__ import annotations

import resend
from slack_sdk.webhook import WebhookClient

from app.core.config import get_settings


def send_upgrade_email(client_email: str, client_name: str) -> None:
    settings = get_settings()
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY is required to send email notifications.")

    resend.api_key = settings.resend_api_key
    resend.Emails.send(
        {
            "from": settings.notification_from_email,
            "to": [client_email],
            "subject": "Monthly takedown limit reached",
            "html": (
                f"<p>Hi {client_name},</p>"
                "<p>You reached your monthly threat limit in SniperIP.</p>"
                "<p>Upgrade your plan to continue automatic discovery and enforcement.</p>"
            ),
        }
    )


def send_threat_digest(client_email: str, threats_count: int, revenue_protected: float) -> None:
    settings = get_settings()
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY is required to send email notifications.")
    resend.api_key = settings.resend_api_key
    resend.Emails.send(
        {
            "from": settings.notification_from_email,
            "to": [client_email],
            "subject": f"SniperIP digest: {threats_count} threats, ${revenue_protected:,.0f} protected",
            "html": (
                "<p>Your latest SniperIP summary:</p>"
                f"<ul><li>Threats found: {threats_count}</li>"
                f"<li>Estimated revenue protected: ${revenue_protected:,.0f}</li></ul>"
            ),
        }
    )


def send_takedown_confirmation(
    client_email: str,
    threat_url: str,
    platform: str,
    case_number: str,
) -> None:
    settings = get_settings()
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY is required to send email notifications.")
    resend.api_key = settings.resend_api_key
    resend.Emails.send(
        {
            "from": settings.notification_from_email,
            "to": [client_email],
            "subject": f"Takedown submitted ({platform})",
            "html": (
                "<p>Your takedown was submitted.</p>"
                f"<p>Case number: <strong>{case_number}</strong></p>"
                f"<p>Infringing URL: <a href=\"{threat_url}\">{threat_url}</a></p>"
            ),
        }
    )


def send_generic_dmca_notice(
    to_emails: list[str],
    subject: str,
    html: str,
    cc_emails: list[str] | None = None,
) -> None:
    settings = get_settings()
    if not settings.resend_api_key:
        raise RuntimeError("RESEND_API_KEY is required to send email notifications.")
    if not to_emails:
        raise RuntimeError("At least one recipient email is required for DMCA notice delivery.")

    resend.api_key = settings.resend_api_key
    payload = {
        "from": settings.notification_from_email,
        "to": to_emails,
        "subject": subject,
        "html": html,
    }
    if cc_emails:
        payload["cc"] = cc_emails
    resend.Emails.send(payload)


def send_slack_alert(message: str) -> None:
    settings = get_settings()
    if not settings.slack_webhook_url:
        raise RuntimeError("SLACK_WEBHOOK_URL is required for Slack alerts.")
    webhook = WebhookClient(settings.slack_webhook_url)
    response = webhook.send(text=message)
    if response.status_code >= 400:
        raise RuntimeError(f"Slack webhook failed: {response.status_code} {response.body}")
