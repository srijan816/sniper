"""Test: IDOR tenant isolation — Client A cannot access Client B's resources."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

CLIENT_A_ID = str(uuid.uuid4())
CLIENT_B_ID = str(uuid.uuid4())
USER_A_ID = str(uuid.uuid4())
USER_B_ID = str(uuid.uuid4())
ASSET_B_ID = str(uuid.uuid4())
THREAT_B_ID = str(uuid.uuid4())


def _make_db_for(client_id: str, user_id: str):
    db = MagicMock()
    user = MagicMock()
    user.id = user_id
    user.email = f"user-{user_id[:8]}@test.com"
    db.auth.get_user.return_value = MagicMock(user=user)

    # Clients table — returns this user's client
    client_table = MagicMock()
    client_table.execute.return_value.data = [{"id": client_id, "owner_id": user_id}]
    db.table.return_value.select.return_value.eq.return_value.limit.return_value = client_table

    return db


@pytest.fixture()
def client_a_http():
    """HTTP client authenticated as Client A."""
    from app.main import app
    db_a = _make_db_for(CLIENT_A_ID, USER_A_ID)

    def _select_chain(*args, **kwargs):
        mock = MagicMock()
        # Default: return empty (nothing found for cross-tenant queries)
        mock.execute.return_value.data = []
        mock.eq.return_value = mock
        mock.limit.return_value = mock
        mock.in_.return_value = mock
        mock.order.return_value = mock
        return mock

    db_a.table.return_value.select.side_effect = _select_chain
    db_a.auth.get_user.return_value = MagicMock(user=MagicMock(
        id=USER_A_ID, email=f"user-{USER_A_ID[:8]}@test.com"
    ))

    # clients lookup specifically needs to return client A
    clients_mock = MagicMock()
    clients_mock.execute.return_value.data = [{"id": CLIENT_A_ID, "owner_id": USER_A_ID}]
    clients_mock.eq.return_value.limit.return_value.execute.return_value.data = [{"id": CLIENT_A_ID}]

    db_a.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"id": CLIENT_A_ID, "owner_id": USER_A_ID}
    ]

    with patch("app.api.deps.get_supabase_client", return_value=db_a):
        with patch("app.core.database.get_supabase_client", return_value=db_a):
            yield TestClient(app, raise_server_exceptions=False), db_a


def test_get_asset_cross_tenant_returns_404(client_a_http):
    """Client A cannot read Client B's asset — must get 404 (not 200)."""
    http, db = client_a_http
    # DB returns empty for ownership check — Client A does not own ASSET_B_ID
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    response = http.get(
        f"/api/assets/{ASSET_B_ID}",
        headers={"Authorization": "Bearer token-a"},
    )
    assert response.status_code == 404, (
        f"Expected 404 for cross-tenant asset access, got {response.status_code}: {response.text}"
    )


def test_get_threat_cross_tenant_returns_404(client_a_http):
    """Client A cannot read Client B's threat — must get 404."""
    http, db = client_a_http
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    response = http.get(
        f"/api/threats/{THREAT_B_ID}",
        headers={"Authorization": "Bearer token-a"},
    )
    assert response.status_code == 404, (
        f"Expected 404 for cross-tenant threat access, got {response.status_code}: {response.text}"
    )


def test_approve_threat_cross_tenant_returns_404(client_a_http):
    """Client A cannot approve Client B's threat."""
    http, db = client_a_http
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    response = http.post(
        f"/api/threats/{THREAT_B_ID}/approve",
        headers={"Authorization": "Bearer token-a"},
    )
    assert response.status_code == 404


def test_audit_trail_cross_tenant_returns_404(client_a_http):
    """Client A cannot read Client B's threat audit trail."""
    http, db = client_a_http
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    response = http.get(
        f"/api/threats/{THREAT_B_ID}/audit-trail",
        headers={"Authorization": "Bearer token-a"},
    )
    assert response.status_code == 404
