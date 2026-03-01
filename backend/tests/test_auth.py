"""Test: every endpoint rejects unauthenticated requests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


PROTECTED_ROUTES = [
    ("GET",  "/api/assets/"),
    ("GET",  "/api/assets/some-id"),
    ("POST", "/api/assets/upload"),
    ("GET",  "/api/threats/"),
    ("GET",  "/api/threats/some-id"),
    ("POST", "/api/threats/some-id/approve"),
    ("POST", "/api/threats/some-id/whitelist"),
    ("POST", "/api/threats/some-id/reject"),
    ("GET",  "/api/threats/some-id/audit-trail"),
    ("GET",  "/api/threats/audit-logs"),
    ("POST", "/api/verify-threat"),
    ("POST", "/api/takedown/submit"),
    ("GET",  "/api/takedown/some-id"),
    ("GET",  "/api/takedown/"),
    ("POST", "/api/clients/"),
    ("GET",  "/api/clients/"),
    ("GET",  "/api/admin/metrics"),
    ("GET",  "/api/admin/costs"),
    ("GET",  "/api/admin/dlq"),
    ("POST", "/api/admin/dlq/some-id/retry"),
    ("POST", "/api/admin/dlq/some-id/dismiss"),
    ("POST", "/api/checkout/create"),
]


@pytest.fixture(scope="module")
def unauthenticated_client():
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("method,path", PROTECTED_ROUTES)
def test_unauthenticated_returns_401_or_403(unauthenticated_client, method, path):
    """Every protected route must reject requests with no Authorization header."""
    fn = getattr(unauthenticated_client, method.lower())
    response = fn(path)
    assert response.status_code in (401, 403, 422), (
        f"{method} {path} returned {response.status_code} without auth — expected 401/403"
    )
