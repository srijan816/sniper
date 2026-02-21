"""Listing intel extraction for seller/support/gateway signals."""
from __future__ import annotations

from dataclasses import dataclass
import re

import httpx


EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", flags=re.IGNORECASE | re.DOTALL)
GATEWAY_ID_RE = re.compile(
    r"(?:payment[_-]?gateway(?:[_-]?id)?|gateway[_-]?id)[\s\"'=:\-]*([a-zA-Z0-9_-]{4,})",
    flags=re.IGNORECASE,
)


@dataclass
class ListingIntel:
    seller_name: str | None = None
    support_email: str | None = None
    payment_gateway_id: str | None = None


KNOWN_GATEWAY_MARKERS = (
    "shopify_payments",
    "stripe",
    "paypal",
    "braintree",
    "adyen",
    "klarna",
    "razorpay",
    "square",
)


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    value = re.sub(r"\s+", " ", text).strip()
    return value or None


def _extract_support_email(html: str) -> str | None:
    matches = EMAIL_RE.findall(html)
    if not matches:
        return None

    ranked: list[str] = []
    fallback: list[str] = []
    for email in matches:
        lowered = email.lower()
        if lowered in ranked or lowered in fallback:
            continue
        if any(prefix in lowered for prefix in ("support@", "help@", "contact@", "legal@", "abuse@", "dmca@")):
            ranked.append(lowered)
        else:
            fallback.append(lowered)

    if ranked:
        return ranked[0]
    return fallback[0] if fallback else None


def _extract_seller_name(html: str, hinted_seller_name: str | None) -> str | None:
    cleaned_hint = _clean(hinted_seller_name)
    if cleaned_hint:
        return cleaned_hint

    title_match = TITLE_RE.search(html)
    if not title_match:
        return None
    title = _clean(re.sub(r"<[^>]+>", "", title_match.group(1)))
    if not title:
        return None

    # Keep seller identity compact and avoid full marketing titles.
    return title[:120]


def _extract_gateway_id(html: str) -> str | None:
    match = GATEWAY_ID_RE.search(html)
    if match:
        return _clean(match.group(1))

    lowered = html.lower()
    for marker in KNOWN_GATEWAY_MARKERS:
        if marker in lowered:
            return marker
    return None


def fetch_listing_intel(listing_url: str, hinted_seller_name: str | None = None) -> ListingIntel:
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            response = client.get(listing_url)
            response.raise_for_status()
            html = response.text or ""
    except Exception:
        return ListingIntel(seller_name=_clean(hinted_seller_name))

    return ListingIntel(
        seller_name=_extract_seller_name(html, hinted_seller_name),
        support_email=_extract_support_email(html),
        payment_gateway_id=_extract_gateway_id(html),
    )
