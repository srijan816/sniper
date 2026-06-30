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

    assert expected_embedding_dimension() == 1152


def test_siglip_features_to_vector_from_batch_tensor():
    from app.services.vision import _siglip_features_to_vector, _normalize_embedding

    class FakeTensor:
        ndim = 2

        def __getitem__(self, index):
            assert index == 0
            return self

        def tolist(self):
            return [1.0, 0.0, 0.0]

    vector = _normalize_embedding(_siglip_features_to_vector(FakeTensor()))
    assert len(vector) == 3
    assert all(isinstance(v, float) for v in vector)


def test_asset_image_source_url_video_requires_thumbnail():
    from app.services.vision import asset_image_source_url

    assert asset_image_source_url({"asset_type": "VIDEO", "storage_url": "https://x/v.mp4"}) is None
    assert (
        asset_image_source_url(
            {"asset_type": "VIDEO", "thumbnail_url": "https://x/thumb.jpg", "storage_url": "https://x/v.mp4"}
        )
        == "https://x/thumb.jpg"
    )
    assert asset_image_source_url({"asset_type": "IMAGE", "storage_url": "https://x/img.jpg"}) == "https://x/img.jpg"
