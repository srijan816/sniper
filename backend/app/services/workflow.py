"""Transactional helpers for threat state transitions."""

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional, Set
import uuid

from psycopg import sql

from app.core.database import get_pg_transaction


class WorkflowNotFoundError(Exception):
    """Raised when a tenant-scoped workflow resource does not exist."""


class WorkflowConflictError(Exception):
    """Raised when a requested state transition is invalid."""


@dataclass(frozen=True)
class ThreatTransitionResult:
    threat: dict
    takedown_id: Optional[str] = None


def _utcnow():
    return datetime.now(timezone.utc)


@lru_cache(maxsize=1)
def _takedown_table_name() -> str:
    with get_pg_transaction() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.takedown_requests') AS takedown_requests")
            row = cur.fetchone() or {}
            if row.get("takedown_requests"):
                return "takedown_requests"
            cur.execute("SELECT to_regclass('public.takedowns') AS takedowns")
            row = cur.fetchone() or {}
            if row.get("takedowns"):
                return "takedowns"
    raise RuntimeError("No takedown table found.")


def _load_owned_threat_for_update(cur, threat_id: str, client_id: str) -> dict:
    cur.execute(
        """
        SELECT *
        FROM threats
        WHERE id = %s AND client_id = %s
        FOR UPDATE
        """,
        (threat_id, client_id),
    )
    threat = cur.fetchone()
    if not threat:
        raise WorkflowNotFoundError("Threat not found")
    return threat


def _insert_audit(cur, *, threat_id: str, old_status: Optional[str], new_status: str, changed_by: str) -> None:
    cur.execute(
        """
        INSERT INTO audit_logs (id, threat_id, old_status, new_status, changed_by, changed_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (str(uuid.uuid4()), threat_id, old_status, new_status, changed_by, _utcnow()),
    )


def transition_threat_status(
    *,
    threat_id: str,
    client_id: str,
    new_status: str,
    changed_by: str,
    allowed_from: Optional[Set[str]] = None,
) -> ThreatTransitionResult:
    """Atomically update a threat status and write its audit log."""
    with get_pg_transaction() as conn:
        with conn.cursor() as cur:
            threat = _load_owned_threat_for_update(cur, threat_id, client_id)
            old_status = threat.get("status") or "DISCOVERED"
            if allowed_from and old_status not in allowed_from:
                raise WorkflowConflictError(f"Cannot transition threat from {old_status} to {new_status}")
            if old_status == new_status:
                return ThreatTransitionResult(threat=threat)

            resolved_at = threat.get("resolved_at")
            if new_status in {"WHITELISTED", "REJECTED", "REMOVED", "TAKEDOWN_CONFIRMED"}:
                resolved_at = _utcnow()
            elif new_status in {"DISCOVERED", "PENDING_APPROVAL", "APPROVED", "TAKEDOWN_SUBMITTED"}:
                resolved_at = None

            cur.execute(
                """
                UPDATE threats
                SET status = %s, resolved_at = %s
                WHERE id = %s
                RETURNING *
                """,
                (new_status, resolved_at, threat_id),
            )
            updated = cur.fetchone()
            _insert_audit(
                cur,
                threat_id=threat_id,
                old_status=old_status,
                new_status=new_status,
                changed_by=changed_by,
            )
            return ThreatTransitionResult(threat=updated)


def approve_threat(
    *,
    threat_id: str,
    client_id: str,
    platform: str,
    changed_by: str,
) -> ThreatTransitionResult:
    """Atomically approve a threat, audit it, and create/reuse a takedown request."""
    takedown_table = _takedown_table_name()

    with get_pg_transaction() as conn:
        with conn.cursor() as cur:
            threat = _load_owned_threat_for_update(cur, threat_id, client_id)
            old_status = threat.get("status") or "DISCOVERED"
            if old_status not in {"DISCOVERED", "PENDING_APPROVAL"}:
                raise WorkflowConflictError(f"Cannot approve threat in status {old_status}")

            cur.execute(
                """
                UPDATE threats
                SET status = 'APPROVED', resolved_at = NULL
                WHERE id = %s
                RETURNING *
                """,
                (threat_id,),
            )
            updated = cur.fetchone()
            _insert_audit(
                cur,
                threat_id=threat_id,
                old_status=old_status,
                new_status="APPROVED",
                changed_by=changed_by,
            )

            cur.execute(
                sql.SQL(
                    """
                    SELECT id
                    FROM {table}
                    WHERE threat_id = %s AND status IN ('PENDING', 'SUBMITTED', 'CONFIRMED')
                    ORDER BY created_at DESC NULLS LAST, submitted_at DESC NULLS LAST
                    LIMIT 1
                    FOR UPDATE
                    """
                ).format(table=sql.Identifier(takedown_table)),
                (threat_id,),
            )
            existing = cur.fetchone()
            if existing:
                return ThreatTransitionResult(threat=updated, takedown_id=str(existing["id"]))

            takedown_id = str(uuid.uuid4())
            cur.execute(
                sql.SQL(
                    """
                    INSERT INTO {table} (
                        id,
                        threat_id,
                        platform,
                        status,
                        retry_count,
                        submitted_at
                    )
                    VALUES (%s, %s, %s, 'PENDING', 0, NULL)
                    """
                ).format(table=sql.Identifier(takedown_table)),
                (takedown_id, threat_id, platform),
            )
            return ThreatTransitionResult(threat=updated, takedown_id=takedown_id)
