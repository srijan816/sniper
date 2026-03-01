"""Asset management API routes (Supabase-backed)."""
from datetime import datetime
import os
import re
import uuid
from typing import List, Optional

import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Depends

from app.core.database import get_supabase_client
from app.models.schemas import AssetResponse
from app.workers.vectorize import vectorize_asset_task
from app.api.deps import get_current_client_id

logger = logging.getLogger(__name__)

router = APIRouter()


def _db():
    db = get_supabase_client()
    if db is None:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")
    return db


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "-", filename or "upload")
    return cleaned.strip("-") or "upload"


def _map_asset(row: dict) -> dict:
    return {
        "id": row.get("id"),
        "client_id": row.get("client_id"),
        "asset_type": row.get("asset_type") or "IMAGE",
        "original_filename": row.get("original_filename") or "unknown",
        "storage_url": row.get("storage_url") or "",
        "thumbnail_url": row.get("thumbnail_url"),
        "status": row.get("status") or "ACTIVE",
        "created_at": row.get("created_at") or datetime.utcnow().isoformat(),
    }


def _try_storage_upload(file: UploadFile, asset_id: str, client_id: str) -> str:
    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "assets")
    filename = _safe_filename(file.filename or "upload.bin")
    path = f"{client_id}/{asset_id}-{filename}"

    file_bytes = file.file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    storage = _db().storage.from_(bucket)
    storage.upload(path, file_bytes, {"content-type": file.content_type or "application/octet-stream", "upsert": "true"})
    public_url = storage.get_public_url(path)
    if isinstance(public_url, dict):
        return public_url.get("publicUrl") or public_url.get("public_url") or path
    return str(public_url)


@router.get("/", response_model=List[AssetResponse])
async def list_assets(client_id: str = Depends(get_current_client_id)):
    """List assets, optionally filtered by client."""
    try:
        query = _db().table("assets").select("*").order("created_at", desc=True)
        if client_id:
            query = query.eq("client_id", client_id)
        res = query.execute()
        return [_map_asset(row) for row in (res.data or [])]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list assets: {exc}") from exc


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(asset_id: str, client_id: str = Depends(get_current_client_id)):
    try:
        res = _db().table("assets").select("*").eq("id", asset_id).eq("client_id", client_id).limit(1).execute()
        rows = res.data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Asset not found")
        return _map_asset(rows[0])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch asset: {exc}") from exc


@router.post("/upload", response_model=AssetResponse)
async def upload_asset(
    asset_type: str = Form("IMAGE"),
    file: UploadFile = File(...),
    client_id: str = Depends(get_current_client_id),
):
    """Upload a new asset and persist record."""
    asset_id = str(uuid.uuid4())
    filename = _safe_filename(file.filename or "upload")

    try:
        storage_url = _try_storage_upload(file, asset_id, client_id)
    except HTTPException:
        raise
    except Exception:
        # Keep pipeline moving even if Storage bucket is not configured yet.
        storage_url = f"/storage/assets/{asset_id}-{filename}"

    row = {
        "id": asset_id,
        "client_id": client_id,
        "asset_type": asset_type,
        "original_filename": filename,
        "storage_url": storage_url,
        "thumbnail_url": None,
        "status": "ACTIVE",
    }

    try:
        res = _db().table("assets").insert(row).execute()
        rows = res.data or []
        if not rows:
            raise HTTPException(status_code=500, detail="Asset upload failed.")
        persisted = _map_asset(rows[0])

        # Kick off real embedding generation without blocking upload UX.
        try:
            vectorize_asset_task.delay(asset_id)
        except Exception as exc:
            # Keep upload successful even if worker queue is temporarily unavailable.
            logger.warning("Could not dispatch vectorize task for asset %s: %s", asset_id, exc)

        return persisted
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to persist asset: {exc}") from exc


@router.delete("/{asset_id}")
async def delete_asset(asset_id: str, client_id: str = Depends(get_current_client_id)):
    try:
        res = _db().table("assets").update({"status": "ARCHIVED"}).eq("id", asset_id).eq("client_id", client_id).execute()
        if not (res.data or []):
            raise HTTPException(status_code=404, detail="Asset not found")
        return {"status": "archived", "asset_id": asset_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to archive asset: {exc}") from exc
