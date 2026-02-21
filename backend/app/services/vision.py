"""Vision utilities: SigLIP embedding, pHash, similarity, and frame extraction."""
from __future__ import annotations

from io import BytesIO
import math
import tempfile
from typing import Iterable, List

import ffmpeg
import httpx
import imagehash
from PIL import Image

from app.core.config import get_settings


def download_bytes(url: str, timeout: float = 30.0) -> bytes:
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content


def compute_phash(image_bytes: bytes) -> str:
    with Image.open(BytesIO(image_bytes)) as image:
        return str(imagehash.phash(image))


def extract_video_frame_bytes(video_url: str, timestamp_seconds: float = 3.0) -> bytes:
    """Extract frame bytes from a remote/local video URL using ffmpeg."""
    with tempfile.NamedTemporaryFile(suffix=".jpg") as output:
        (
            ffmpeg.input(video_url, ss=timestamp_seconds)
            .output(output.name, vframes=1, format="image2")
            .overwrite_output()
            .run(quiet=True)
        )
        with open(output.name, "rb") as handle:
            return handle.read()


def _normalize_embedding(values: Iterable[float]) -> List[float]:
    vector = [float(v) for v in values]
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        raise RuntimeError("Embedding norm is zero.")
    return [v / norm for v in vector]


def _pool_features(features):
    if not isinstance(features, list):
        raise RuntimeError("Invalid embedding format returned by Hugging Face API.")
    if not features:
        raise RuntimeError("Empty embedding vector returned by Hugging Face API.")
    if isinstance(features[0], (int, float)):
        return [float(v) for v in features]
    # Token-level features: average pool.
    first_row = features[0]
    if not isinstance(first_row, list):
        raise RuntimeError("Unexpected Hugging Face embedding shape.")
    size = len(first_row)
    sums = [0.0] * size
    count = 0
    for row in features:
        if not isinstance(row, list) or len(row) != size:
            continue
        count += 1
        for idx, val in enumerate(row):
            sums[idx] += float(val)
    if count == 0:
        raise RuntimeError("No valid rows in Hugging Face embedding output.")
    return [value / count for value in sums]


def embedding_from_image_bytes(image_bytes: bytes) -> List[float]:
    """Generate SigLIP embedding via Hugging Face inference API."""
    settings = get_settings()
    if not settings.huggingface_api_token:
        raise RuntimeError("HUGGINGFACE_API_TOKEN is required for vectorization.")

    endpoint = (
        f"https://api-inference.huggingface.co/pipeline/feature-extraction/"
        f"{settings.huggingface_embedding_model}"
    )
    headers = {
        "Authorization": f"Bearer {settings.huggingface_api_token}",
        "Content-Type": "application/octet-stream",
    }
    with httpx.Client(timeout=120.0) as client:
        response = client.post(endpoint, headers=headers, content=image_bytes)
        response.raise_for_status()
        payload = response.json()

    pooled = _pool_features(payload)
    return _normalize_embedding(pooled)


def embedding_from_image_url(image_url: str) -> List[float]:
    return embedding_from_image_bytes(download_bytes(image_url))


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        raise ValueError("Embedding dimensions do not match for cosine similarity.")
    return sum(x * y for x, y in zip(a, b))
