"""Takedown persistence monitoring — detects reinstated listings."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
import resend

from app.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import get_supabase_client

logger = logging.getLogger(__name__)


def _db():
    db = get_supabase_client()
    if db is None:
        raise RuntimeError("Supabase is not configured.")
    return db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _utcnow_iso() -> str:
    return _utcnow().isoformat()


def _table_missing(exc: Exception) -> bool:
    message = str(exc)
    return "PGRST205" in message or "Could not find the table" in message


def _fetch_submitted_takedowns() -> tuple[str, list[dict]]:
    """Try both takedown table names; return (table_name, rows)."""
    seven_days_ago = (_utcnow() - timedelta(days=7)).isoformat()
    thirty_days_ago = (_utcnow() - timedelta(days=30)).isoformat()

    for table_name in ("takedown_requests", "takedowns"):
        try:
            rows = (
                _db()
                .table(table_name)
                .select("*")
                .in_("status", ["SUBMITTED", "CONFIRMED"])
                .gte("completed_at", thirty_days_ago)
                .lte("completed_at", seven_days_ago)
                .execute()
                .data
                or []
            )
            return table_name, rows
        except Exception as exc:
            if _table_missing(exc):
                continue
            raise

    return "takedown_requests", []


def _fetch_threat(threat_id: str) -> dict | None:
    rows = (
        _db()
        .table("threats")
        .select("*")
        .eq("id", threat_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else None


def _write_audit_log(threat_id: str, old_status: str | None, new_status: str, changed_by: str = "SYSTEM"):
    _db().table("audit_logs").insert(
        {
            "threat_id": threat_id,
            "old_status": old_status,
            "new_status": new_status,
            "changed_by": changed_by,
            "changed_at": _utcnow_iso(),
        }
    ).execute()


def _update_threat_status(threat_id: str, new_status: str) -> str | None:
    rows = _db().table("threats").select("id,status").eq("id", threat_id).limit(1).execute().data or []
    if not rows:
        return None
    old_status = rows[0].get("status")
    _db().table("threats").update({"status": new_status}).eq("id", threat_id).execute()
    _write_audit_log(threat_id, old_status, new_status, "SYSTEM")
    return old_status


def _is_reinstated(infringing_url: str) -> bool:
    """
    HEAD the URL; if 200, GET the first 50KB and check for purchase-intent keywords.
    Returns True if the listing appears to be active again.
    """
    product_keywords = ["add to cart", "buy now", "checkout", "price", "$", "order now", "shop"]

    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            head_resp = client.head(infringing_url)
            if head_resp.status_code != 200:
                return False

            keyword_hits = 0
            with client.stream("GET", infringing_url) as stream_resp:
                content = b""
                for chunk in stream_resp.iter_bytes():
                    content += chunk
                    if len(content) >= 50_000:
                        break

            html = content.decode("utf-8", errors="ignore").lower()
            for keyword in product_keywords:
                if keyword in html:
                    keyword_hits += 1
                if keyword_hits >= 2:
                    return True

    except Exception as exc:
        logger.warning("Network check failed for %s: %s", infringing_url, exc)

    return False


def _send_reinstatement_email(client_email: str, domain: str, infringing_url: str) -> None:
    settings = get_settings()
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY is not set; skipping reinstatement email to %s.", client_email)
        return

    dashboard_url = f"{settings.frontend_url}/dashboard"
    legal_partners_url = f"{settings.frontend_url}/dashboard/legal-partners"

    subject = f"Alert: Takedown Reversed — {domain} may be back online"
    html = (
        f"<p>Hi,</p>"
        f"<p>Our monitoring system has detected that a previously taken-down listing on "
        f"<strong>{domain}</strong> may have been reinstated.</p>"
        f"<p><strong>Infringing URL:</strong> <a href=\"{infringing_url}\">{infringing_url}</a></p>"
        f"<h3>What is a counter-notice?</h3>"
        f"<p>When a listing is removed following a DMCA or platform takedown, the seller may file a "
        f"counter-notice claiming the removal was in error. If a valid counter-notice is filed, platforms "
        f"are legally required to restore the content within 10-14 business days unless you initiate a "
        f"federal lawsuit. A counter-notice also shifts legal liability to the seller if their claim is "
        f"false.</p>"
        f"<p>If you believe this listing is still infringing, you have the following options:</p>"
        f"<table cellpadding=\"0\" cellspacing=\"0\" border=\"0\">"
        f"<tr>"
        f"<td style=\"padding: 8px 12px;\">"
        f"<a href=\"{dashboard_url}\" style=\"display:inline-block;background:#39FF14;color:#1A1C24;"
        f"font-weight:bold;padding:12px 24px;border-radius:6px;text-decoration:none;\">"
        f"Re-submit Takedown</a>"
        f"</td>"
        f"<td style=\"padding: 8px 12px;\">"
        f"<a href=\"{legal_partners_url}\" style=\"display:inline-block;border:1px solid #1A1C24;"
        f"color:#1A1C24;font-weight:bold;padding:12px 24px;border-radius:6px;text-decoration:none;\">"
        f"Consult Legal Counsel</a>"
        f"</td>"
        f"</tr>"
        f"</table>"
        f"<p style=\"margin-top:24px;\">If you need help deciding on next steps, our legal partner "
        f"directory at <a href=\"{legal_partners_url}\">{legal_partners_url}</a> connects you with "
        f"specialist IP attorneys experienced in counter-notice litigation.</p>"
        f"<p>Regards,<br/>SniperIP Enforcement Automation</p>"
    )

    resend.api_key = settings.resend_api_key
    resend.Emails.send(
        {
            "from": settings.notification_from_email,
            "to": [client_email],
            "subject": subject,
            "html": html,
        }
    )


def _get_client_email(threat: dict) -> str | None:
    """Walk asset -> client to get the legal contact email."""
    asset_id = threat.get("asset_id")
    if not asset_id:
        return None

    asset_rows = (
        _db()
        .table("assets")
        .select("client_id")
        .eq("id", asset_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not asset_rows:
        return None

    client_id = asset_rows[0].get("client_id")
    if not client_id:
        return None

    client_rows = (
        _db()
        .table("clients")
        .select("legal_contact_email")
        .eq("id", client_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not client_rows:
        return None

    return client_rows[0].get("legal_contact_email")


@celery_app.task(name="app.workers.monitoring.check_takedown_persistence")
def check_takedown_persistence():
    """
    Scan recently submitted/confirmed takedowns to detect reinstated listings.
    Runs against takedowns completed between 7 and 30 days ago.
    """
    table_name, takedowns = _fetch_submitted_takedowns()
    logger.info(
        "check_takedown_persistence: scanning %d takedowns from table '%s'.",
        len(takedowns),
        table_name,
    )

    checked = 0
    reinstated = 0
    errors = 0

    for takedown in takedowns:
        takedown_id = takedown.get("id")
        threat_id = takedown.get("threat_id")
        current_status = takedown.get("status", "SUBMITTED")

        if not threat_id:
            continue

        threat = _fetch_threat(threat_id)
        if not threat:
            continue

        infringing_url = threat.get("infringing_url", "")
        if not infringing_url:
            continue

        domain = urlparse(infringing_url).netloc or infringing_url
        checked += 1

        try:
            if not _is_reinstated(infringing_url):
                continue

            logger.warning(
                "Listing appears reinstated: takedown_id=%s threat_id=%s url=%s",
                takedown_id,
                threat_id,
                infringing_url,
            )

            # Update takedown status
            _db().table(table_name).update({"status": "REINSTATED"}).eq("id", takedown_id).execute()

            # Update threat status and write audit log
            _update_threat_status(threat_id, "REINSTATED")

            # Override audit log entry to record the old takedown status, not the intermediate
            _write_audit_log(threat_id, current_status, "REINSTATED", "SYSTEM")

            # Notify the client
            try:
                client_email = _get_client_email(threat)
                if client_email:
                    _send_reinstatement_email(client_email, domain, infringing_url)
            except Exception as email_exc:
                logger.error(
                    "Failed to send reinstatement email for threat %s: %s",
                    threat_id,
                    email_exc,
                )

            reinstated += 1

        except Exception as exc:
            logger.error(
                "Error checking takedown %s (threat %s, url %s): %s",
                takedown_id,
                threat_id,
                infringing_url,
                exc,
            )
            errors += 1
            continue

    return {
        "table": table_name,
        "checked": checked,
        "reinstated": reinstated,
        "errors": errors,
    }


@celery_app.task(
    name="app.workers.monitoring.send_scan_followup_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_scan_followup_email(self, email: str, matches_found: int, scan_id: str):
    """
    Send a follow-up email to a scan lead with the number of matches found
    and a CTA to view results on the dashboard.
    """
    settings = get_settings()
    if not settings.resend_api_key:
        logger.warning(
            "RESEND_API_KEY is not configured; skipping scan follow-up email to %s (scan_id=%s).",
            email,
            scan_id,
        )
        return {"status": "skipped", "reason": "no_resend_api_key"}

    dashboard_url = f"{settings.frontend_url}/dashboard"
    noun = "match" if matches_found == 1 else "matches"

    html = (
        f"<p>Hi,</p>"
        f"<p>Your SniperIP scan (ID: <code>{scan_id}</code>) is complete.</p>"
        f"<p>We found <strong>{matches_found} potential {noun}</strong> that may be infringing your "
        f"brand assets across the web.</p>"
        f"<p>"
        f"<a href=\"{dashboard_url}\" style=\"display:inline-block;background:#39FF14;color:#1A1C24;"
        f"font-weight:bold;padding:12px 24px;border-radius:6px;text-decoration:none;\">"
        f"View Results in Dashboard</a>"
        f"</p>"
        f"<p>From your dashboard you can review each match, approve takedowns, and track enforcement "
        f"status in real time.</p>"
        f"<p>Regards,<br/>SniperIP Enforcement Automation</p>"
    )

    try:
        resend.api_key = settings.resend_api_key
        resend.Emails.send(
            {
                "from": settings.notification_from_email,
                "to": [email],
                "subject": f"Your SniperIP scan found {matches_found} {noun}",
                "html": html,
            }
        )
        return {"status": "sent", "to": email, "scan_id": scan_id, "matches_found": matches_found}
    except Exception as exc:
        logger.error("Failed to send scan follow-up email to %s: %s", email, exc)
        raise self.retry(exc=exc)
