"""Vision utilities: SigLIP 2 + DINOv2 ensemble, pHash, similarity."""
from __future__ import annotations

from io import BytesIO
import math
import tempfile
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional

import base64
import ffmpeg
import httpx
import imagehash
from PIL import Image

from app.core.config import get_settings

_LOCAL_SIGLIP_MODEL = None
_LOCAL_SIGLIP_PROCESSOR = None
_LOCAL_DINOV2_MODEL = None
_LOCAL_DINOV2_PROCESSOR = None


@dataclass
class SimilarityBreakdown:
    combined: float
    siglip: float
    dinov2: float
    phash: float
    phash_distance: int


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


def phash_similarity(phash_a: str, phash_b: str) -> tuple[float, int]:
    distance = phash_hamming_distance(phash_a, phash_b)
    return max(0.0, 1.0 - (distance / 64.0)), distance


def extract_video_frame_bytes(video_url: str, timestamp_seconds: float = 3.0) -> bytes:
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


def _hf_feature_extraction(model_id: str, image_bytes: bytes) -> List[float]:
    settings = get_settings()
    if settings.huggingface_inference_endpoint_url and model_id == settings.huggingface_embedding_model:
        token = settings.huggingface_inference_endpoint_token or settings.huggingface_api_token
        headers = {"Content-Type": "application/octet-stream"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        payload = _post_with_retry(settings.huggingface_inference_endpoint_url, headers, image_bytes)
        return _normalize_embedding(_pool_features(payload))

    if not settings.huggingface_api_token:
        raise RuntimeError("HUGGINGFACE_API_TOKEN is required for Hugging Face inference.")
    endpoint = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model_id}"
    headers = {
        "Authorization": f"Bearer {settings.huggingface_api_token}",
        "Content-Type": "application/octet-stream",
    }
    payload = _post_with_retry(endpoint, headers, image_bytes)
    return _normalize_embedding(_pool_features(payload))


def _get_local_siglip():
    global _LOCAL_SIGLIP_MODEL, _LOCAL_SIGLIP_PROCESSOR
    if _LOCAL_SIGLIP_MODEL is not None and _LOCAL_SIGLIP_PROCESSOR is not None:
        return _LOCAL_SIGLIP_MODEL, _LOCAL_SIGLIP_PROCESSOR
    from transformers import AutoModel, AutoProcessor

    model_name = get_settings().huggingface_embedding_model
    _LOCAL_SIGLIP_PROCESSOR = AutoProcessor.from_pretrained(model_name)
    _LOCAL_SIGLIP_MODEL = AutoModel.from_pretrained(model_name)
    _LOCAL_SIGLIP_MODEL.eval()
    return _LOCAL_SIGLIP_MODEL, _LOCAL_SIGLIP_PROCESSOR


def _get_local_dinov2():
    global _LOCAL_DINOV2_MODEL, _LOCAL_DINOV2_PROCESSOR
    if _LOCAL_DINOV2_MODEL is not None and _LOCAL_DINOV2_PROCESSOR is not None:
        return _LOCAL_DINOV2_MODEL, _LOCAL_DINOV2_PROCESSOR
    from transformers import AutoImageProcessor, AutoModel

    model_name = get_settings().dinov2_model
    _LOCAL_DINOV2_PROCESSOR = AutoImageProcessor.from_pretrained(model_name)
    _LOCAL_DINOV2_MODEL = AutoModel.from_pretrained(model_name)
    _LOCAL_DINOV2_MODEL.eval()
    return _LOCAL_DINOV2_MODEL, _LOCAL_DINOV2_PROCESSOR


def asset_image_source_url(asset: dict) -> str | None:
    """Return the URL to use for image-based verification (thumbnail for videos)."""
    if (asset.get("asset_type") or "").upper() == "VIDEO":
        return asset.get("thumbnail_url") or None
    return asset.get("storage_url")


def _siglip_features_to_vector(outputs) -> List[float]:
    """Extract a 1D embedding from SigLIP get_image_features output."""
    if hasattr(outputs, "pooler_output") and outputs.pooler_output is not None:
        return outputs.pooler_output[0].tolist()
    if hasattr(outputs, "last_hidden_state"):
        return outputs.last_hidden_state.mean(dim=1)[0].tolist()
    if hasattr(outputs, "ndim") and hasattr(outputs, "tolist"):
        if outputs.ndim >= 2:
            return outputs[0].tolist()
        return outputs.tolist()
    if isinstance(outputs, (list, tuple)) and outputs:
        first = outputs[0]
        if hasattr(first, "ndim") and hasattr(first, "tolist"):
            return first.tolist() if first.ndim == 1 else first[0].tolist()
        return list(first)
    raise RuntimeError("Unexpected SigLIP embedding output shape.")


