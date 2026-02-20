"""Notification services — Resend emails, Slack webhooks"""
from app.core.config import get_settings


def send_upgrade_email(client_email: str, client_name: str):
    """
    Send quota limit upgrade email via Resend.
    
    Triggered when client hits monthly_threat_limit.
    """
    settings = get_settings()
    
    # In production:
    # import resend
    # resend.api_key = settings.resend_api_key
    # resend.Emails.send({
    #     "from": "SniperIP <noreply@sniperip.com>",
    #     "to": client_email,
    #     "subject": "You've reached your monthly threat limit",
    #     "html": f"<h1>Hi {client_name},</h1>..."
    # })
    
    return {
        "status": "sent",
        "to": client_email,
        "subject": "You've reached your monthly threat limit — Upgrade to continue protecting your brand",
    }


def send_threat_digest(client_email: str, threats_count: int, revenue_protected: float):
    """Weekly digest email with threat summary"""
    return {
        "status": "sent",
        "to": client_email,
        "subject": f"Weekly IP Report: {threats_count} threats found, ${revenue_protected:,.0f} protected",
    }


def send_slack_alert(message: str, channel: str = "admin-alerts"):
    """
    Send alert to Slack admin channel.
    
    Used for:
    - DLQ failures (🚨 Shopify DMCA failed after 5 retries)
    - New client signups
    - System health alerts
    """
    settings = get_settings()
    
    # In production:
    # from slack_sdk.webhook import WebhookClient
    # webhook = WebhookClient(settings.slack_webhook_url)
    # webhook.send(text=message)
    
    return {
        "status": "sent",
        "channel": channel,
        "message": message,
    }


def send_takedown_confirmation(client_email: str, threat_url: str, platform: str, case_number: str):
    """Notify client that a takedown was successfully filed"""
    return {
        "status": "sent",
        "to": client_email,
        "subject": f"Takedown filed: {platform} — Case #{case_number}",
    }
