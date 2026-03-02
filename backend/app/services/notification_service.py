"""Notification delivery (Resend + Slack + per-client webhooks)."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time

import httpx
import resend
from slack_sdk.webhook import WebhookClient

from app.core.config import get_settings

logger = logging.getLogger(__name__)


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


# ── Per-client notification dispatch (Feature 8) ─────────────────────────────

def _send_client_slack(
    slack_webhook_url: str,
    event_type: str,
    title: str,
    message: str,
    details: dict | None = None,
) -> None:
    """Send a Slack Block Kit message to a client's webhook URL."""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"SniperIP: {title}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": message},
        },
    ]
    if details:
        fields = [{"type": "mrkdwn", "text": f"*{k}:*\n{v}"} for k, v in details.items()]
        blocks.append({"type": "section", "fields": fields[:10]})
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"Event: `{event_type}` • <https://sniperip.com/dashboard|Open Dashboard>"}],
    })

    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(slack_webhook_url, json={"blocks": blocks})
            if r.status_code >= 400:
                logger.warning("Client Slack webhook returned %d", r.status_code)
    except Exception as exc:
        logger.warning("Failed to send client Slack notification: %s", exc)


def _send_client_webhook(
    webhook_url: str,
    webhook_secret: str | None,
    event_type: str,
    payload: dict,
) -> None:
    """POST event payload to client's generic webhook with HMAC signature."""
    body = json.dumps({"event_type": event_type, "timestamp": int(time.time()), "data": payload}).encode()
    headers = {"Content-Type": "application/json", "X-SniperIP-Event": event_type}
    if webhook_secret:
        sig = hmac.new(webhook_secret.encode(), body, hashlib.sha256).hexdigest()
        headers["X-SniperIP-Signature"] = f"sha256={sig}"
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(webhook_url, content=body, headers=headers)
            if r.status_code >= 400:
                logger.warning("Client webhook returned %d for event %s", r.status_code, event_type)
    except Exception as exc:
        logger.warning("Failed to send client webhook for event %s: %s", event_type, exc)


def dispatch_client_notification(
    client: dict,
    event_type: str,
    title: str,
    email_subject: str,
    email_html: str,
    slack_message: str,
    slack_details: dict | None = None,
    webhook_payload: dict | None = None,
) -> None:
    """
    Dispatch a notification to all configured channels for a client.
    event_type examples: 'threat.discovered', 'takedown.completed', 'takedown.reinstated', 'quota.warning'
    """
    prefs = client.get("notification_prefs") or {}

    # Email (always on unless explicitly disabled for this event)
    email = client.get("legal_contact_email")
    if email and prefs.get(event_type, {}).get("email", True):
        try:
            settings = get_settings()
            if settings.resend_api_key:
                resend.api_key = settings.resend_api_key
                resend.Emails.send({
                    "from": settings.notification_from_email,
                    "to": [email],
                    "subject": email_subject,
                    "html": email_html,
                })
        except Exception as exc:
            logger.warning("Failed to send notification email for event %s: %s", event_type, exc)

    # Slack (if client has configured their own webhook)
    slack_url = client.get("slack_webhook_url")
    if slack_url and prefs.get(event_type, {}).get("slack", True):
        _send_client_slack(slack_url, event_type, title, slack_message, slack_details)

    # Generic webhook
    wh_url = client.get("webhook_url")
    if wh_url and prefs.get(event_type, {}).get("webhook", True):
        _send_client_webhook(
            wh_url,
            client.get("webhook_secret"),
            event_type,
            webhook_payload or {"message": slack_message},
        )


def send_reinstatement_alert(
    client: dict,
    infringing_url: str,
    takedown_id: str,
    domain: str,
) -> None:
    """Notify client when a previously taken-down listing is detected as reinstated."""
    dashboard_url = "https://sniperip.com/dashboard"
    legal_url = "https://sniperip.com/dashboard/legal-partners"
    html = (
        f"<p>Hi {client.get('company_name', 'there')},</p>"
        f"<p>Our monitoring system detected that a listing at <strong>{domain}</strong> "
        "appears to be back online after a previous takedown.</p>"
        "<p>This may indicate that the infringing party filed a DMCA counter-notice. "
        "Under 17 U.S.C. §512(g), platforms must reinstate content within 10-14 business days "
        "unless you file a federal lawsuit.</p>"
        "<p><strong>Your options:</strong></p>"
        "<ul>"
        f"<li><a href='{dashboard_url}/threats'>Re-submit Takedown</a> — file a new takedown against the reinstated listing</li>"
        f"<li><a href='{legal_url}'>Consult Legal Counsel</a> — our partner IP attorneys can advise on counter-notice litigation</li>"
        "</ul>"
        f"<p>Infringing URL: <a href='{infringing_url}'>{infringing_url}</a></p>"
    )
    dispatch_client_notification(
        client=client,
        event_type="takedown.reinstated",
        title="Takedown Reversed",
        email_subject=f"Alert: Takedown Reversed — {domain} may be back online",
        email_html=html,
        slack_message=f":rotating_light: *Takedown Reversed*\n{domain} appears to be back online. Possible counter-notice filed.",
        slack_details={"Domain": domain, "URL": infringing_url[:80]},
        webhook_payload={"infringing_url": infringing_url, "domain": domain, "takedown_id": takedown_id},
    )


def send_threat_discovered_notification(client: dict, threat_count: int, platform: str) -> None:
    """Notify client when new threats are discovered during a discovery scan."""
    dispatch_client_notification(
        client=client,
        event_type="threat.discovered",
        title="New Threats Detected",
        email_subject=f"SniperIP: {threat_count} new threat(s) detected",
        email_html=(
            f"<p>Hi {client.get('company_name', 'there')},</p>"
            f"<p>SniperIP detected <strong>{threat_count} new suspected counterfeit listing(s)</strong> "
            f"on {platform}.</p>"
            "<p>Log in to review and approve enforcement actions.</p>"
            "<p><a href='https://sniperip.com/dashboard/threats'>View Threats →</a></p>"
        ),
        slack_message=f":shield: *{threat_count} new threat(s) detected* on {platform}. <https://sniperip.com/dashboard/threats|Review now>",
        slack_details={"Platform": platform, "Count": str(threat_count)},
        webhook_payload={"threat_count": threat_count, "platform": platform},
    )
