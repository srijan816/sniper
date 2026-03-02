"""Generic registrar and hosting provider abuse reporting service.

Handles domains that do not match a known platform (Shopify, Meta, Amazon,
TikTok, eBay).  Three escalation tiers are attempted in order:

1. Known-registrar form  – URL or email mapped via REGISTRAR_ABUSE_FORMS.
2. Playwright web form   – Basic stealth form-fill for registrars with a form URL.
3. Generic email         – Falls back to abuse@<domain> via the notification service.
"""
from __future__ import annotations

import logging
import uuid
from urllib.parse import urlparse

import httpx
import whois

from app.core.config import get_settings
from app.services.notification_service import send_generic_dmca_notice
from app.workers.takedown import (
    SubmissionResult,
    _extract_sitekey,
    _fill_first,
    _click_first,
    _inject_recaptcha_token,
    _open_hardened_page,
    _solve_recaptcha_v2,
    _utcnow_iso,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Registrar abuse contact lookup table
# Keys are lower-case substrings matched against the WHOIS registrar name.
# Values are either an HTTPS form URL or a mailto: address.
# ---------------------------------------------------------------------------
REGISTRAR_ABUSE_FORMS: dict[str, str] = {
    "godaddy":    "https://supportcenter.godaddy.com/AbuseReport",
    "namecheap":  "https://www.namecheap.com/support/abuse-form/",
    "cloudflare": "https://abuse.cloudflare.com/",
    "ovh":        "abuse@ovh.net",
    "hostinger":  "abuse@hostinger.com",
    "bluehost":   "abuse@bluehost.com",
}

_GOOD_FAITH_STATEMENT = (
    "I have a good faith belief that use of the material in the manner complained "
    "of is not authorized by the copyright owner, its agent, or the law."
)
_PERJURY_STATEMENT = (
    "I swear, under penalty of perjury, that the information in this notification "
    "is accurate and that I am the copyright owner or am authorized to act on "
    "behalf of the owner of an exclusive right that is allegedly infringed."
)
_SIGNATURE = "/s/ Authorized Agent — SniperIP Enforcement Automation"


# ---------------------------------------------------------------------------
# WHOIS helpers
# ---------------------------------------------------------------------------

def resolve_registrar(domain: str) -> dict:
    """Perform a WHOIS lookup and return structured registrar information.

    Returns a dict with keys:
        ``registrar``          – Registrar name string or empty string.
        ``registrar_email``    – Primary registrar abuse / contact email or empty string.
        ``creation_date``      – Domain creation date string or empty string.
        ``registrant_country`` – Registrant country code or empty string.

    All exceptions are caught silently; an empty result dict is returned on
    any failure so callers do not need to handle WHOIS errors.
    """
    result: dict = {
        "registrar": "",
        "registrar_email": "",
        "creation_date": "",
        "registrant_country": "",
    }
    try:
        info = whois.whois(domain)

        registrar = info.get("registrar") or ""
        if isinstance(registrar, list):
            registrar = registrar[0] if registrar else ""
        result["registrar"] = str(registrar).strip()

        emails = info.get("emails") or []
        if isinstance(emails, str):
            emails = [emails]
        for email in emails:
            if email and "@" in email:
                result["registrar_email"] = email.strip().lower()
                break

        creation_date = info.get("creation_date") or ""
        if isinstance(creation_date, list):
            creation_date = creation_date[0] if creation_date else ""
        result["creation_date"] = str(creation_date).strip() if creation_date else ""

        country = info.get("registrant_country") or info.get("country") or ""
        if isinstance(country, list):
            country = country[0] if country else ""
        result["registrant_country"] = str(country).strip()

    except Exception as exc:
        logger.warning("WHOIS lookup failed for %s: %s", domain, exc)

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _root_domain(host: str) -> str:
    host = (host or "").strip().lower().split(":")[0]
    parts = [p for p in host.split(".") if p]
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def _match_registrar_form(registrar_name: str) -> str | None:
    """Return the abuse contact (URL or email) for *registrar_name*, or None."""
    lower = registrar_name.lower()
    for key, contact in REGISTRAR_ABUSE_FORMS.items():
        if key in lower:
            return contact
    return None


def _build_dmca_html(
    *,
    contact_name: str,
    infringing_url: str,
    original_url: str,
    similarity: float,
    loa_url: str,
    evidence_url: str,
    host_domain: str,
) -> str:
    return (
        "<p>Hello Abuse / DMCA Team,</p>"
        "<p>This is a formal notice of copyright infringement pursuant to 17 U.S.C. § 512(c)(3) "
        "(the Digital Millennium Copyright Act). We request that you expeditiously remove or disable "
        "access to the infringing material identified below.</p>"
        "<h3>Identification of the infringing material:</h3>"
        "<ul>"
        f"<li>Infringing URL: <a href='{infringing_url}'>{infringing_url}</a></li>"
        f"<li>Original copyrighted asset URL: <a href='{original_url}'>{original_url}</a></li>"
        f"<li>Similarity score: {similarity:.4f}</li>"
        f"<li>Letter of Authorization: <a href='{loa_url}'>{loa_url}</a></li>"
        f"<li>Evidence packet (PDF): <a href='{evidence_url}'>{evidence_url}</a></li>"
        "</ul>"
        "<h3>Required Statutory Statements (17 U.S.C. § 512(c)(3)):</h3>"
        f"<p><strong>Good faith belief:</strong> {_GOOD_FAITH_STATEMENT}</p>"
        f"<p><strong>Accuracy and authority:</strong> {_PERJURY_STATEMENT}</p>"
        "<p><strong>Electronic Signature:</strong><br/>"
        f"/s/ {contact_name}<br/>Authorized Agent — SniperIP Enforcement Automation</p>"
        "<p>Please take immediate action to remove or disable access to the infringing material.</p>"
        "<p>Regards,<br/>"
        f"{contact_name}<br/>SniperIP Enforcement Automation</p>"
    )


# ---------------------------------------------------------------------------
# Main public functions
# ---------------------------------------------------------------------------

def submit_registrar_abuse(ctx: dict, evidence: dict, registrar_info: dict) -> SubmissionResult:
    """Report abuse to the domain's registrar or hosting provider.

    Decision logic:
    - If the registrar maps to a known *email* address → send DMCA notice email.
    - If the registrar maps to a known *form URL* → attempt Playwright form fill.
    - Otherwise → fall back to emailing abuse@<root_domain>.

    Parameters
    ----------
    ctx:
        Dict containing ``threat``, ``client``, and ``asset`` records.
    evidence:
        Dict from ``_capture_evidence``; must include ``proof_pdf_url``.
    registrar_info:
        Dict returned by ``resolve_registrar``.  Expected keys:
        ``registrar``, ``registrar_email``, ``creation_date``, ``registrant_country``.

    Returns
    -------
    SubmissionResult
    """
    settings = get_settings()
    threat = ctx["threat"]
    client = ctx["client"]
    asset = ctx["asset"]

    infringing_url = threat.get("infringing_url") or ""
    original_url = asset.get("thumbnail_url") or asset.get("storage_url") or ""
    similarity = float(threat.get("similarity_score") or 0.0)
    host_domain = threat.get("host_domain") or (urlparse(infringing_url).netloc or "")
    root = _root_domain(host_domain)

    loa_url = client.get("loa_document_url") or ""
    if not loa_url:
        raise RuntimeError("Client LOA document is missing. Upload LOA before enforcement.")

    contact_name = client.get("legal_contact_name") or "Authorized Agent"
    cc = [client["legal_contact_email"]] if client.get("legal_contact_email") else None

    registrar_name = registrar_info.get("registrar") or ""
    abuse_contact = _match_registrar_form(registrar_name) if registrar_name else None

    evidence_url = evidence.get("proof_pdf_url") or ""
    subject = (
        f"DMCA Takedown Notice (17 U.S.C. § 512): Unauthorized content on {host_domain}"
    )
    html = _build_dmca_html(
        contact_name=contact_name,
        infringing_url=infringing_url,
        original_url=original_url,
        similarity=similarity,
        loa_url=loa_url,
        evidence_url=evidence_url,
        host_domain=host_domain,
    )

    # -- Branch: known email address -------------------------------------------
    if abuse_contact and not abuse_contact.startswith("http"):
        recipients = [abuse_contact]
        if settings.takedown_test_mode_no_submit:
            logger.info("Registrar abuse (email): test mode – skipping send to %s.", abuse_contact)
            return SubmissionResult(
                case_number=f"TEST-REG-{uuid.uuid4().hex[:10].upper()}",
                payload={
                    "mode": "registrar_email_test_mode",
                    "submitted_at": _utcnow_iso(),
                    "registrar": registrar_name,
                    "abuse_contact": abuse_contact,
                    "infringing_url": infringing_url,
                    "evidence_url": evidence_url,
                    "test_mode": True,
                },
            )
        logger.info("Sending registrar abuse email to %s for %s.", abuse_contact, infringing_url)
        send_generic_dmca_notice(recipients, subject, html, cc_emails=cc)
        return SubmissionResult(
            case_number=f"REG-{uuid.uuid4().hex[:10].upper()}",
            payload={
                "mode": "registrar_email",
                "submitted_at": _utcnow_iso(),
                "registrar": registrar_name,
                "abuse_contact": abuse_contact,
                "recipients": recipients,
                "infringing_url": infringing_url,
                "original_url": original_url,
                "loa_url": loa_url,
                "evidence_url": evidence_url,
            },
        )

    # -- Branch: known web form URL --------------------------------------------
    if abuse_contact and abuse_contact.startswith("http"):
        try:
            result = _submit_registrar_form(
                form_url=abuse_contact,
                contact_name=contact_name,
                contact_email=client.get("legal_contact_email") or "",
                company_name=client.get("company_name") or "SniperIP Client",
                infringing_url=infringing_url,
                original_url=original_url,
                evidence_url=evidence_url,
                description=html,
                settings=settings,
            )
            result.payload.update({
                "registrar": registrar_name,
                "loa_url": loa_url,
            })
            return result
        except Exception as exc:
            logger.warning(
                "Registrar web-form submission failed for %s (%s); falling back to email. Error: %s",
                registrar_name, abuse_contact, exc,
            )
            # Fall through to generic email fallback

    # -- Branch: generic fallback email ----------------------------------------
    fallback_recipients = [f"abuse@{root}"]
    if registrar_info.get("registrar_email"):
        fallback_recipients.insert(0, registrar_info["registrar_email"])

    if settings.takedown_test_mode_no_submit:
        logger.info("Registrar abuse (fallback email): test mode – skipping send to %s.", fallback_recipients)
        return SubmissionResult(
            case_number=f"TEST-REG-{uuid.uuid4().hex[:10].upper()}",
            payload={
                "mode": "registrar_fallback_email_test_mode",
                "submitted_at": _utcnow_iso(),
                "registrar": registrar_name,
                "recipients": fallback_recipients,
                "infringing_url": infringing_url,
                "evidence_url": evidence_url,
                "test_mode": True,
            },
        )

    logger.info(
        "Sending fallback registrar abuse email to %s for %s.",
        fallback_recipients, infringing_url,
    )
    send_generic_dmca_notice(fallback_recipients, subject, html, cc_emails=cc)
    return SubmissionResult(
        case_number=f"REG-{uuid.uuid4().hex[:10].upper()}",
        payload={
            "mode": "registrar_fallback_email",
            "submitted_at": _utcnow_iso(),
            "registrar": registrar_name,
            "recipients": fallback_recipients,
            "infringing_url": infringing_url,
            "original_url": original_url,
            "loa_url": loa_url,
            "evidence_url": evidence_url,
        },
    )


def submit_google_safe_browsing(infringing_url: str) -> None:
    """Log a URL for manual Google Safe Browsing submission.

    The Google Safe Browsing report API requires enrollment in the Trusted
    Copyright Program (https://safebrowsing.google.com/safebrowsing/report_phish/).
    Automated programmatic submission is not available without program membership,
    so this function logs the URL for operator review and manual follow-up.

    Parameters
    ----------
    infringing_url:
        The URL of the infringing page to be flagged.
    """
    logger.warning(
        "Google Safe Browsing manual action required: the URL below must be "
        "submitted manually via https://safebrowsing.google.com/safebrowsing/report_phish/ "
        "or via the Google Trusted Copyright Program API (membership required). "
        "Infringing URL: %s",
        infringing_url,
    )


# ---------------------------------------------------------------------------
# Internal: Playwright form fill for registrar abuse forms
# ---------------------------------------------------------------------------

def _submit_registrar_form(
    *,
    form_url: str,
    contact_name: str,
    contact_email: str,
    company_name: str,
    infringing_url: str,
    original_url: str,
    evidence_url: str,
    description: str,
    settings,
) -> SubmissionResult:
    """Fill a registrar abuse web form using Playwright stealth."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
    from app.workers.takedown import _extract_case_number  # local import to avoid circular at module level

    if settings.takedown_test_mode_no_submit:
        logger.info("Registrar form: test mode – skipping real submission to %s.", form_url)
        return SubmissionResult(
            case_number=f"TEST-REG-{uuid.uuid4().hex[:10].upper()}",
            payload={
                "mode": "registrar_form_test_mode",
                "form_url": form_url,
                "submitted_at": _utcnow_iso(),
                "infringing_url": infringing_url,
                "original_url": original_url,
                "evidence_url": evidence_url,
                "test_mode": True,
            },
        )

    with sync_playwright() as playwright:
        browser, context, page = _open_hardened_page(playwright)
        try:
            logger.info("Navigating to registrar abuse form: %s", form_url)
            page.goto(form_url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(1500)

            _fill_first(page, [
                "input[name='full_name']",
                "input[name='name']",
                "input[id*='name']",
                "input[autocomplete='name']",
            ], contact_name)

            _fill_first(page, [
                "input[name='email']",
                "input[type='email']",
                "input[autocomplete='email']",
                "input[id*='email']",
            ], contact_email)

            _fill_first(page, [
                "input[name='company']",
                "input[name='organization']",
                "input[id*='company']",
                "input[autocomplete='organization']",
            ], company_name)

            _fill_first(page, [
                "input[name='infringing_url']",
                "input[name='url']",
                "input[name='reported_url']",
                "input[id*='infringing']",
                "input[id*='url']",
                "textarea[name='url']",
            ], infringing_url)

            _fill_first(page, [
                "textarea[name='description']",
                "textarea[name='details']",
                "textarea[name='comments']",
                "textarea[name='notes']",
                "textarea[id*='description']",
                "textarea[id*='detail']",
                "textarea",
            ], description)

            # Upload evidence PDF when a file input is available
            try:
                file_inputs = page.locator("input[type='file']")
                if file_inputs.count() > 0:
                    with httpx.Client(timeout=45.0, follow_redirects=True) as http:
                        pdf_bytes = http.get(evidence_url).content
                    file_inputs.first.set_input_files([{
                        "name": "proof-of-infringement.pdf",
                        "mimeType": "application/pdf",
                        "buffer": pdf_bytes,
                    }])
                    logger.info("Evidence PDF uploaded to registrar abuse form.")
            except Exception as exc:
                logger.warning("Could not attach evidence PDF to registrar abuse form: %s", exc)

            # Check all checkboxes
            try:
                checkboxes = page.locator("input[type='checkbox']")
                for idx in range(checkboxes.count()):
                    checkbox = checkboxes.nth(idx)
                    if not checkbox.is_checked():
                        checkbox.check(force=True)
            except Exception as exc:
                logger.warning("Could not check registrar form checkboxes: %s", exc)

            # CAPTCHA
            site_key = _extract_sitekey(page)
            if site_key:
                logger.info("CAPTCHA detected on registrar form; solving via 2Captcha.")
                captcha_token = _solve_recaptcha_v2(site_key, page.url)
                _inject_recaptcha_token(page, captcha_token)

            if not _click_first(page, [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Submit')",
                "button:has-text('Send')",
                "button:has-text('Report')",
                "button:has-text('Continue')",
            ]):
                raise RuntimeError(f"Could not find a submit button on registrar form: {form_url}")

            try:
                page.wait_for_load_state("networkidle", timeout=30000)
            except PlaywrightTimeoutError:
                pass
            page.wait_for_timeout(2500)

            content = page.content().lower()
            success = any(
                phrase in content
                for phrase in ("thank you", "submitted", "received", "reference", "case number", "ticket")
            ) or page.url != form_url

            if not success:
                raise RuntimeError(f"Registrar form submission at {form_url} could not be verified as successful.")

            case_number = _extract_case_number(page.content()) or f"REG-{uuid.uuid4().hex[:10].upper()}"
            logger.info("Registrar form submission successful. Case: %s", case_number)

            return SubmissionResult(
                case_number=case_number,
                payload={
                    "mode": "registrar_form",
                    "form_url": form_url,
                    "final_url": page.url,
                    "submitted_at": _utcnow_iso(),
                    "infringing_url": infringing_url,
                    "original_url": original_url,
                    "evidence_url": evidence_url,
                },
            )
        finally:
            context.close()
            browser.close()
