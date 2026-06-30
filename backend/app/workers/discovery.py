"""Discovery worker: SerpApi radar + whitelist + verification pipeline."""
from __future__ import annotations

import time
from urllib.parse import urlparse

import redis

from app.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import get_supabase_client
from app.services.blacklist_store import BadActorSignals, is_known_bad_actor, record_bad_actor
from app.services.discovery_orchestrator import discover_candidates_for_asset
from app.services.listing_intel import fetch_listing_intel
from app.services.threat_intelligence import enrich_threat_with_explanation
from app.services.threat_store import create_or_get_discovered_threat
from app.services.vision import asset_image_source_url, combined_similarity, download_bytes
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


def _create_threat(asset_id: str, infringing_url: str, host_domain: str, similarity: float, client_id: str) -> tuple[str, bool]:
    return create_or_get_discovered_threat(
        asset_id=asset_id,
        infringing_url=infringing_url,
        host_domain=host_domain,
        similarity_score=similarity,
        client_id=client_id,
    )


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


def _paid_client_ids() -> list[str]:
    rows = (
        _db()
        .table("clients")
        .select("id")
        .neq("subscription_tier", "FREE")
        .gt("monthly_threat_limit", 0)
        .order("id")
        .execute()
        .data
        or []
    )
    return [row["id"] for row in rows if row.get("id")]


def _next_client_index(total: int) -> int:
    if total <= 0:
        return 0
    settings = get_settings()
    key = "sniperip:discovery:client_cursor"
    try:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        raw = client.get(key)
        current = int(raw) if raw is not None else 0
        index = current % total
        client.set(key, (index + 1) % total)
        return index
    except Exception:
        # Fallback keeps discovery alive when Redis cursor state is unavailable.
        return int(time.time()) % total


@celery_app.task(name="app.workers.discovery.run_discovery_tick")
def run_discovery_tick():
    """
    Queue discovery for exactly one paid client per tick.
    This smooths load and avoids batch spikes.
    """
    client_ids = _paid_client_ids()
    if not client_ids:
        return {"status": "no_paid_clients"}

    selected = client_ids[_next_client_index(len(client_ids))]
    run_discovery_for_client.apply_async(args=[selected], queue="discovery")
    return {"status": "queued_one_client", "client_id": selected, "total_paid_clients": len(client_ids)}


@celery_app.task(name="app.workers.discovery.run_discovery_all")
def run_discovery_all():
    """
    Queue all paid clients with spacing.
    Keep for manual catch-up runs; beat uses run_discovery_tick.
    """
    settings = get_settings()
    client_ids = _paid_client_ids()
    spacing = max(0, int(settings.discovery_client_spacing_seconds or 30))
    for idx, client_id in enumerate(client_ids):
        run_discovery_for_client.apply_async(
            args=[client_id],
            countdown=idx * spacing,
            queue="discovery",
        )
    return {"clients_queued": len(client_ids), "spacing_seconds": spacing}


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
    # Build merged whitelist: authorized_sellers table (new) + whitelist_domains column (legacy)
    try:
        sellers_resp = _db().table("authorized_sellers").select("domain").eq("client_id", client_id).execute()
        authorized_domains = [row["domain"].lower().strip() for row in (sellers_resp.data or []) if row.get("domain")]
    except Exception:
        authorized_domains = []
    legacy_whitelist = [d.lower().strip() for d in (client.get("whitelist_domains") or []) if d]
    # Expand each entry to cover both bare domain and www. variant for robust matching
    expanded: list[str] = []
    for d in set(authorized_domains + legacy_whitelist):
        expanded.append(d)
        if d.startswith("www."):
            expanded.append(d[4:])
        else:
            expanded.append(f"www.{d}")
    whitelist = list(set(expanded))
    created = 0

    for asset in assets:
        if current + created >= limit:
            break
        asset_id = asset["id"]
        ensure_asset_vectorized(asset_id)
        source_url = asset_image_source_url(asset)
        if not source_url:
            continue

        try:
            asset_bytes = download_bytes(source_url)
        except Exception:
            continue

        candidates = discover_candidates_for_asset(
            image_url=source_url,
            brand_name=client.get("company_name"),
            product_title=asset.get("original_filename"),
            whitelist_domains=whitelist,
            enable_shopping=settings.discovery_enable_shopping_search,
            enable_bing=settings.discovery_enable_bing_reverse,
        )
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

            try:
                candidate_bytes = download_bytes(candidate.image_url)
            except Exception:
                continue

            from app.services.vector_store import get_asset_phash

            breakdown = combined_similarity(
                asset_bytes,
                candidate_bytes,
                asset_phash=get_asset_phash(asset_id),
            )
            stored_similarity = breakdown.combined

            threshold = settings.similarity_threshold - 0.07 if blacklist_hit else settings.similarity_threshold
            threshold = max(0.80, threshold)
            if stored_similarity < threshold:
                continue

            if blacklist_hit and stored_similarity < settings.similarity_threshold:
                stored_similarity = settings.similarity_threshold + 0.01

            threat_id, created_now = _create_threat(
                asset_id=asset_id,
                infringing_url=candidate.listing_url,
                host_domain=_host(candidate.listing_url),
                similarity=stored_similarity,
                client_id=client_id,
            )
            _safe_record_bad_actor(actor_signals)

            if created_now:
                enrich_threat_with_explanation(
                    threat_id,
                    asset_name=asset.get("original_filename") or "Protected asset",
                    infringing_url=candidate.listing_url,
                    host_domain=_host(candidate.listing_url),
                    similarity_score=stored_similarity,
                    siglip_score=breakdown.siglip,
                    dinov2_score=breakdown.dinov2,
                    phash_distance=breakdown.phash_distance,
                    listing_price=candidate.listing_price,
                )
                created += 1

    if created:
        _db().table("clients").update({"current_month_count": current + created}).eq("id", client_id).execute()

    return {"client_id": client_id, "threats_created": created, "quota_remaining": max(limit - (current + created), 0)}
