"""Discovery worker: SerpApi radar + whitelist + verification pipeline."""
from __future__ import annotations

import time
from urllib.parse import urlparse

import redis

from app.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import get_supabase_client
from app.services.blacklist_store import BadActorSignals, is_known_bad_actor, record_bad_actor
from app.services.listing_intel import fetch_listing_intel
from app.services.scrapers import AliExpressEngine, GoogleLensEngine, filter_whitelisted
from app.services.threat_store import create_or_get_discovered_threat
from app.services.workflow import WorkflowConflictError, approve_threat as approve_threat_transaction
from app.services.vector_store import find_similar_assets
from app.services.vision import embedding_from_image_url
from app.workers.notifications import send_upgrade_email
from app.workers.vectorize import ensure_asset_vectorized
from app.workers.takedown import queue_takedown
import uuid


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
        source_url = asset.get("thumbnail_url") if (asset.get("asset_type") or "").upper() == "VIDEO" else asset.get("storage_url")
        if not source_url:
            continue

        keyword = asset.get("original_filename", "").replace("-", " ").replace("_", " ").split(".")[0]
        
        engines = [GoogleLensEngine(), AliExpressEngine()]
        raw_candidates = []
        
        for engine in engines:
            raw_candidates.extend(engine.search_by_image(source_url))
            if keyword and len(keyword) > 3:
                raw_candidates.extend(engine.search_by_keyword(keyword))

        candidates = filter_whitelisted(raw_candidates, whitelist)
        
        for candidate in candidates:
            if current + created >= limit:
                break
            if not candidate.listing_url:
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

            # If the engine natively found an image, hash it immediately.
            # Otherwise we must wait for verified takedowns to provide the asset context.
            if candidate.image_url:
                try:
                    candidate_embedding = embedding_from_image_url(candidate.image_url)
                    matches = find_similar_assets(candidate_embedding, client_id=client_id, limit=1)
                except Exception:
                    matches = []
            else:
                matches = []
                
            # If we don't have a direct visual match but we matched by precise Keyword logic,
            # we can optionally queue it for manual verification, but for V2 Phase 2, we 
            # only auto-generate threats for explicitly matched geometries to avoid false-positive storms.
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

            threat_id, created_now = _create_threat(
                asset_id=asset_id,
                infringing_url=candidate.listing_url,
                host_domain=_host(candidate.listing_url),
                similarity=stored_similarity,
                client_id=client_id,
            )
            _safe_record_bad_actor(actor_signals)
            if created_now:
                created += 1

                # Autonomous Eradication execution
                auto_rules = client.get("automation_rules") or {}
                auto_thresh = auto_rules.get("auto_takedown_threshold")
                
                if auto_thresh and stored_similarity >= float(auto_thresh):
                    try:
                        result = approve_threat_transaction(
                            threat_id=threat_id,
                            client_id=client_id,
                            platform=_host(candidate.listing_url),
                            changed_by="SYSTEM",
                        )
                        if result.takedown_id:
                            queue_takedown(result.takedown_id)
                    except WorkflowConflictError:
                        # Another worker or manual action may have moved the threat already.
                        pass
                    except Exception:
                        db = _db()
                        db.table("threats").update({"status": "APPROVED"}).eq("id", threat_id).execute()
                        db.table("audit_logs").insert({
                            "threat_id": threat_id,
                            "old_status": "DISCOVERED",
                            "new_status": "APPROVED",
                            "changed_by": "SYSTEM"
                        }).execute()

                        takedown_id = str(uuid.uuid4())
                        db.table("takedown_requests").insert({
                            "id": takedown_id,
                            "threat_id": threat_id,
                            "platform": _host(candidate.listing_url),
                            "status": "PENDING",
                            "retry_count": 0,
                            "submitted_at": None,
                        }).execute()

                        queue_takedown(takedown_id)

    if created:
        _db().table("clients").update({"current_month_count": current + created}).eq("id", client_id).execute()

    return {"client_id": client_id, "threats_created": created, "quota_remaining": max(limit - (current + created), 0)}
