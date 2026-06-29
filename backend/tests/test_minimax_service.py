"""Tests for MiniMax threat explanation service."""
from __future__ import annotations

from unittest.mock import patch

from app.services.minimax_service import generate_threat_explanation


def test_generate_threat_explanation_returns_none_without_api_key():
    with patch("app.services.minimax_service.get_settings") as mock_settings:
        mock_settings.return_value.minimax_api_key = ""
        mock_settings.return_value.minimax_model = "MiniMax-M3"
        result = generate_threat_explanation(
            asset_name="Test Shoe",
            infringing_url="https://fake.example/listing",
            host_domain="fake.example",
            similarity_score=0.95,
        )
        assert result is None


def test_generate_threat_explanation_with_mock_response():
    with patch("app.services.minimax_service.get_settings") as mock_settings, patch(
        "app.services.minimax_service._chat"
    ) as mock_chat:
        mock_settings.return_value.minimax_api_key = "test-key"
        mock_settings.return_value.minimax_model = "MiniMax-M3"
        mock_chat.return_value = "High-confidence visual match on product silhouette and logo placement."
        result = generate_threat_explanation(
            asset_name="Test Shoe",
            infringing_url="https://fake.example/listing",
            host_domain="fake.example",
            similarity_score=0.95,
            siglip_score=0.97,
            dinov2_score=0.93,
        )
        assert result is not None
        assert "visual match" in result.lower()
