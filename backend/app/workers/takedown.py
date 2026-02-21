"""Takedown execution worker (evidence locker + platform fallback + retry/DLQ)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
import hashlib
import re
import textwrap
import time
import traceback
import uuid
from urllib.parse import parse_qs, urlparse

import httpx
from PIL import Image, ImageDraw, ImageOps
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
import whois

from app.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import get_supabase_client
from app.services.notification_service import send_generic_dmca_notice
from app.workers.notifications import send_slack_alert, send_takedown_confirmation

MAX_RETRIES = 5
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


@dataclass
class SubmissionResult:
    case_number: str
    payload: dict


def _db():
    db = get_supabase_client()
    if db is None:
        raise RuntimeError("Supabase is not configured.")
    return db


def _table_missing(exc: Exception) -> bool:
    message = str(exc)
    return "PGRST205" in message or "Could not find the table" in message


def _with_table(candidates: tuple[str, ...], fn):
    last_error: Exception | None = None
    for table_name in candidates:
        try:
            return fn(table_name)
        except Exception as exc:
            if _table_missing(exc):
                last_error = exc
                continue
            raise
    raise RuntimeError(f"Required table not found: {last_error}")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _update_threat_status(threat_id: str, new_status: str):
    rows = _db().table("threats").select("id,status").eq("id", threat_id).limit(1).execute().data or []
    if not rows:
        return
    old_status = rows[0].get("status")
    if old_status == new_status:
        return
    _db().table("threats").update({"status": new_status}).eq("id", threat_id).execute()
    _write_audit_log(threat_id, old_status, new_status, "SYSTEM")


def _fetch_takedown(takedown_id: str) -> tuple[str, dict]:
    def _load(table_name: str):
        return _db().table(table_name).select("*").eq("id", takedown_id).limit(1).execute()

    res = _with_table(("takedown_requests", "takedowns"), _load)
    rows = res.data or []
    if not rows:
        raise RuntimeError(f"Takedown {takedown_id} not found.")

    for candidate in ("takedown_requests", "takedowns"):
        try:
            check = _db().table(candidate).select("id").eq("id", takedown_id).limit(1).execute().data or []
            if check:
                return candidate, rows[0]
        except Exception as exc:
            if not _table_missing(exc):
                raise
    return "takedown_requests", rows[0]


def _update_takedown(table_name: str, takedown_id: str, updates: dict):
    _db().table(table_name).update(updates).eq("id", takedown_id).execute()


def _insert_dlq(takedown_id: str, reason: str, stack_trace: str):
    payload = {
        "id": str(uuid.uuid4()),
        "takedown_id": takedown_id,
        "error_reason": f"{reason}\n\n{stack_trace}"[:60000],
        "failed_at": _utcnow_iso(),
    }

    def _insert(table_name: str):
        return _db().table(table_name).insert(payload).execute()

    _with_table(("dead_letter_queue", "dlq"), _insert)


def _fetch_context(threat_id: str) -> dict:
    threat_rows = _db().table("threats").select("*").eq("id", threat_id).limit(1).execute().data or []
    if not threat_rows:
        raise RuntimeError(f"Threat {threat_id} not found.")
    threat = threat_rows[0]

    asset_rows = _db().table("assets").select("*").eq("id", threat["asset_id"]).limit(1).execute().data or []
    if not asset_rows:
        raise RuntimeError(f"Asset {threat['asset_id']} not found for threat {threat_id}.")
    asset = asset_rows[0]

    client_rows = _db().table("clients").select("*").eq("id", asset["client_id"]).limit(1).execute().data or []
    if not client_rows:
        raise RuntimeError(f"Client {asset['client_id']} not found.")
    client = client_rows[0]

    return {"threat": threat, "asset": asset, "client": client}


def _fill_first(page, selectors: list[str], value: str) -> bool:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if locator.count() == 0:
                continue
            locator.fill(value)
            return True
        except Exception:
            try:
                locator.click()
                locator.press("ControlOrMeta+a")
                locator.type(value)
                return True
            except Exception:
                continue
    return False


def _click_first(page, selectors: list[str]) -> bool:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if locator.count() == 0:
                continue
            locator.click(timeout=5000)
            return True
        except Exception:
            continue
    return False


def _extract_sitekey(page) -> str | None:
    try:
        data_key = page.locator("[data-sitekey]").first
        if data_key.count() > 0:
            value = data_key.get_attribute("data-sitekey")
            if value:
                return value
    except Exception:
        pass

    try:
        iframes = page.locator("iframe[src*='recaptcha']")
        for idx in range(min(iframes.count(), 5)):
            src = iframes.nth(idx).get_attribute("src") or ""
            if "?" not in src:
                continue
            query = parse_qs(urlparse(src).query)
            for key in ("k", "sitekey", "render"):
                values = query.get(key)
                if values and values[0]:
                    return values[0]
    except Exception:
        pass

    return None


def _solve_recaptcha_v2(site_key: str, page_url: str) -> str:
    settings = get_settings()
    if not settings.two_captcha_api_key:
        raise RuntimeError("2Captcha is required but TWO_CAPTCHA_API_KEY is not configured.")

    with httpx.Client(timeout=60.0) as client:
        create = client.post(
            "https://2captcha.com/in.php",
            data={
                "key": settings.two_captcha_api_key,
                "method": "userrecaptcha",
                "googlekey": site_key,
                "pageurl": page_url,
                "json": 1,
            },
        )
        create.raise_for_status()
        create_payload = create.json()
        if create_payload.get("status") != 1:
            raise RuntimeError(f"2Captcha create failed: {create_payload}")

        captcha_id = create_payload.get("request")
        for _ in range(24):
            time.sleep(5)
            fetch = client.get(
                "https://2captcha.com/res.php",
                params={
                    "key": settings.two_captcha_api_key,
                    "action": "get",
                    "id": captcha_id,
                    "json": 1,
                },
            )
            fetch.raise_for_status()
            payload = fetch.json()
            if payload.get("status") == 1:
                return str(payload.get("request"))
            if payload.get("request") != "CAPCHA_NOT_READY":
                raise RuntimeError(f"2Captcha solve failed: {payload}")

    raise RuntimeError("2Captcha timed out while solving captcha.")


def _inject_recaptcha_token(page, token: str):
    page.evaluate(
        """
        (captchaToken) => {
          let textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
          if (!textarea) {
            textarea = document.createElement('textarea');
            textarea.name = 'g-recaptcha-response';
            textarea.style.display = 'none';
            document.body.appendChild(textarea);
          }
          textarea.value = captchaToken;
          textarea.dispatchEvent(new Event('input', { bubbles: true }));
          textarea.dispatchEvent(new Event('change', { bubbles: true }));
        }
        """,
        token,
    )


def _extract_case_number(page_content: str) -> str | None:
    patterns = [
        r"(?:case|reference|ticket)\s*(?:number|id)?\s*[:#-]?\s*([A-Z0-9-]{6,})",
        r"\b([A-Z]{2,6}-\d{4,}-[A-Z0-9]{3,})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, page_content, flags=re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return None


def _public_url(value) -> str:
    if isinstance(value, dict):
        return value.get("publicUrl") or value.get("public_url") or ""
    return str(value or "")


def _upload_storage_bytes(path: str, content: bytes, content_type: str, bucket_candidates: list[str]) -> str:
    unique = []
    for bucket in bucket_candidates:
        if bucket and bucket not in unique:
            unique.append(bucket)

    last_error: Exception | None = None
    for bucket in unique:
        try:
            storage = _db().storage.from_(bucket)
            storage.upload(path, content, {"content-type": content_type, "upsert": "true"})
            return _public_url(storage.get_public_url(path))
        except Exception as exc:
            last_error = exc
            continue

    raise RuntimeError(f"Failed to upload artifact to Supabase Storage: {last_error}")


def _build_proof_pdf(
    screenshot_png: bytes,
    *,
    threat_id: str,
    infringing_url: str,
    host_domain: str,
    similarity_score: float,
    captured_at: str,
) -> bytes:
    screenshot = Image.open(BytesIO(screenshot_png)).convert("RGB")

    max_content_width = 1400
    rendered = ImageOps.contain(screenshot, (max_content_width - 80, 1600))

    header_lines = [
        "SniperIP - Proof of Infringement",
        f"Threat ID: {threat_id}",
        f"Captured At (UTC): {captured_at}",
        f"Host Domain: {host_domain}",
        f"Similarity Score: {similarity_score:.4f}",
        f"Infringing URL: {infringing_url}",
    ]

    wrapped_url = textwrap.wrap(header_lines[-1], width=125)
    lines = header_lines[:-1] + wrapped_url

    line_height = 28
    header_height = 80 + (len(lines) * line_height)
    canvas_height = header_height + rendered.height + 80

    canvas = Image.new("RGB", (max_content_width, canvas_height), "white")
    draw = ImageDraw.Draw(canvas)

    y = 30
    for idx, line in enumerate(lines):
        if idx == 0:
            draw.text((30, y), line, fill=(26, 28, 36))
        else:
            draw.text((30, y), line, fill=(60, 66, 80))
        y += line_height

    canvas.paste(rendered, (40, header_height))

    out = BytesIO()
    canvas.save(out, format="PDF", resolution=110.0)
    return out.getvalue()


def _capture_evidence(ctx: dict) -> dict:
    settings = get_settings()
    threat = ctx["threat"]
    client = ctx["client"]

    threat_id = threat["id"]
    client_id = client["id"]
    infringing_url = threat.get("infringing_url") or ""
    if not infringing_url:
        raise RuntimeError("Threat has no infringing_url; cannot capture evidence.")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=settings.playwright_headless)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(infringing_url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(1500)
            screenshot = page.screenshot(full_page=True, type="png")
        finally:
            context.close()
            browser.close()

    if not screenshot:
        raise RuntimeError("Failed to capture infringement screenshot.")

    captured_at = _utcnow_iso()
    host_domain = threat.get("host_domain") or (urlparse(infringing_url).netloc or "")
    similarity = float(threat.get("similarity_score") or 0.0)

    proof_pdf = _build_proof_pdf(
        screenshot,
        threat_id=threat_id,
        infringing_url=infringing_url,
        host_domain=host_domain,
        similarity_score=similarity,
        captured_at=captured_at,
    )

    stamp = captured_at.replace(":", "-").replace("+", "Z")
    screenshot_path = f"{client_id}/threats/{threat_id}/{stamp}-infringing.png"
    pdf_path = f"{client_id}/threats/{threat_id}/{stamp}-proof-of-infringement.pdf"

    buckets = [settings.evidence_storage_bucket, settings.supabase_storage_bucket]
    screenshot_url = _upload_storage_bytes(screenshot_path, screenshot, "image/png", buckets)
    proof_pdf_url = _upload_storage_bytes(pdf_path, proof_pdf, "application/pdf", buckets)

    return {
        "captured_at": captured_at,
        "infringing_url": infringing_url,
        "screenshot_url": screenshot_url,
        "proof_pdf_url": proof_pdf_url,
        "screenshot_sha256": hashlib.sha256(screenshot).hexdigest(),
    }


def _download_bytes(url: str) -> bytes:
    with httpx.Client(timeout=45.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content


def _attach_loa_file_if_present(page, loa_url: str) -> bool:
    loa_bytes = _download_bytes(loa_url)
    inputs = page.locator("input[type='file']")
    for idx in range(inputs.count()):
        try:
            inputs.nth(idx).set_input_files(
                [
                    {
                        "name": "letter-of-authorization.pdf",
                        "mimeType": "application/pdf",
                        "buffer": loa_bytes,
                    }
                ]
            )
            return True
        except Exception:
            continue
    return False


def _is_shopify_listing(infringing_url: str, host_domain: str | None) -> bool:
    domain = (host_domain or "").lower()
    if domain.endswith("myshopify.com"):
        return True

    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            response = client.get(infringing_url)
            response.raise_for_status()
            html = response.text.lower()
    except Exception:
        return False

    markers = (
        "cdn.shopify.com",
        "shopify.theme",
        "x-shopid",
        "shopify-payment-button",
        "myshopify.com",
    )
    return any(marker in html for marker in markers)


def _build_summary(original_url: str, infringing_url: str, loa_url: str, evidence_url: str) -> str:
    return (
        "I represent the rights holder and request removal of unauthorized copyrighted content. "
        f"Original asset URL: {original_url}. "
        f"Infringing listing URL: {infringing_url}. "
        f"Authorization on file: {loa_url}. "
        f"Proof of infringement packet: {evidence_url}."
    )


def _submit_shopify_dmca(ctx: dict, evidence: dict) -> SubmissionResult:
    settings = get_settings()
    threat = ctx["threat"]
    client = ctx["client"]
    asset = ctx["asset"]

    form_url = settings.shopify_dmca_form_url
    company_name = client.get("company_name") or "SniperIP Client"
    contact_name = client.get("legal_contact_name") or "Legal Contact"
    contact_email = client.get("legal_contact_email") or ""
    loa_url = client.get("loa_document_url") or ""
    if not loa_url:
        raise RuntimeError("Client LOA document is missing. Upload LOA before enforcement.")

    infringing_url = threat.get("infringing_url") or ""
    original_url = asset.get("thumbnail_url") or asset.get("storage_url") or ""
    summary = _build_summary(original_url, infringing_url, loa_url, evidence["proof_pdf_url"])

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=settings.playwright_headless)
        context = browser.new_context()
        page = context.new_page()
        loa_attached = False
        try:
            page.goto(form_url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(1200)

            _fill_first(page, [
                "input[name='name']",
                "input[name='full_name']",
                "input[id*='name']",
                "input[autocomplete='name']",
            ], contact_name)
            _fill_first(page, [
                "input[name='email']",
                "input[type='email']",
                "input[autocomplete='email']",
            ], contact_email)
            _fill_first(page, [
                "input[name='company']",
                "input[id*='company']",
                "input[autocomplete='organization']",
            ], company_name)
            _fill_first(page, [
                "input[name='url']",
                "input[name='original_url']",
                "input[id*='original']",
                "textarea[name='original']",
            ], original_url)
            _fill_first(page, [
                "input[name='infringing_url']",
                "input[id*='infringing']",
                "textarea[name='infringing']",
                "textarea[id*='infringing']",
            ], infringing_url)
            _fill_first(page, [
                "textarea[name='description']",
                "textarea[name='details']",
                "textarea[id*='description']",
                "textarea[id*='detail']",
                "textarea",
            ], summary)

            try:
                loa_attached = _attach_loa_file_if_present(page, loa_url)
            except Exception:
                loa_attached = False

            try:
                checkboxes = page.locator("input[type='checkbox']")
                for idx in range(checkboxes.count()):
                    checkbox = checkboxes.nth(idx)
                    if not checkbox.is_checked():
                        checkbox.check(force=True)
            except Exception:
                pass

            site_key = _extract_sitekey(page)
            if site_key:
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
                raise RuntimeError("Could not find a submit button on Shopify legal form.")

            try:
                page.wait_for_load_state("networkidle", timeout=30000)
            except PlaywrightTimeoutError:
                pass
            page.wait_for_timeout(2500)

            content = page.content().lower()
            success = any(
                phrase in content
                for phrase in (
                    "thank you",
                    "submitted",
                    "received",
                    "reference",
                    "case number",
                )
            ) or page.url != form_url

            if not success:
                raise RuntimeError("Form submission could not be verified as successful.")

            case_number = _extract_case_number(page.content()) or f"SHP-{uuid.uuid4().hex[:10].upper()}"
            payload = {
                "mode": "shopify_form",
                "form_url": form_url,
                "final_url": page.url,
                "submitted_at": _utcnow_iso(),
                "infringing_url": infringing_url,
                "original_url": original_url,
                "loa_url": loa_url,
                "loa_attached": loa_attached,
                "evidence_proof_pdf_url": evidence["proof_pdf_url"],
            }
            return SubmissionResult(case_number=case_number, payload=payload)
        finally:
            context.close()
            browser.close()


def _root_domain(host_domain: str) -> str:
    host = (host_domain or "").strip().lower().split(":")[0]
    parts = [p for p in host.split(".") if p]
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def _resolve_abuse_contacts(host_domain: str) -> list[str]:
    root_domain = _root_domain(host_domain)
    emails: list[str] = []

    try:
        info = whois.whois(root_domain)
        raw = info.emails
        if raw:
            if isinstance(raw, str):
                raw = [raw]
            for email in raw:
                if not email:
                    continue
                value = email.strip().lower()
                if EMAIL_RE.fullmatch(value) and value not in emails:
                    emails.append(value)
    except Exception:
        pass

    prioritized = [
        email
        for email in emails
        if any(token in email for token in ("abuse@", "dmca@", "legal@", "copyright"))
    ]

    if prioritized:
        contacts = prioritized[:5]
    elif emails:
        contacts = emails[:5]
    else:
        contacts = []

    fallback = [f"abuse@{root_domain}", f"legal@{root_domain}", f"dmca@{root_domain}"]
    for email in fallback:
        if EMAIL_RE.fullmatch(email) and email not in contacts:
            contacts.append(email)
        if len(contacts) >= 5:
            break

    return contacts


def _submit_generic_email_dmca(ctx: dict, evidence: dict) -> SubmissionResult:
    threat = ctx["threat"]
    asset = ctx["asset"]
    client = ctx["client"]

    host_domain = threat.get("host_domain") or (urlparse(threat.get("infringing_url") or "").netloc or "")
    infringing_url = threat.get("infringing_url") or ""
    original_url = asset.get("thumbnail_url") or asset.get("storage_url") or ""
    similarity = float(threat.get("similarity_score") or 0.0)

    loa_url = client.get("loa_document_url") or ""
    if not loa_url:
        raise RuntimeError("Client LOA document is missing. Upload LOA before enforcement.")

    recipients = _resolve_abuse_contacts(host_domain)
    if not recipients:
        raise RuntimeError(f"No abuse contacts discovered for domain: {host_domain}")

    case_number = f"EML-{uuid.uuid4().hex[:10].upper()}"
    subject = f"DMCA Notice: Unauthorized content on {host_domain}"
    html = (
        "<p>Hello Abuse Team,</p>"
        "<p>This is a formal DMCA notice regarding unauthorized use of copyrighted content.</p>"
        "<ul>"
        f"<li>Infringing URL: <a href='{infringing_url}'>{infringing_url}</a></li>"
        f"<li>Original Asset URL: <a href='{original_url}'>{original_url}</a></li>"
        f"<li>Similarity Score: {similarity:.4f}</li>"
        f"<li>Authorization (LOA): <a href='{loa_url}'>{loa_url}</a></li>"
        f"<li>Proof of Infringement PDF: <a href='{evidence['proof_pdf_url']}'>{evidence['proof_pdf_url']}</a></li>"
        "</ul>"
        "<p>Please remove or disable access to the infringing material immediately.</p>"
        "<p>Regards,<br/>SniperIP Enforcement Automation</p>"
    )

    cc = [client.get("legal_contact_email")] if client.get("legal_contact_email") else None
    send_generic_dmca_notice(recipients, subject, html, cc_emails=cc)

    payload = {
        "mode": "generic_email",
        "submitted_at": _utcnow_iso(),
        "infringing_url": infringing_url,
        "original_url": original_url,
        "loa_url": loa_url,
        "recipients": recipients,
        "evidence_proof_pdf_url": evidence["proof_pdf_url"],
    }
    return SubmissionResult(case_number=case_number, payload=payload)


def queue_takedown(takedown_id: str, countdown: int = 0):
    execute_takedown_task.apply_async(args=[takedown_id], countdown=max(0, int(countdown)))


@celery_app.task(name="app.workers.takedown.execute_takedown_task")
def execute_takedown_task(takedown_id: str):
    table_name, takedown = _fetch_takedown(takedown_id)
    threat_id = takedown.get("threat_id")
    retry_count = int(takedown.get("retry_count") or 0)
    status = (takedown.get("status") or "PENDING").upper()

    if status in {"SUBMITTED", "CONFIRMED"}:
        return {"takedown_id": takedown_id, "status": status, "skipped": True}

    context = _fetch_context(threat_id)
    threat = context["threat"]
    client = context["client"]

    requested = (takedown.get("platform") or "").strip().lower()
    if requested in {"shopify", "generic_email"}:
        platform = requested
    else:
        platform = "shopify" if _is_shopify_listing(threat.get("infringing_url") or "", threat.get("host_domain")) else "generic_email"

    try:
        evidence = _capture_evidence(context)

        if platform == "shopify":
            result = _submit_shopify_dmca(context, evidence)
        else:
            result = _submit_generic_email_dmca(context, evidence)

        _update_takedown(
            table_name,
            takedown_id,
            {
                "platform": platform,
                "status": "SUBMITTED",
                "case_number": result.case_number,
                "rpa_payload": {
                    **result.payload,
                    "evidence": evidence,
                },
                "submitted_at": _utcnow_iso(),
            },
        )
        _update_threat_status(threat_id, "TAKEDOWN_SUBMITTED")

        client_email = client.get("legal_contact_email")
        if client_email:
            send_takedown_confirmation.delay(
                client_email,
                threat.get("infringing_url") or "",
                platform,
                result.case_number,
            )

        return {
            "takedown_id": takedown_id,
            "status": "SUBMITTED",
            "platform": platform,
            "case_number": result.case_number,
        }
    except Exception as exc:
        stack = traceback.format_exc()
        next_retry = retry_count + 1

        if next_retry >= MAX_RETRIES:
            _update_takedown(
                table_name,
                takedown_id,
                {
                    "status": "FAILED",
                    "retry_count": next_retry,
                    "rpa_payload": {
                        "error": str(exc),
                        "stack_trace": stack,
                        "failed_at": _utcnow_iso(),
                    },
                },
            )
            _insert_dlq(takedown_id, str(exc), stack)
            send_slack_alert.delay(
                (
                    "SniperIP takedown failed after 5 retries. "
                    f"Threat ID: {threat_id}. Platform: {platform}. Reason: {exc}"
                )
            )
            return {
                "takedown_id": takedown_id,
                "status": "FAILED",
                "retry_count": next_retry,
                "error": str(exc),
            }

        delay = 60 * (2 ** next_retry)
        _update_takedown(
            table_name,
            takedown_id,
            {
                "status": "PENDING",
                "retry_count": next_retry,
                "rpa_payload": {
                    "last_error": str(exc),
                    "last_error_at": _utcnow_iso(),
                },
            },
        )
        queue_takedown(takedown_id, countdown=delay)
        return {
            "takedown_id": takedown_id,
            "status": "RETRY_SCHEDULED",
            "retry_count": next_retry,
            "next_delay_seconds": delay,
            "error": str(exc),
        }
