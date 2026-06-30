"""Free scan PLG endpoint — public, rate-limited, lead-capture."""
import base64
import hashlib
import logging
import uuid
from datetime import datetime
from io import BytesIO
from typing import List, Optional
from urllib.parse import urlparse

import httpx
import imagehash
import numpy as np
import resend
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from PIL import Image as PILImage, ImageFilter

from app.core.limiter import get_real_ip, limiter

from app.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import get_supabase_client
from app.services.serpapi_service import search_google_lens
from app.services.vision import embedding_from_image_bytes

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_platform(domain: str) -> str:
    d = domain.lower()
    if "myshopify.com" in d or "shopify.com" in d:
        return "Shopify"
    if "amazon." in d:
        return "Amazon"
    if "ebay." in d:
        return "eBay"
    if "tiktok.com" in d or "tiktokshop" in d:
        return "TikTok Shop"
    if "instagram.com" in d or "facebook.com" in d:
        return "Meta"
    return "Independent Store"


def _obscure_domain(domain: str) -> str:
    """Obscure ~60% of the domain characters with '*'."""
    if not domain:
        return domain
    # Split off TLD to preserve it readable
    parts = domain.rsplit(".", 1)
    base = parts[0]
    tld = f".{parts[1]}" if len(parts) == 2 else ""

    total = len(base)
    keep = max(2, int(total * 0.40))
    keep_start = keep // 2
    keep_end = keep - keep_start

    if keep_end > 0:
        obscured = base[:keep_start] + "*" * (total - keep_start - keep_end) + base[total - keep_end:]
    else:
        obscured = base[:keep_start] + "*" * (total - keep_start)

    return obscured + tld


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0.0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def _blurred_thumbnail_b64(image_bytes: bytes) -> Optional[str]:
    """Return a base64 data-URI of a blurred 100x100 thumbnail, or None on failure."""
    try:
        with PILImage.open(BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            img = img.resize((100, 100), PILImage.LANCZOS)
            img = img.filter(ImageFilter.GaussianBlur(radius=5))
            buf = BytesIO()
            img.save(buf, format="JPEG")
            encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{encoded}"
    except Exception as exc:
        logger.debug("Thumbnail generation failed: %s", exc)
        return None


def _upload_scan_to_storage(db, file_bytes: bytes, scan_id: str, content_type: str) -> str:
    """Upload scan image to Supabase storage and return the public URL."""
    bucket = "scans"
    path = f"scans/{scan_id}.jpg"
    storage = db.storage.from_(bucket)
    storage.upload(path, file_bytes, {"content-type": content_type, "upsert": "true"})
    public_url = storage.get_public_url(path)
    if isinstance(public_url, dict):
        return public_url.get("publicUrl") or public_url.get("public_url") or path
    return str(public_url)


def _extract_host(url: str) -> str:
    return (urlparse(url).netloc or "").lower().strip()


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@celery_app.task(name="app.api.scan.send_scan_followup_email")
def send_scan_followup_email(lead_email: str, matches_found: int) -> dict:
    """Send a follow-up email to a free-scan lead after 24 hours."""
    settings = get_settings()
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set — skipping scan follow-up email to %s", lead_email)
        return {"status": "skipped", "reason": "no_resend_key"}

    resend.api_key = settings.resend_api_key
    frontend_url = settings.frontend_url or "https://sniperip.com"

    resend.Emails.send(
        {
            "from": settings.notification_from_email,
            "to": [lead_email],
            "subject": f"We found {matches_found} counterfeits of your product",
            "html": (
                f"<p>Hi there,</p>"
                f"<p>Yesterday you ran a free scan on SniperIP and we found "
                f"<strong>{matches_found}</strong> potential counterfeit listing(s) of your product.</p>"
                f"<p>Sign up to unlock the full URLs, platform details, and our one-click automated takedown tools.</p>"
                f'<p><a href="{frontend_url}/auth/login" '
                f'style="display:inline-block;padding:12px 24px;background:#10D94B;color:#1A1C24;'
                f'font-weight:700;border-radius:6px;text-decoration:none;">'
                f"Unlock Full Results &amp; Remove Listings &rarr;</a></p>"
                f"<p>The SniperIP Team</p>"
            ),
        }
    )
    return {"status": "sent", "to": lead_email}


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/free")
@limiter.limit("3/day")
async def free_scan(
    request: Request,
    file: UploadFile = File(...),
    email: str = Form(...),
    website: Optional[str] = Form(None),
):
    """
    Public free-scan endpoint. Accepts a product image, runs Google Lens discovery,
    computes visual similarity, and returns blurred/obscured results for lead capture.
    Rate-limited to 3 requests per day per IP.
    """
    # 1. Validate file type
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")

    # 2. Read file bytes
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # 3. Compute pHash
    try:
        phash_value = str(imagehash.phash(PILImage.open(BytesIO(file_bytes))))
    except Exception as exc:
        logger.warning("pHash computation failed: %s", exc)
        phash_value = hashlib.sha256(file_bytes).hexdigest()[:16]

    # 4. Determine requester IP
    ip_address = get_real_ip(request)

    # 5. Store lead record
    scan_id = str(uuid.uuid4())
    db = get_supabase_client()

    lead_row = {
        "id": scan_id,
        "email": email,
        "ip_address": ip_address,
        "image_hash": phash_value,
        "matches_found": 0,
        "created_at": datetime.utcnow().isoformat(),
    }

    if db is not None:
        try:
            db.table("leads").insert(lead_row).execute()
        except Exception as exc:
            logger.warning("Failed to store lead record: %s", exc)

    # 6. Generate embedding for the original image
    try:
        original_embedding = embedding_from_image_bytes(file_bytes)
    except Exception as exc:
        logger.warning("Embedding generation failed for scan %s: %s", scan_id, exc)
        original_embedding = None

    # 7. Upload to Supabase storage, get public URL
    image_url: Optional[str] = None
    if db is not None:
        try:
            image_url = _upload_scan_to_storage(db, file_bytes, scan_id, content_type)
        except Exception as exc:
            logger.warning("Storage upload failed for scan %s: %s", scan_id, exc)

    if not image_url:
        raise HTTPException(
            status_code=503,
            detail="Image storage is unavailable. Please try again later.",
        )

    # 8. Run Google Lens search
    try:
        candidates = search_google_lens(image_url)
    except Exception as exc:
        logger.error("SerpApi search failed for scan %s: %s", scan_id, exc)
        candidates = []

    # 9. Filter out prospect's own website and cap at top 10
    own_host: Optional[str] = None
    if website:
        own_host = _extract_host(website) or website.lower().strip()

    filtered_candidates = []
    for c in candidates:
        if own_host and (c.host_domain == own_host or c.host_domain.endswith(f".{own_host}")):
            continue
        filtered_candidates.append(c)

    top_candidates = filtered_candidates[:10]

    # 10. Score each candidate via embedding cosine similarity
    results = []
    for candidate in top_candidates:
        candidate_image_url = candidate.image_url
        if not candidate_image_url:
            continue

        # Download candidate image
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get(candidate_image_url)
                resp.raise_for_status()
                candidate_bytes = resp.content
        except Exception as exc:
            logger.debug("Could not download candidate image %s: %s", candidate_image_url, exc)
            continue

        # Compute similarity
        similarity = 0.0
        if original_embedding is not None:
            try:
                candidate_embedding = embedding_from_image_bytes(candidate_bytes)
                similarity = _cosine_similarity(original_embedding, candidate_embedding)
            except Exception as exc:
                logger.debug("Embedding failed for candidate %s: %s", candidate_image_url, exc)
                continue

        if similarity < 0.60:
            continue

        # Generate blurred thumbnail
        thumbnail_b64 = _blurred_thumbnail_b64(candidate_bytes)

        # Build result entry
        domain = candidate.host_domain
        results.append(
            {
                "platform": _detect_platform(domain),
                "country": "Unknown",
                "similarity_score": round(similarity, 4),
                "thumbnail_url": thumbnail_b64,
                "domain_hint": _obscure_domain(domain),
            }
        )

    # Sort by similarity descending
    results.sort(key=lambda r: r["similarity_score"], reverse=True)

    total_matches = len(results)
    high_confidence = sum(1 for r in results if r["similarity_score"] >= 0.80)

    # 11. Update lead record with matches_found
    if db is not None:
        try:
            db.table("leads").update({"matches_found": total_matches}).eq("id", scan_id).execute()
        except Exception as exc:
            logger.warning("Failed to update lead matches_found for %s: %s", scan_id, exc)

    # 12. Queue follow-up email (runs after 24 hours)
    try:
        send_scan_followup_email.apply_async(
            args=[email, total_matches],
            countdown=86400,
        )
    except Exception as exc:
        logger.warning("Could not queue follow-up email for %s: %s", email, exc)

    return {
        "total_matches_found": total_matches,
        "high_confidence_matches": high_confidence,
        "results": results,
        "email_captured": True,
        "cta_message": "Unlock full URLs and automated takedowns",
    }
