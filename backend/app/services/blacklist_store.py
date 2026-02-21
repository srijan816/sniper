"""Persistent bad-actor store for cross-client discovery intelligence."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from app.core.database import get_pg_connection


@dataclass
class BadActorSignals:
    host_domain: str | None = None
    seller_name: str | None = None
    support_email: str | None = None
    payment_gateway_id: str | None = None


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().lower()
    return cleaned or None


def _normalized_signals(signals: BadActorSignals) -> BadActorSignals:
    return BadActorSignals(
        host_domain=_normalize(signals.host_domain),
        seller_name=signals.seller_name.strip() if signals.seller_name else None,
        support_email=_normalize(signals.support_email),
        payment_gateway_id=_normalize(signals.payment_gateway_id),
    )


def ensure_blacklist_table() -> None:
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS blacklist_actors (
                    id UUID PRIMARY KEY,
                    host_domain TEXT,
                    seller_name TEXT,
                    support_email TEXT,
                    payment_gateway_id TEXT,
                    threat_count INT NOT NULL DEFAULT 1,
                    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_blacklist_host_domain ON blacklist_actors (host_domain)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_blacklist_seller_name ON blacklist_actors (seller_name)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_blacklist_support_email ON blacklist_actors (support_email)")
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_blacklist_payment_gateway_id ON blacklist_actors (payment_gateway_id)"
            )


def _query_match(signals: BadActorSignals):
    clauses = []
    params: list[str] = []
    if signals.host_domain:
        clauses.append("host_domain = %s")
        params.append(signals.host_domain)
    if signals.seller_name:
        clauses.append("seller_name = %s")
        params.append(signals.seller_name)
    if signals.support_email:
        clauses.append("support_email = %s")
        params.append(signals.support_email)
    if signals.payment_gateway_id:
        clauses.append("payment_gateway_id = %s")
        params.append(signals.payment_gateway_id)
    return clauses, params


def is_known_bad_actor(signals: BadActorSignals) -> bool:
    normalized = _normalized_signals(signals)
    clauses, params = _query_match(normalized)
    if not clauses:
        return False

    ensure_blacklist_table()
    where_clause = " OR ".join(clauses)

    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT id FROM blacklist_actors WHERE {where_clause} LIMIT 1", params)
            return cur.fetchone() is not None


def record_bad_actor(signals: BadActorSignals) -> None:
    normalized = _normalized_signals(signals)
    clauses, params = _query_match(normalized)
    if not clauses:
        return

    ensure_blacklist_table()
    where_clause = " OR ".join(clauses)

    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT id, threat_count FROM blacklist_actors WHERE {where_clause} ORDER BY last_seen_at DESC LIMIT 1",
                params,
            )
            existing = cur.fetchone()
            now = datetime.now(timezone.utc)

            if existing:
                actor_id = existing[0]
                cur.execute(
                    """
                    UPDATE blacklist_actors
                    SET threat_count = threat_count + 1,
                        last_seen_at = %s,
                        host_domain = COALESCE(host_domain, %s),
                        seller_name = COALESCE(seller_name, %s),
                        support_email = COALESCE(support_email, %s),
                        payment_gateway_id = COALESCE(payment_gateway_id, %s)
                    WHERE id = %s
                    """,
                    (
                        now,
                        normalized.host_domain,
                        normalized.seller_name,
                        normalized.support_email,
                        normalized.payment_gateway_id,
                        actor_id,
                    ),
                )
                return

            cur.execute(
                """
                INSERT INTO blacklist_actors (
                    id,
                    host_domain,
                    seller_name,
                    support_email,
                    payment_gateway_id,
                    threat_count,
                    first_seen_at,
                    last_seen_at
                )
                VALUES (%s, %s, %s, %s, %s, 1, %s, %s)
                """,
                (
                    str(uuid.uuid4()),
                    normalized.host_domain,
                    normalized.seller_name,
                    normalized.support_email,
                    normalized.payment_gateway_id,
                    now,
                    now,
                ),
            )
