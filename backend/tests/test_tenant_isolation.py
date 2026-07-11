"""Test: IDOR tenant isolation — Client A cannot access Client B's resources."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_client_id

CLIENT_A_ID = str(uuid.uuid4())
ASSET_B_ID = str(uuid.uuid4())
THREAT_B_ID = str(uuid.uuid4())


@pytest.fixture()
def client_a_http():
    from app.main import app
    from unittest.mock import MagicMock, patch
    from tests.supabase_mock import make_supabase_db

    db_a = make_supabase_db(client_id=CLIENT_A_ID, user_id=str(uuid.uuid4()))
    app.dependency_overrides[get_current_client_id] = lambda: CLIENT_A_ID

    with patch("app.api.assets.get_supabase_client", return_value=db_a), patch(
        "app.api.threats.get_supabase_client", return_value=db_a
    ):
        yield TestClient(app, raise_server_exceptions=False), db_a

    app.dependency_overrides.clear()


def test_get_asset_cross_tenant_returns_404(client_a_http):
    http, _db = client_a_http
    response = http.get(f"/api/assets/{ASSET_B_ID}", headers={"Authorization": "Bearer token-a"})
    assert response.status_code == 404, f"got {response.status_code}: {response.text}"


def test_get_threat_cross_tenant_returns_404(client_a_http):
    http, _db = client_a_http
    response = http.get(f"/api/threats/{THREAT_B_ID}", headers={"Authorization": "Bearer token-a"})
    assert response.status_code == 404


def test_approve_threat_cross_tenant_returns_404(client_a_http):
    http, _db = client_a_http
    response = http.post(f"/api/threats/{THREAT_B_ID}/approve", headers={"Authorization": "Bearer token-a"})
    assert response.status_code == 404


def test_audit_trail_cross_tenant_returns_404(client_a_http):
    http, _db = client_a_http
    response = http.get(f"/api/threats/{THREAT_B_ID}/audit-trail", headers={"Authorization": "Bearer token-a"})
    assert response.status_code == 404
