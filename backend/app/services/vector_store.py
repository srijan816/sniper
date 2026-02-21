"""Helpers for pgvector writes/searches."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional
import uuid

from app.core.database import get_pg_connection


def _vector_literal(values: Iterable[float]) -> str:
    return "[" + ",".join(f"{float(v):.8f}" for v in values) + "]"


@dataclass
class SimilarAssetMatch:
    asset_id: str
    client_id: str
    similarity: float


def upsert_asset_embedding(asset_id: str, phash: str, embedding: List[float]) -> None:
    """Store embedding for asset (replace previous if it exists)."""
    vector = _vector_literal(embedding)
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM asset_embeddings WHERE asset_id = %s", (asset_id,))
            cur.execute(
                """
                INSERT INTO asset_embeddings (id, asset_id, phash, embedding)
                VALUES (%s, %s, %s, %s::vector)
                """,
                (str(uuid.uuid4()), asset_id, phash, vector),
            )


def get_asset_embedding(asset_id: str) -> Optional[List[float]]:
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT embedding::text FROM asset_embeddings WHERE asset_id = %s LIMIT 1",
                (asset_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            raw = row[0].strip("[]")
            if not raw:
                return None
            return [float(v) for v in raw.split(",")]


def find_similar_assets(
    embedding: List[float],
    *,
    client_id: Optional[str] = None,
    limit: int = 5,
) -> List[SimilarAssetMatch]:
    """Find nearest asset vectors by cosine similarity."""
    vector = _vector_literal(embedding)
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            if client_id:
                cur.execute(
                    """
                    SELECT ae.asset_id,
                           a.client_id,
                           (1 - (ae.embedding <=> %s::vector)) AS similarity
                    FROM asset_embeddings ae
                    JOIN assets a ON a.id = ae.asset_id
                    WHERE a.client_id = %s
                    ORDER BY ae.embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (vector, client_id, vector, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT ae.asset_id,
                           a.client_id,
                           (1 - (ae.embedding <=> %s::vector)) AS similarity
                    FROM asset_embeddings ae
                    JOIN assets a ON a.id = ae.asset_id
                    ORDER BY ae.embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (vector, vector, limit),
                )
            rows = cur.fetchall() or []

    return [
        SimilarAssetMatch(asset_id=row[0], client_id=row[1], similarity=float(row[2]))
        for row in rows
    ]
