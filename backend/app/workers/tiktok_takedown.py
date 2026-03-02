"""TikTok DMCA/IP takedown handler.

Supports two submission paths:
  1. BPP API  – used when the client has a TikTok Brand Protection Partner token.
  2. Browser  – Playwright + stealth fallback that fills the public IP-report form.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

try:
    from playwright_stealth import stealth_sync
except Exception:  # pragma: no cover – optional at runtime
    stealth_sync = None

from app.core.config import get_settings
from app.workers.takedown import (
    SubmissionResult,
    _extract_case_number,
    _extract_sitekey,
    _fill_first,
    _click_first,
    _inject_recaptcha_token,
    _open_hardened_page,
    _solve_recaptcha_v2,
    _utcnow_iso,
)

logger = logging.getLogger(__name__)

_TIKTOK_IP_FORM_URL = "https://www.tiktok.com/legal/report/ip"
_TIKTOK_BPP_ENDPOINT = "https://open-api.tiktok.com/api/v1.3/ip-report/submit"

_GOOD_FAITH_STATEMENT = (
    "I have a good faith belief that use of the copyrighted material described above "
    "is not authorized by the copyright owner, its agent, or the law."
)
_PERJURY_STATEMENT = (
    "I swear, under penalty of perjury, that the information in this notification is "
    "accurate and that I am the copyright owner or am authorized to act on behalf of "
    "the owner of an exclusive right that is allegedly infringed."
)
_SIGNATURE = "/s/ Authorized Agent — SniperIP Enforcement Automation"


def _build_tiktok_description(asset: dict, infringing_url: str, original_url: str, evidence_url: str) -> str:
    ai_description = asset.get("ai_description") or asset.get("description") or "Copyrighted original work."
    return (
        f"Original work description: {ai_description}\n\n"
        f"Original asset URL: {original_url}\n"
        f"Infringing URL: {infringing_url}\n"
        f"Evidence packet (PDF): {evidence_url}\n\n"
        f"{_GOOD_FAITH_STATEMENT}\n\n"
        f"{_PERJURY_STATEMENT}\n\n"
        f"{_SIGNATURE}"
    )


def submit_tiktok_dmca(ctx: dict, evidence: dict) -> SubmissionResult:
    """Submit a TikTok IP/DMCA takedown report.

    Parameters
    ----------
    ctx:
        Dict containing ``threat``, ``client``, and ``asset`` records.
    evidence:
        Dict produced by ``_capture_evidence``; must include ``proof_pdf_url``.

    Returns
    -------
    SubmissionResult
        Populated with a ``TT-`` prefixed case number and metadata payload.
    """
    settings = get_settings()
    threat = ctx["threat"]
    client = ctx["client"]
    asset = ctx["asset"]

    infringing_url = threat.get("infringing_url") or ""
    original_url = asset.get("thumbnail_url") or asset.get("storage_url") or ""
    evidence_url = evidence.get("proof_pdf_url") or ""
    bpp_token = (client.get("tiktok_bpp_token") or "").strip()

    if bpp_token:
        return _submit_via_bpp_api(
            bpp_token=bpp_token,
            infringing_url=infringing_url,
            original_url=original_url,
            evidence_url=evidence_url,
            settings=settings,
        )

    return _submit_via_browser(
        ctx=ctx,
        evidence=evidence,
        infringing_url=infringing_url,
        original_url=original_url,
        evidence_url=evidence_url,
        settings=settings,
    )


# ---------------------------------------------------------------------------
# BPP API path
# ---------------------------------------------------------------------------

def _submit_via_bpp_api(
    *,
    bpp_token: str,
    infringing_url: str,
    original_url: str,
    evidence_url: str,
    settings,
) -> SubmissionResult:
    """Use TikTok's Brand Protection Partner (BPP) REST API."""
    payload = {
        "access_token": bpp_token,
        "infringing_url": infringing_url,
        "original_url": original_url,
        "ip_type": "COPYRIGHT",
        "evidence_url": evidence_url,
    }

    if settings.takedown_test_mode_no_submit:
        logger.info("TikTok BPP API: test mode – skipping real submission.")
        return SubmissionResult(
            case_number=f"TEST-TT-{uuid.uuid4().hex[:10].upper()}",
            payload={
                "mode": "tiktok_bpp_api_test_mode",
                "submitted_at": _utcnow_iso(),
                "endpoint": _TIKTOK_BPP_ENDPOINT,
                "infringing_url": infringing_url,
                "original_url": original_url,
                "evidence_url": evidence_url,
                "test_mode": True,
            },
        )

    logger.info("Submitting TikTok IP report via BPP API: %s", infringing_url)
    with httpx.Client(timeout=45.0) as http:
        response = http.post(_TIKTOK_BPP_ENDPOINT, json=payload)
        response.raise_for_status()
        response_data: dict = (
            response.json()
            if response.headers.get("content-type", "").startswith("application/json")
            else {}
        )

    case_number = (
        response_data.get("report_id")
        or response_data.get("case_id")
        or response_data.get("id")
        or f"TT-{uuid.uuid4().hex[:10].upper()}"
    )
    logger.info("TikTok BPP API submission successful. Case: %s", case_number)

    return SubmissionResult(
        case_number=str(case_number),
        payload={
            "mode": "tiktok_bpp_api",
            "submitted_at": _utcnow_iso(),
            "endpoint": _TIKTOK_BPP_ENDPOINT,
            "infringing_url": infringing_url,
            "original_url": original_url,
            "evidence_url": evidence_url,
            "response": response_data,
        },
    )


