"""Test: Pydantic schema validation — URL format and similarity_score range."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.schemas import ThreatCreate, VerifyThreatRequest


class TestVerifyThreatRequest:
    def test_valid_request(self):
        req = VerifyThreatRequest(
            asset_id="some-uuid",
            candidate_image_url="https://example.com/image.jpg",
            candidate_listing_url="https://shop.example.com/listing/123",
            host_domain="shop.example.com",
        )
        assert str(req.candidate_image_url).startswith("https://")

    def test_invalid_image_url_rejects(self):
        with pytest.raises(ValidationError):
            VerifyThreatRequest(
                asset_id="some-uuid",
                candidate_image_url="not-a-url",
                candidate_listing_url="https://shop.example.com/listing/123",
                host_domain="shop.example.com",
            )

    def test_private_ip_rejected(self):
        with pytest.raises(ValidationError):
            VerifyThreatRequest(
                asset_id="some-uuid",
                candidate_image_url="http://192.168.1.1/evil",
                candidate_listing_url="https://shop.example.com/listing/123",
                host_domain="shop.example.com",
            )

    def test_loopback_ip_rejected(self):
        with pytest.raises(ValidationError):
            VerifyThreatRequest(
                asset_id="some-uuid",
                candidate_image_url="http://127.0.0.1:8080/internal",
                candidate_listing_url="https://shop.example.com/listing/123",
                host_domain="shop.example.com",
            )

    def test_negative_listing_price_rejected(self):
        with pytest.raises(ValidationError):
            VerifyThreatRequest(
                asset_id="some-uuid",
                candidate_image_url="https://example.com/image.jpg",
                candidate_listing_url="https://shop.example.com/listing/123",
                host_domain="shop.example.com",
                listing_price=-1.0,
            )


class TestThreatCreate:
    def test_similarity_score_above_1_rejected(self):
        with pytest.raises(ValidationError):
            ThreatCreate(
                asset_id="uuid",
                client_id="uuid",
                infringing_url="https://fake.com/listing",
                host_domain="fake.com",
                similarity_score=1.5,
            )

    def test_similarity_score_below_0_rejected(self):
        with pytest.raises(ValidationError):
            ThreatCreate(
                asset_id="uuid",
                client_id="uuid",
                infringing_url="https://fake.com/listing",
                host_domain="fake.com",
                similarity_score=-0.1,
            )

    def test_valid_threat_create(self):
        t = ThreatCreate(
            asset_id="uuid",
            client_id="uuid",
            infringing_url="https://fake.com/listing",
            host_domain="fake.com",
            similarity_score=0.97,
        )
        assert t.similarity_score == 0.97
