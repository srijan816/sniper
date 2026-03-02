"""eBay VeRO (Verified Rights Owner) takedown handler.

Supports two submission paths:
  1. VeRO web-form API – POST to eBay's VeRO NOCI reporting endpoint using
     the client's VeRO participant credentials.
  2. Browser fallback  – Playwright + stealth fills the public VeRO NOCI form
     at https://www.vero.ebay.com.
"""
from __future__ import annotations

import logging
import re
import uuid
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

_EBAY_VERO_FORM_URL = "https://www.vero.ebay.com"
_EBAY_ITEM_RE = re.compile(r"/itm/(?:[\w-]+/)?(\d+)")

_GOOD_FAITH_STATEMENT = (
    "I have a good faith belief that use of the copyrighted material described "
    "below is not authorized by the copyright owner, its agent, or the law."
)
_PERJURY_STATEMENT = (
    "I swear, under penalty of perjury, that the information in this NOCI is "
    "accurate and that I am the rights owner or am authorized to act on behalf "
    "of the owner of the exclusive right that is allegedly infringed."
)
_SIGNATURE = "/s/ Authorized Agent — SniperIP Enforcement Automation"


def _extract_ebay_item_number(url: str) -> str | None:
    """Return the eBay item number embedded in *url*, or None."""
    match = _EBAY_ITEM_RE.search(url or "")
    return match.group(1) if match else None


def _build_contact_block(client: dict) -> str:
    """Return plain-text contact block required by 17 U.S.C. § 512(c)(3)(A)(iv)."""
    import logging as _logging
    _log = _logging.getLogger(__name__)
    name = client.get("legal_contact_name") or "Authorized Agent"
    email = client.get("legal_contact_email") or ""
    phone = client.get("contact_phone") or ""
    address = client.get("contact_address") or ""
    if not phone:
        _log.warning("eBay DMCA notice missing contact_phone for client %s", client.get("id"))
    if not address:
        _log.warning("eBay DMCA notice missing contact_address for client %s", client.get("id"))
    lines = [
        "Contact Information (17 U.S.C. § 512(c)(3)(A)(iv)):",
        f"Name: {name}",
        f"Email: {email}",
    ]
    if phone:
        lines.append(f"Phone: {phone}")
    if address:
        lines.append(f"Address: {address}")
    return "\n".join(lines)


def _build_noci_description(
    asset: dict,
    infringing_url: str,
    item_number: str | None,
    original_url: str,
    evidence_url: str,
    client: dict | None = None,
) -> str:
    ai_description = asset.get("ai_description") or asset.get("description") or "Copyrighted original work."
    item_ref = f"eBay item #{item_number}" if item_number else infringing_url
    contact_block = _build_contact_block(client) if client else ""
    return (
        f"Notice of Claimed Infringement (NOCI)\n\n"
        f"Original work description: {ai_description}\n\n"
        f"Infringing listing: {item_ref}\n"
        f"Infringing URL: {infringing_url}\n"
        f"Original asset URL: {original_url}\n"
        f"Evidence packet (PDF): {evidence_url}\n\n"
        + (contact_block + "\n\n" if contact_block else "")
        + f"{_GOOD_FAITH_STATEMENT}\n\n"
        f"{_PERJURY_STATEMENT}\n\n"
        f"{_SIGNATURE}"
    )


def _build_vero_xml_noci(
    *,
    participant_id: str,
    contact_name: str,
    contact_email: str,
    company_name: str,
    item_number: str | None,
    infringing_url: str,
    original_url: str,
    evidence_url: str,
    noci_description: str,
) -> str:
    """Build a minimal XML NOCI payload for eBay's VeRO API endpoint."""
    item_id_elem = f"<ItemID>{item_number}</ItemID>" if item_number else ""
    return (
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
        "<NOCIRequest xmlns=\"urn:ebay:apis:eBLBaseComponents\">"
        f"  <ParticipantID>{participant_id}</ParticipantID>"
        "  <NOCIDetails>"
        "    <InfringementType>COPYRIGHT</InfringementType>"
        f"    {item_id_elem}"
        f"    <InfringingURL>{infringing_url}</InfringingURL>"
        f"    <OriginalWorkURL>{original_url}</OriginalWorkURL>"
        f"    <EvidenceURL>{evidence_url}</EvidenceURL>"
        f"    <Description><![CDATA[{noci_description}]]></Description>"
        "  </NOCIDetails>"
        "  <ContactInfo>"
        f"    <Name>{contact_name}</Name>"
        f"    <Email>{contact_email}</Email>"
        f"    <Company>{company_name}</Company>"
        "  </ContactInfo>"
        "</NOCIRequest>"
    )


