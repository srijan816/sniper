"""Vectorization worker (SigLIP + pHash + pgvector)."""
from __future__ import annotations

import uuid

from app.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import get_supabase_client
from app.services.vector_store import get_asset_embedding, upsert_asset_embedding
from app.services.vision import (
    compute_phash,
    cosine_similarity,
    download_bytes,
    embedding_from_image_bytes,
    embedding_from_image_url,
    extract_video_frame_bytes,
)


def _db():
    db = get_supabase_client()
    if db is None:
        raise RuntimeError("Supabase is not configured.")
    return db


def _upload_thumbnail(asset_id: str, client_id: str, frame_bytes: bytes) -> str:
    settings = get_settings()
    bucket = settings.supabase_storage_bucket
    path = f"{client_id}/{asset_id}-thumb.jpg"
    storage = _db().storage.from_(bucket)
    storage.upload(path, frame_bytes, {"content-type": "image/jpeg", "upsert": "true"})
    public_url = storage.get_public_url(path)
    if isinstance(public_url, dict):
        return public_url.get("publicUrl") or public_url.get("public_url") or path
    return str(public_url)


def _fetch_asset(asset_id: str) -> dict:
    rows = _db().table("assets").select("*").eq("id", asset_id).limit(1).execute().data or []
    if not rows:
        raise RuntimeError(f"Asset {asset_id} not found.")
    return rows[0]


@celery_app.task(name="app.workers.vectorize.vectorize_asset_task")
def vectorize_asset_task(asset_id: str):
    """Vectorize asset and persist into asset_embeddings."""
    asset = _fetch_asset(asset_id)
    asset_type = (asset.get("asset_type") or "IMAGE").upper()
    source_url = asset.get("storage_url")
    if not source_url:
        raise RuntimeError(f"Asset {asset_id} has no storage_url.")

    if asset_type == "VIDEO":
        frame_bytes = extract_video_frame_bytes(source_url, timestamp_seconds=3.0)
        thumbnail_url = _upload_thumbnail(asset_id, asset["client_id"], frame_bytes)
        _db().table("assets").update({"thumbnail_url": thumbnail_url}).eq("id", asset_id).execute()
        image_bytes = frame_bytes
    else:
        image_bytes = download_bytes(source_url)

    embedding = embedding_from_image_bytes(image_bytes)
    phash = compute_phash(image_bytes)
    upsert_asset_embedding(asset_id=asset_id, phash=phash, embedding=embedding)
    return {"asset_id": asset_id, "embedding_dim": len(embedding), "phash": phash, "status": "vectorized"}


def ensure_asset_vectorized(asset_id: str) -> list[float]:
    existing = get_asset_embedding(asset_id)
    if existing:
        return existing
    vectorize_asset_task(asset_id)
    created = get_asset_embedding(asset_id)
    if not created:
        raise RuntimeError(f"Failed to generate embedding for asset {asset_id}.")
    return created


def similarity_for_candidate(asset_id: str, candidate_image_url: str) -> float:
    """Compute real cosine similarity between an asset vector and candidate image."""
    asset_embedding = ensure_asset_vectorized(asset_id)
    candidate_embedding = embedding_from_image_url(candidate_image_url)
    return float(cosine_similarity(asset_embedding, candidate_embedding))


def similarity_for_candidate_bytes(asset_id: str, candidate_image_bytes: bytes) -> float:
    """Compute cosine similarity using already-downloaded candidate image bytes."""
    asset_embedding = ensure_asset_vectorized(asset_id)
    candidate_embedding = embedding_from_image_bytes(candidate_image_bytes)
    return float(cosine_similarity(asset_embedding, candidate_embedding))
