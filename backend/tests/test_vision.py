"""Tests for vision ensemble utilities."""
from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from app.services.vision import compute_phash, phash_hamming_distance, phash_similarity


def _solid_image(color: tuple[int, int, int]) -> bytes:
    img = Image.new("RGB", (64, 64), color)
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_phash_identical_images_have_zero_distance():
    a = compute_phash(_solid_image((255, 0, 0)))
    b = compute_phash(_solid_image((255, 0, 0)))
    assert phash_hamming_distance(a, b) == 0


def test_phash_similarity_range():
    a = compute_phash(_solid_image((255, 0, 0)))
    b = compute_phash(_solid_image((0, 0, 255)))
    sim, dist = phash_similarity(a, b)
    assert 0.0 <= sim <= 1.0
    assert 0 <= dist <= 64


def test_expected_embedding_dimension_default():
    from app.services.vision import expected_embedding_dimension

    assert expected_embedding_dimension() == 768