def submit_ebay_dmca(ctx: dict, evidence: dict) -> SubmissionResult:
    """Submit an eBay VeRO NOCI (Notice of Claimed Infringement).

    Parameters
    ----------
    ctx:
        Dict containing ``threat``, ``client``, and ``asset`` records.
    evidence:
        Dict produced by ``_capture_evidence``; must include ``proof_pdf_url``.

    Returns
    -------
    SubmissionResult
        Populated with an ``EBAY-VeRO-`` prefixed case number and metadata payload.
    """
    settings = get_settings()
    threat = ctx["threat"]
    client = ctx["client"]
    asset = ctx["asset"]

    infringing_url = threat.get("infringing_url") or ""
    original_url = asset.get("thumbnail_url") or asset.get("storage_url") or ""
    evidence_url = evidence.get("proof_pdf_url") or ""
    item_number = _extract_ebay_item_number(infringing_url)

    participant_id = (client.get("vero_participant_id") or "").strip()

    if participant_id:
        return _submit_via_vero_api(
            ctx=ctx,
            participant_id=participant_id,
            infringing_url=infringing_url,
            original_url=original_url,
            evidence_url=evidence_url,
            item_number=item_number,
            settings=settings,
        )

    return _submit_via_browser(
        ctx=ctx,
        evidence=evidence,
        infringing_url=infringing_url,
        original_url=original_url,
        evidence_url=evidence_url,
        item_number=item_number,
        settings=settings,
    )


# ---------------------------------------------------------------------------
# VeRO API path
# ---------------------------------------------------------------------------

