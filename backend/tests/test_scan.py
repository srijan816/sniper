"""Tests for free scan endpoint."""
from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image


def _jpeg_bytes() -> bytes:
    img = Image.new("RGB", (32, 32), (200, 100, 50))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture()
def scan_client():
    from app.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_free_scan_resolves_client_ip_without_name_error(scan_client):
    with patch("app.api.scan.get_supabase_client", return_value=None):
        with patch("app.api.scan.embedding_from_image_bytes", return_value=[0.1, 0.2]):
            with patch("app.api.scan.search_google_lens", return_value=[]):
                response = scan_client.post(
                    "/api/scan/free",
                    data={"email": "lead@example.com"},
                    files={"file": ("product.jpg", _jpeg_bytes(), "image/jpeg")},
                )
    assert response.status_code != 500
    assert "get_real_ip" not in (response.text or "")