# ---------------------------------------------------------------------------
# Browser (Playwright + stealth) path
# ---------------------------------------------------------------------------

def _submit_via_browser(
    *,
    ctx: dict,
    evidence: dict,
    infringing_url: str,
    original_url: str,
    evidence_url: str,
    settings,
) -> SubmissionResult:
    """Fill TikTok's public IP-report web form using Playwright."""
    asset = ctx["asset"]
    client = ctx["client"]

    contact_name = client.get("legal_contact_name") or "Authorized Agent"
    contact_email = client.get("legal_contact_email") or ""
    company_name = client.get("company_name") or "SniperIP Client"
    ai_description = asset.get("ai_description") or asset.get("description") or "Copyrighted original work."

    work_description = _build_tiktok_description(asset, infringing_url, original_url, evidence_url)

    form_url = _TIKTOK_IP_FORM_URL

    with sync_playwright() as playwright:
        browser, context, page = _open_hardened_page(playwright)
        try:
            logger.info("Navigating to TikTok IP report form: %s", form_url)
            page.goto(form_url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(2000)

            # Handle potential login wall – TikTok sometimes requires an account.
            # Attempt to proceed as guest if a "continue as guest" option is visible.
            _click_first(page, [
                "button:has-text('Continue as guest')",
                "button:has-text('Not now')",
                "[data-testid='modal-close-inner-button']",
            ])
            page.wait_for_timeout(1000)

            # Select violation type (Copyright)
            _click_first(page, [
                "input[value='COPYRIGHT']",
                "input[value='copyright']",
                "label:has-text('Copyright')",
                "option[value='COPYRIGHT']",
                "li:has-text('Copyright')",
            ])
            page.wait_for_timeout(500)

            # Reporter contact info
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

            # Original work description
            _fill_first(page, [
                "textarea[name='original_work_description']",
                "textarea[name='description']",
                "textarea[name='original_description']",
                "textarea[id*='description']",
                "textarea[id*='original']",
            ], ai_description)

            # Infringing URL
            _fill_first(page, [
                "input[name='infringing_url']",
                "input[name='reported_url']",
                "textarea[name='infringing_url']",
                "input[id*='infringing']",
                "input[placeholder*='infringing']",
                "input[placeholder*='TikTok']",
            ], infringing_url)

            # Original content URL
            _fill_first(page, [
                "input[name='original_url']",
                "input[name='original_content_url']",
                "input[id*='original_url']",
                "input[placeholder*='original']",
            ], original_url)

            # Full notice / summary text
            _fill_first(page, [
                "textarea[name='additional_info']",
                "textarea[name='notes']",
                "textarea[name='details']",
                "textarea[id*='additional']",
                "textarea[id*='detail']",
            ], work_description)

            # Upload evidence PDF if a file input is present
            try:
                file_inputs = page.locator("input[type='file']")
                if file_inputs.count() > 0:
                    import io
                    with httpx.Client(timeout=45.0, follow_redirects=True) as http:
                        pdf_bytes = http.get(evidence_url).content
                    file_inputs.first.set_input_files([{
                        "name": "proof-of-infringement.pdf",
                        "mimeType": "application/pdf",
                        "buffer": pdf_bytes,
                    }])
                    logger.info("Evidence PDF uploaded to TikTok form.")
            except Exception as exc:
                logger.warning("Could not attach evidence PDF to TikTok form: %s", exc)

            # Check all checkboxes (good faith, perjury, etc.)
            try:
                checkboxes = page.locator("input[type='checkbox']")
                for idx in range(checkboxes.count()):
                    checkbox = checkboxes.nth(idx)
                    if not checkbox.is_checked():
                        checkbox.check(force=True)
            except Exception as exc:
                logger.warning("Could not check TikTok form checkboxes: %s", exc)

            # CAPTCHA
            site_key = _extract_sitekey(page)
            if site_key:
                logger.info("CAPTCHA detected on TikTok form; solving via 2Captcha.")
                captcha_token = _solve_recaptcha_v2(site_key, page.url)
                _inject_recaptcha_token(page, captcha_token)

            if settings.takedown_test_mode_no_submit:
                page.screenshot(path="pre_submit_tiktok_test_mode.png", full_page=True)
                case_number = f"TEST-TT-{uuid.uuid4().hex[:10].upper()}"
                return SubmissionResult(
                    case_number=case_number,
                    payload={
                        "mode": "tiktok_browser_form_test_mode",
                        "form_url": form_url,
                        "final_url": page.url,
                        "submitted_at": _utcnow_iso(),
                        "infringing_url": infringing_url,
                        "original_url": original_url,
                        "evidence_url": evidence_url,
                        "test_mode": True,
                    },
                )

            # Submit
            if not _click_first(page, [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Submit')",
                "button:has-text('Send')",
                "button:has-text('Report')",
                "button:has-text('Continue')",
            ]):
                raise RuntimeError("Could not find a submit button on the TikTok IP report form.")

            try:
                page.wait_for_load_state("networkidle", timeout=30000)
            except PlaywrightTimeoutError:
                pass
            page.wait_for_timeout(2500)

            content = page.content().lower()
            success = any(
                phrase in content
                for phrase in ("thank you", "submitted", "received", "reference", "case number", "report id")
            ) or page.url != form_url

            if not success:
                raise RuntimeError("TikTok IP report form submission could not be verified as successful.")

            case_number = _extract_case_number(page.content()) or f"TT-{uuid.uuid4().hex[:10].upper()}"
            logger.info("TikTok browser form submission successful. Case: %s", case_number)

            return SubmissionResult(
                case_number=case_number,
                payload={
                    "mode": "tiktok_browser_form",
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
