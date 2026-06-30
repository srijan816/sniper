"""Tests for production observability endpoints."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_prometheus_metrics_endpoint():
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/metrics")
    assert resp.status_code == 200
    assert "sniperip_http_requests_total" in resp.text


def test_health_includes_research_queue():
    from app.main import app

    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "dependencies" in body
    assert "research_queue" in body["dependencies"]