def _submit_via_vero_api(
    *,
    ctx: dict,
    participant_id: str,
    infringing_url: str,
    original_url: str,
    evidence_url: str,
    item_number: str | None,
    settings,
) -> SubmissionResult:
    """Submit a NOCI using eBay's VeRO API endpoint."""
    client = ctx["client"]
    asset = ctx["asset"]

    contact_name = client.get("legal_contact_name") or "Authorized Agent"
    contact_email = client.get("legal_contact_email") or ""
    company_name = client.get("company_name") or "SniperIP Client"

    noci_description = _build_noci_description(
        asset,
        infringing_url,
        item_number,
        original_url,
        evidence_url,
        client=client,
    )

    xml_body = _build_vero_xml_noci(
        participant_id=participant_id,
        contact_name=contact_name,
        contact_email=contact_email,
        company_name=company_name,
        item_number=item_number,
        infringing_url=infringing_url,
        original_url=original_url,
        evidence_url=evidence_url,
        noci_description=noci_description,
    )

    vero_endpoint = "https://api.ebay.com/ws/api.dll"
    headers = {
        "X-EBAY-API-CALL-NAME": "SubmitVeROReport",
        "X-EBAY-API-SITEID": "0",
        "X-EBAY-API-COMPATIBILITY-LEVEL": "967",
        "X-EBAY-API-APP-NAME": "SniperIP",
        "Content-Type": "application/xml",
    }

    if settings.takedown_test_mode_no_submit:
        logger.info("eBay VeRO API: test mode – skipping real submission.")
        return SubmissionResult(
            case_number=f"TEST-EBAY-VeRO-{uuid.uuid4().hex[:10].upper()}",
            payload={
                "mode": "ebay_vero_api_test_mode",
                "submitted_at": _utcnow_iso(),
                "endpoint": vero_endpoint,
                "infringing_url": infringing_url,
                "item_number": item_number,
                "original_url": original_url,
                "evidence_url": evidence_url,
                "participant_id": participant_id,
                "test_mode": True,
            },
        )

    logger.info(
        "Submitting eBay VeRO NOCI via API for item %s / %s",
        item_number or "N/A",
        infringing_url,
    )

    with httpx.Client(timeout=45.0) as http:
        response = http.post(vero_endpoint, headers=headers, content=xml_body.encode("utf-8"))
        response.raise_for_status()
        response_text = response.text

    # eBay's XML response may include a ReportID; attempt a simple extraction.
    report_id_match = re.search(r"<ReportID>(\w+)</ReportID>", response_text)
    case_number = (
        report_id_match.group(1)
        if report_id_match
        else f"EBAY-VeRO-{uuid.uuid4().hex[:10].upper()}"
    )
    logger.info("eBay VeRO API submission successful. Case: %s", case_number)

    return SubmissionResult(
        case_number=case_number,
        payload={
            "mode": "ebay_vero_api",
            "submitted_at": _utcnow_iso(),
            "endpoint": vero_endpoint,
            "infringing_url": infringing_url,
            "item_number": item_number,
            "original_url": original_url,
            "evidence_url": evidence_url,
            "participant_id": participant_id,
            "response_excerpt": response_text[:2000],
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
    item_number: str | None,
    settings,
) -> SubmissionResult:
    """Fill the eBay VeRO public NOCI web form using Playwright."""
    client = ctx["client"]
    asset = ctx["asset"]

    contact_name = client.get("legal_contact_name") or "Authorized Agent"
    contact_email = client.get("legal_contact_email") or ""
    company_name = client.get("company_name") or "SniperIP Client"
    noci_description = _build_noci_description(
        asset, infringing_url, item_number, original_url, evidence_url, client=client
    )

    form_url = _EBAY_VERO_FORM_URL

    with sync_playwright() as playwright:
        browser, context, page = _open_hardened_page(playwright)
        try:
            logger.info("Navigating to eBay VeRO form: %s", form_url)
            page.goto(form_url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(2000)

            # Contact information
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

            # eBay item number
            if item_number:
                _fill_first(page, [
                    "input[name='item_id']",
                    "input[name='itemId']",
                    "input[name='item_number']",
                    "input[id*='item']",
                    "input[placeholder*='item']",
                ], item_number)

            # Infringing URL
            _fill_first(page, [
                "input[name='infringing_url']",
                "input[name='listing_url']",
                "input[id*='infringing']",
                "input[id*='listing']",
                "textarea[name='infringing_url']",
            ], infringing_url)

            # Original work URL
            _fill_first(page, [
                "input[name='original_url']",
                "input[name='original_work_url']",
                "input[id*='original']",
            ], original_url)

            # NOCI description / details
            _fill_first(page, [
                "textarea[name='description']",
                "textarea[name='details']",
                "textarea[name='notes']",
                "textarea[id*='description']",
                "textarea[id*='detail']",
                "textarea",
            ], noci_description)

            # Upload evidence PDF
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
                    logger.info("Evidence PDF uploaded to eBay VeRO form.")
            except Exception as exc:
                logger.warning("Could not attach evidence PDF to eBay VeRO form: %s", exc)

            # Checkboxes
            try:
                checkboxes = page.locator("input[type='checkbox']")
                for idx in range(checkboxes.count()):
                    checkbox = checkboxes.nth(idx)
                    if not checkbox.is_checked():
                        checkbox.check(force=True)
            except Exception as exc:
                logger.warning("Could not check eBay VeRO form checkboxes: %s", exc)

            # CAPTCHA
            site_key = _extract_sitekey(page)
            if site_key:
                logger.info("CAPTCHA detected on eBay VeRO form; solving via 2Captcha.")
                captcha_token = _solve_recaptcha_v2(site_key, page.url)
                _inject_recaptcha_token(page, captcha_token)

            if settings.takedown_test_mode_no_submit:
                page.screenshot(path="pre_submit_ebay_vero_test_mode.png", full_page=True)
                return SubmissionResult(
                    case_number=f"TEST-EBAY-VeRO-{uuid.uuid4().hex[:10].upper()}",
                    payload={
                        "mode": "ebay_vero_browser_form_test_mode",
                        "form_url": form_url,
                        "final_url": page.url,
                        "submitted_at": _utcnow_iso(),
                        "infringing_url": infringing_url,
                        "item_number": item_number,
                        "original_url": original_url,
                        "evidence_url": evidence_url,
                        "test_mode": True,
                    },
                )

            if not _click_first(page, [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Submit')",
                "button:has-text('Send')",
                "button:has-text('Report')",
                "button:has-text('Continue')",
            ]):
                raise RuntimeError("Could not find a submit button on the eBay VeRO NOCI form.")

            try:
                page.wait_for_load_state("networkidle", timeout=30000)
            except PlaywrightTimeoutError:
                pass
            page.wait_for_timeout(2500)

            content = page.content().lower()
            success = any(
                phrase in content
                for phrase in ("thank you", "submitted", "received", "reference", "case number", "report id", "noci")
            ) or page.url != form_url

            if not success:
                raise RuntimeError("eBay VeRO NOCI form submission could not be verified as successful.")

            case_number = _extract_case_number(page.content()) or f"EBAY-VeRO-{uuid.uuid4().hex[:10].upper()}"
            logger.info("eBay VeRO browser form submission successful. Case: %s", case_number)

            return SubmissionResult(
                case_number=case_number,
                payload={
                    "mode": "ebay_vero_browser_form",
                    "form_url": form_url,
                    "final_url": page.url,
                    "submitted_at": _utcnow_iso(),
                    "infringing_url": infringing_url,
                    "item_number": item_number,
                    "original_url": original_url,
                    "evidence_url": evidence_url,
                },
            )
        finally:
            context.close()
            browser.close()
