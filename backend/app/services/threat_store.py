"""Threat persistence helpers (atomic RPC + safe fallback)."""
from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any, Tuple

from app.core.database import get_supabase_client


def _db():
    db = get_supabase_client()
    if db is None:
        raise RuntimeError("Supabase is not configured.")
    return db


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _duplicate_key_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "23505" in message or "duplicate key value violates unique constraint" in message


def _asset_client_id(asset_id: str) -> str | None:
    rows = _db().table("assets").select("client_id").eq("id", asset_id).limit(1).execute().data or []
    if not rows:
        return None
    return rows[0].get("client_id")


def _existing_threat_id(asset_id: str, infringing_url: str) -> str | None:
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
    return rows[0].get("id") if rows else None


def _parse_rpc_data(data: Any) -> Tuple[str | None, bool]:
    if data is None:
        return None, False

    if isinstance(data, list):
        if not data:
            return None, False
        row = data[0]
        if isinstance(row, dict):
            threat_id = row.get("threat_id") or row.get("id")
            created = bool(row.get("created", False))
            return (str(threat_id), created) if threat_id else (None, False)
        if isinstance(row, str):
            return row, False

    if isinstance(data, dict):
        threat_id = data.get("threat_id") or data.get("id")
        created = bool(data.get("created", False))
        return (str(threat_id), created) if threat_id else (None, False)

    if isinstance(data, str):
        return data, False

    return None, False


def create_or_get_discovered_threat(
    *,
    asset_id: str,
    infringing_url: str,
    host_domain: str,
    similarity_score: float,
    client_id: str | None = None,
) -> Tuple[str, bool]:
    """
    Insert DISCOVERED threat + audit log atomically via RPC.

    Returns:
      (threat_id, created)
    """
    resolved_client_id = client_id or _asset_client_id(asset_id)
    payload = {
        "p_asset_id": asset_id,
        "p_client_id": resolved_client_id,
        "p_infringing_url": infringing_url,
        "p_host_domain": host_domain,
        "p_similarity_score": float(similarity_score),
        "p_discovered_at": _utcnow_iso(),
    }

    try:
        rpc_result = _db().rpc("create_threat_with_audit", payload).execute()
        threat_id, created = _parse_rpc_data(rpc_result.data)
        if threat_id:
            return threat_id, created
    except Exception:
        # Fall through to the compatibility path when RPC is not yet deployed.
        pass

    existing_id = _existing_threat_id(asset_id, infringing_url)
    if existing_id:
        return existing_id, False

    threat_id = str(uuid.uuid4())
    row = {
        "id": threat_id,
        "asset_id": asset_id,
        "client_id": resolved_client_id,
        "infringing_url": infringing_url,
        "host_domain": host_domain,
        "similarity_score": float(similarity_score),
        "status": "DISCOVERED",
        "discovered_at": _utcnow_iso(),
    }

    try:
        _db().table("threats").insert(row).execute()
        _db().table("audit_logs").insert(
            {
                "threat_id": threat_id,
                "old_status": None,
                "new_status": "DISCOVERED",
                "changed_by": "SYSTEM",
            }
        ).execute()
        return threat_id, True
    except Exception as exc:
        if _duplicate_key_error(exc):
            existing_id = _existing_threat_id(asset_id, infringing_url)
            if existing_id:
                return existing_id, False
        raise
