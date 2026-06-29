"""MiniMax M3 client for threat intelligence and explanations."""
from __future__ import annotations

import logging
import re
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_THINKING_RE = re.compile(r"<think>[\s\S]*?</think>\s*", re.IGNORECASE)


def _strip_thinking(text: str) -> str:
    cleaned = _THINKING_RE.sub("", text).strip()
    if cleaned:
        return cleaned
    # Unclosed thinking block — drop everything before the last blank-line paragraph
    if "<think>" in text.lower():
        parts = [p.strip() for p in text.split("\n\n") if p.strip()]
        return parts[-1] if parts else text.strip()
    return text.strip()


def _chat(
    messages: list[dict],
    *,
    max_tokens: int = 800,
    temperature: float = 0.2,
) -> Optional[str]:
    settings = get_settings()
    api_key = settings.minimax_api_key
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai package not installed for MiniMax client")
        return None

    model = settings.minimax_model or "MiniMax-M3"
    client = OpenAI(base_url="https://api.minimax.io/v1", api_key=api_key)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            extra_body={"reasoning_split": True, "thinking": {"type": "disabled"}},
        )
        content = response.choices[0].message.content
        if not content:
            return None
        return _strip_thinking(str(content))
    except Exception as exc:
        logger.warning("MiniMax chat failed: %s", exc)
        return None


def generate_threat_explanation(
    *,
    asset_name: str,
    infringing_url: str,
    host_domain: str,
    similarity_score: float,
    siglip_score: float | None = None,
    dinov2_score: float | None = None,
    phash_distance: int | None = None,
    listing_price: float | None = None,
) -> Optional[str]:
    """Produce a concise legal-review explanation for a discovered threat."""
    score_lines = [f"- Combined similarity: {similarity_score:.3f}"]
    if siglip_score is not None:
        score_lines.append(f"- SigLIP 2 visual match: {siglip_score:.3f}")
    if dinov2_score is not None:
        score_lines.append(f"- DINOv2 structural match: {dinov2_score:.3f}")
    if phash_distance is not None:
        score_lines.append(f"- pHash Hamming distance: {phash_distance}")
    if listing_price is not None:
        score_lines.append(f"- Listed price: ${listing_price:.2f}")

    prompt = (
        "You are an IP enforcement analyst for a D2C brand protection platform.\n"
        "Write a 3-5 sentence threat assessment for a legal reviewer.\n"
        "Be specific about why this listing likely infringes (visual similarity, unauthorized seller, price anomaly).\n"
        "Do not claim certainty beyond the scores. No markdown headers. Output only the assessment.\n\n"
        f"Protected asset: {asset_name}\n"
        f"Infringing URL: {infringing_url}\n"
        f"Host domain: {host_domain}\n"
        + "\n".join(score_lines)
    )

    return _chat(
        [
            {"role": "system", "content": "You write concise, factual IP threat assessments."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=400,
    )
