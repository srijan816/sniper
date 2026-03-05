"""Vision utilities: SigLIP embedding, pHash, similarity, and frame extraction."""
from __future__ import annotations

from io import BytesIO
import math
import tempfile
import time
from typing import Iterable, List

import ffmpeg
import httpx
import imagehash
from PIL import Image
from app.core.config import get_settings

_LOCAL_MODEL = None
_LOCAL_PROCESSOR = None


def download_bytes(url: str, timeout: float = 30.0) -> bytes:
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content


def compute_phash(image_bytes: bytes) -> str:
    with Image.open(BytesIO(image_bytes)) as image:
        return str(imagehash.phash(image))


def phash_hamming_distance(phash_a: str, phash_b: str) -> int:
    try:
        return int(bin(int(phash_a, 16) ^ int(phash_b, 16)).count("1"))
    except Exception as exc:
        raise RuntimeError(f"Invalid pHash values for distance calculation: {exc}") from exc


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


def _post_with_retry(url: str, headers: dict, payload: bytes) -> list:
    settings = get_settings()
    retries = max(1, int(settings.embedding_request_retries or 3))
    backoff = 1.2
    last_error: Exception | None = None
    with httpx.Client(timeout=120.0) as client:
        for attempt in range(retries):
            try:
                response = client.post(url, headers=headers, content=payload)
                if response.status_code in (408, 425, 429, 500, 502, 503, 504):
                    raise RuntimeError(f"Transient embedding API failure: {response.status_code} {response.text[:300]}")
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last_error = exc
                if attempt < retries - 1:
                    time.sleep(backoff)
                    backoff *= 1.7
                    continue
                break
    raise RuntimeError(f"Embedding API request failed after {retries} attempts: {last_error}")


def _embedding_from_shared_inference(image_bytes: bytes) -> List[float]:
    settings = get_settings()
    if not settings.huggingface_api_token:
        raise RuntimeError("HUGGINGFACE_API_TOKEN is required for shared Hugging Face inference.")
    endpoint = (
        f"https://api-inference.huggingface.co/pipeline/feature-extraction/"
        f"{settings.huggingface_embedding_model}"
    )
    headers = {
        "Authorization": f"Bearer {settings.huggingface_api_token}",
        "Content-Type": "application/octet-stream",
    }
    payload = _post_with_retry(endpoint, headers, image_bytes)
    pooled = _pool_features(payload)
    return _normalize_embedding(pooled)


def _embedding_from_dedicated_endpoint(image_bytes: bytes) -> List[float]:
    settings = get_settings()
    if not settings.huggingface_inference_endpoint_url:
        raise RuntimeError("HUGGINGFACE_INFERENCE_ENDPOINT_URL is required for endpoint embedding backend.")

    token = settings.huggingface_inference_endpoint_token or settings.huggingface_api_token
    headers = {"Content-Type": "application/octet-stream"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = _post_with_retry(settings.huggingface_inference_endpoint_url, headers, image_bytes)
    pooled = _pool_features(payload)
    return _normalize_embedding(pooled)


def _get_local_siglip():
    global _LOCAL_MODEL, _LOCAL_PROCESSOR
    if _LOCAL_MODEL is not None and _LOCAL_PROCESSOR is not None:
        return _LOCAL_MODEL, _LOCAL_PROCESSOR

    try:
        from transformers import AutoModel, AutoProcessor
    except Exception as exc:
        raise RuntimeError("Local embedding backend requires `transformers`.") from exc

    model_name = get_settings().huggingface_embedding_model
    _LOCAL_PROCESSOR = AutoProcessor.from_pretrained(model_name)
    _LOCAL_MODEL = AutoModel.from_pretrained(model_name)
    _LOCAL_MODEL.eval()
    return _LOCAL_MODEL, _LOCAL_PROCESSOR


def embedding_from_image_bytes(image_bytes: bytes) -> List[float]:
    """
    Generate dense visual embeddings using Meta's DINOv2 or OpenAI CLIP via Hugging Face.
    These models extract geometric and texture data directly from pixels, avoiding lossy NLP boundaries.
    """
    settings = get_settings()
    backend = settings.huggingface_embedding_backend

    try:
        if backend == "endpoint" and settings.huggingface_inference_endpoint_url:
            return _embedding_from_dedicated_endpoint(image_bytes)
        
        if backend == "shared" or (backend == "auto" and settings.huggingface_allow_shared_fallback):
            return _embedding_from_shared_inference(image_bytes)

        if backend == "local":
            model, processor = _get_local_siglip()
            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            inputs = processor(images=image, return_tensors="pt")
            outputs = model(**inputs)
            pooled = outputs.pooler_output[0].detach().numpy().tolist()
            return _normalize_embedding(pooled)

        # Fallback to shared HuggingFace API if 'auto' and no endpoint provided
        return _embedding_from_shared_inference(image_bytes)

    except Exception as exc:
        raise RuntimeError(f"Visual Embedding generation failed using backend '{backend}'. Error: {exc}")


def embedding_from_image_url(image_url: str) -> List[float]:
    return embedding_from_image_bytes(download_bytes(image_url))


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        raise ValueError("Embedding dimensions do not match for cosine similarity.")
    return sum(x * y for x, y in zip(a, b))
