"""Tests for production observability endpoints."""
from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient


def test_prometheus_metrics_endpoint():
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/metrics")
    assert resp.status_code == 200
    assert "sniperip_http_requests_total" in resp.text


def test_prometheus_metrics_requires_auth_in_production():
    from app.main import app

    client = TestClient(app)
    with patch("app.api.prometheus.get_settings") as mock_settings:
        mock_settings.return_value.prometheus_enabled = True
        mock_settings.return_value.environment = "production"
        mock_settings.return_value.metrics_auth_token = ""
        resp = client.get("/api/metrics")
    assert resp.status_code == 401


def test_health_includes_research_queue():
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "dependencies" in body
    assert "research_queue" in body["dependencies"]
