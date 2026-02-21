"""Discovery worker: SerpApi radar + whitelist + verification pipeline."""
from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse
import uuid

from app.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import get_supabase_client
from app.services.blacklist_store import BadActorSignals, is_known_bad_actor, record_bad_actor
from app.services.listing_intel import fetch_listing_intel
from app.services.serpapi_service import filter_whitelisted, search_google_lens
from app.services.vector_store import find_similar_assets
from app.services.vision import embedding_from_image_url
from app.workers.notifications import send_upgrade_email
from app.workers.vectorize import ensure_asset_vectorized


def _db():
    db = get_supabase_client()
    if db is None:
        raise RuntimeError("Supabase is not configured.")
    return db


def _host(url: str) -> str:
    return (urlparse(url).netloc or "").lower().strip()


def _already_known(asset_id: str, infringing_url: str) -> bool:
    rows = (
        _db()
        .table("threats")
        .select("id")
        .eq("asset_id", asset_id)
        .eq("infringing_url", infringing_url)
        .limit(1)
        .execute()
        .data
        or []
    )
    return bool(rows)


def _create_threat(asset_id: str, infringing_url: str, host_domain: str, similarity: float) -> str:
    threat_id = str(uuid.uuid4())
    _db().table("threats").insert(
        {
            "id": threat_id,
            "asset_id": asset_id,
            "infringing_url": infringing_url,
            "host_domain": host_domain,
            "similarity_score": similarity,
            "status": "DISCOVERED",
            "discovered_at": datetime.utcnow().isoformat(),
        }
    ).execute()
    _db().table("audit_logs").insert(
        {
            "threat_id": threat_id,
            "old_status": None,
            "new_status": "DISCOVERED",
            "changed_by": "SYSTEM",
        }
    ).execute()
    return threat_id


def _safe_known_bad_actor(signals: BadActorSignals) -> bool:
    try:
        return is_known_bad_actor(signals)
    except Exception:
        return False


def _safe_record_bad_actor(signals: BadActorSignals):
    try:
        record_bad_actor(signals)
    except Exception:
        # Discovery should continue even if blacklist persistence fails.
        return


@celery_app.task(name="app.workers.discovery.run_discovery_all")
def run_discovery_all():
    """Periodic task: run discovery for all active paid clients."""
    clients = (
        _db()
        .table("clients")
        .select("id")
        .neq("subscription_tier", "FREE")
        .gt("monthly_threat_limit", 0)
        .execute()
        .data
        or []
    )
    for client in clients:
        run_discovery_for_client.delay(client["id"])
    return {"clients_queued": len(clients)}


@celery_app.task(name="app.workers.discovery.run_discovery_for_client")
def run_discovery_for_client(client_id: str):
    """Run discovery for a single client with quota enforcement."""
    settings = get_settings()
    client_rows = _db().table("clients").select("*").eq("id", client_id).limit(1).execute().data or []
    if not client_rows:
        raise RuntimeError(f"Client {client_id} not found.")
    client = client_rows[0]

    current = int(client.get("current_month_count") or 0)
    limit = int(client.get("monthly_threat_limit") or 0)
    if limit <= 0 or current >= limit:
        email = client.get("legal_contact_email")
        if email:
            send_upgrade_email.delay(email, client.get("company_name") or "there")
        return {"client_id": client_id, "status": "quota_exceeded", "current": current, "limit": limit}

    assets = (
        _db()
        .table("assets")
        .select("*")
        .eq("client_id", client_id)
        .eq("status", "ACTIVE")
        .execute()
        .data
        or []
    )
    whitelist = client.get("whitelist_domains") or []
    created = 0

    for asset in assets:
        if current + created >= limit:
            break
        asset_id = asset["id"]
        ensure_asset_vectorized(asset_id)
        source_url = asset.get("thumbnail_url") if (asset.get("asset_type") or "").upper() == "VIDEO" else asset.get("storage_url")
        if not source_url:
            continue

        candidates = filter_whitelisted(search_google_lens(source_url), whitelist)
        for candidate in candidates:
            if current + created >= limit:
                break
            if not candidate.image_url:
                continue
            if _already_known(asset_id, candidate.listing_url):
                continue

            listing_intel = fetch_listing_intel(candidate.listing_url, candidate.seller_name)
            actor_signals = BadActorSignals(
                host_domain=_host(candidate.listing_url),
                seller_name=listing_intel.seller_name,
                support_email=listing_intel.support_email,
                payment_gateway_id=listing_intel.payment_gateway_id,
            )
            blacklist_hit = _safe_known_bad_actor(actor_signals)

            candidate_embedding = embedding_from_image_url(candidate.image_url)
            matches = find_similar_assets(candidate_embedding, client_id=client_id, limit=1)
            if not matches:
                continue
            best = matches[0]
            if best.asset_id != asset_id:
                continue

            threshold = settings.similarity_threshold - 0.07 if blacklist_hit else settings.similarity_threshold
            threshold = max(0.80, threshold)
            if best.similarity < threshold:
                continue

            stored_similarity = best.similarity
            if blacklist_hit and stored_similarity < settings.similarity_threshold:
                stored_similarity = settings.similarity_threshold + 0.01

            _create_threat(
                asset_id=asset_id,
                infringing_url=candidate.listing_url,
                host_domain=_host(candidate.listing_url),
                similarity=stored_similarity,
            )
            _safe_record_bad_actor(actor_signals)
            created += 1

    if created:
        _db().table("clients").update({"current_month_count": current + created}).eq("id", client_id).execute()

    return {"client_id": client_id, "threats_created": created, "quota_remaining": max(limit - (current + created), 0)}