def _embedding_siglip_local(image_bytes: bytes) -> List[float]:
    import torch

    model, processor = _get_local_siglip()
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = model.get_image_features(**inputs)
        vector = _siglip_features_to_vector(outputs)
    return _normalize_embedding(vector)


def _embedding_dinov2_local(image_bytes: bytes) -> List[float]:
    import torch

    model, processor = _get_local_dinov2()
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
        vector = outputs.last_hidden_state[:, 0, :][0].tolist()
    return _normalize_embedding(vector)


def _embedding_from_openai(image_bytes: bytes) -> List[float]:
    import openai

    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for OpenAI vision embeddings.")
    if int(settings.embedding_dimension or 1152) != 1536:
        raise RuntimeError(
            "OpenAI text-embedding-3-small produces 1536-dim vectors; "
            "set EMBEDDING_DIMENSION=1536 or disable HUGGINGFACE_ALLOW_OPENAI_FALLBACK."
        )

    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
    prompt = (
        "Describe this e-commerce product in extreme detail, focusing on brand, model, color, "
        "shape, materials, and defining features. The goal is to uniquely identify this exact "
        "product among counterfeits."
    )
    client = openai.OpenAI(api_key=settings.openai_api_key)
    vision_resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}},
                ],
            }
        ],
        max_tokens=300,
    )
    description = vision_resp.choices[0].message.content
    if not description:
        raise RuntimeError("OpenAI Vision failed to return a valid description.")
    embed_resp = client.embeddings.create(input=description, model="text-embedding-3-small")
    return _normalize_embedding(embed_resp.data[0].embedding)


def siglip_embedding_from_image_bytes(image_bytes: bytes) -> List[float]:
    settings = get_settings()
    backend = (settings.huggingface_embedding_backend or "auto").lower()
    model_id = settings.huggingface_embedding_model

    if backend == "openai":
        return _embedding_from_openai(image_bytes)

    errors: list[str] = []
    if backend in {"endpoint", "auto"} and settings.huggingface_inference_endpoint_url:
        try:
            return _hf_feature_extraction(model_id, image_bytes)
        except Exception as exc:
            errors.append(f"endpoint: {exc}")

    if backend in {"shared", "auto"} and settings.huggingface_api_token:
        try:
            return _hf_feature_extraction(model_id, image_bytes)
        except Exception as exc:
            errors.append(f"shared: {exc}")

    if backend in {"local", "auto"}:
        try:
            return _embedding_siglip_local(image_bytes)
        except Exception as exc:
            errors.append(f"local: {exc}")

    if settings.openai_api_key and settings.huggingface_allow_openai_fallback:
        return _embedding_from_openai(image_bytes)

    raise RuntimeError(f"SigLIP embedding failed ({'; '.join(errors) or 'no backend configured'})")


def dinov2_embedding_from_image_bytes(image_bytes: bytes) -> List[float]:
    settings = get_settings()
    if not settings.dinov2_enabled:
        raise RuntimeError("DINOv2 is disabled.")
    backend = (settings.dinov2_backend or "shared").lower()
    model_id = settings.dinov2_model

    if backend == "shared" and settings.huggingface_api_token:
        return _hf_feature_extraction(model_id, image_bytes)
    if backend == "local":
        return _embedding_dinov2_local(image_bytes)
    raise RuntimeError("DINOv2 backend not configured.")


def embedding_from_image_bytes(image_bytes: bytes) -> List[float]:
    """Primary stored embedding (SigLIP 2 family)."""
    return siglip_embedding_from_image_bytes(image_bytes)


def embedding_from_image_url(image_url: str) -> List[float]:
    return embedding_from_image_bytes(download_bytes(image_url))


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        raise ValueError("Embedding dimensions do not match for cosine similarity.")
    return sum(x * y for x, y in zip(a, b))


def expected_embedding_dimension() -> int:
    return int(get_settings().embedding_dimension or 768)


def combined_similarity(
    asset_bytes: bytes,
    candidate_bytes: bytes,
    *,
    asset_phash: str | None = None,
    asset_siglip: List[float] | None = None,
) -> SimilarityBreakdown:
    """
    Ensemble score: SigLIP 2 (semantic) + DINOv2 (structural) + pHash (perceptual).
    Weights tuned for counterfeit listing detection.
    """
    settings = get_settings()

    candidate_phash = compute_phash(candidate_bytes)
    if asset_phash:
        phash_sim, phash_dist = phash_similarity(asset_phash, candidate_phash)
    else:
        asset_phash_val = compute_phash(asset_bytes)
        phash_sim, phash_dist = phash_similarity(asset_phash_val, candidate_phash)

    siglip_a = asset_siglip or siglip_embedding_from_image_bytes(asset_bytes)
    siglip_b = siglip_embedding_from_image_bytes(candidate_bytes)
    siglip_sim = cosine_similarity(siglip_a, siglip_b)

    dinov2_sim = siglip_sim
    if settings.dinov2_enabled:
        try:
            dinov2_a = dinov2_embedding_from_image_bytes(asset_bytes)
            dinov2_b = dinov2_embedding_from_image_bytes(candidate_bytes)
            dinov2_sim = cosine_similarity(dinov2_a, dinov2_b)
        except Exception:
            dinov2_sim = siglip_sim

    combined = (
        float(settings.similarity_weight_siglip) * siglip_sim
        + float(settings.similarity_weight_dinov2) * dinov2_sim
        + float(settings.similarity_weight_phash) * phash_sim
    )
    return SimilarityBreakdown(
        combined=combined,
        siglip=siglip_sim,
        dinov2=dinov2_sim,
        phash=phash_sim,
        phash_distance=phash_dist,
    )


def score_candidate_match(
    candidate_bytes: bytes,
    *,
    asset_phash: str | None = None,
    asset_siglip: List[float] | None = None,
    asset_bytes: bytes | None = None,
    asset_source_url: str | None = None,
    fast_reject_margin: float | None = None,
) -> SimilarityBreakdown:
    """
    Cascade verification for discovery/verify:
    1. pHash fast-path when hashes are very close
    2. SigLIP using stored asset embedding (one inference, not two)
    3. Full DINOv2 ensemble only when score is near threshold
    """
    settings = get_settings()
    margin = float(fast_reject_margin if fast_reject_margin is not None else settings.discovery_fast_reject_margin)
    threshold = float(settings.similarity_threshold)

    candidate_phash = compute_phash(candidate_bytes)
    if asset_phash:
        phash_sim, phash_dist = phash_similarity(asset_phash, candidate_phash)
        if phash_dist <= int(settings.phash_distance_threshold):
            fast_combined = max(threshold, 1.0 - (phash_dist / 64.0))
            return SimilarityBreakdown(
                combined=fast_combined,
                siglip=fast_combined,
                dinov2=fast_combined,
                phash=phash_sim,
                phash_distance=phash_dist,
            )
    else:
        if asset_bytes is None:
            raise ValueError("asset_phash or asset_bytes required for candidate scoring")
        asset_phash_val = compute_phash(asset_bytes)
        phash_sim, phash_dist = phash_similarity(asset_phash_val, candidate_phash)
        asset_phash = asset_phash_val

    siglip_a = asset_siglip
    if siglip_a is None:
        if asset_bytes is None:
            if asset_source_url:
                asset_bytes = download_bytes(asset_source_url)
            else:
                raise ValueError("asset_siglip, asset_bytes, or asset_source_url required")
        siglip_a = siglip_embedding_from_image_bytes(asset_bytes)

    siglip_b = siglip_embedding_from_image_bytes(candidate_bytes)
    siglip_sim = cosine_similarity(siglip_a, siglip_b)

    quick_combined = (
        float(settings.similarity_weight_siglip) * siglip_sim
        + float(settings.similarity_weight_dinov2) * siglip_sim
        + float(settings.similarity_weight_phash) * phash_sim
    )
    if quick_combined < threshold - margin:
        return SimilarityBreakdown(
            combined=quick_combined,
            siglip=siglip_sim,
            dinov2=siglip_sim,
            phash=phash_sim,
            phash_distance=phash_dist,
        )

    if asset_bytes is None and asset_source_url and settings.dinov2_enabled:
        asset_bytes = download_bytes(asset_source_url)

    dinov2_sim = siglip_sim
    if settings.dinov2_enabled and asset_bytes:
        try:
            dinov2_a = dinov2_embedding_from_image_bytes(asset_bytes)
            dinov2_b = dinov2_embedding_from_image_bytes(candidate_bytes)
            dinov2_sim = cosine_similarity(dinov2_a, dinov2_b)
        except Exception:
            dinov2_sim = siglip_sim

    combined = (
        float(settings.similarity_weight_siglip) * siglip_sim
        + float(settings.similarity_weight_dinov2) * dinov2_sim
        + float(settings.similarity_weight_phash) * phash_sim
    )
    return SimilarityBreakdown(
        combined=combined,
        siglip=siglip_sim,
        dinov2=dinov2_sim,
        phash=phash_sim,
        phash_distance=phash_dist,
    )
