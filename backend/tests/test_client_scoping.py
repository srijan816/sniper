"""Tests for explicit client path scoping and `/me` aliases."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


CLIENT_ID = str(uuid.uuid4())
OTHER_CLIENT_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())


def _make_db():
    db = MagicMock()
    user = MagicMock()
    user.id = USER_ID
    user.email = "owner@test.com"
    db.auth.get_user.return_value = MagicMock(user=user)

    row = {
        "id": CLIENT_ID,
        "owner_id": USER_ID,
        "company_name": "Acme",
        "legal_contact_name": "Jane Doe",
        "legal_contact_email": "legal@acme.test",
        "subscription_tier": "FREE",
        "monthly_threat_limit": 0,
        "current_month_count": 0,
        "whitelist_domains": [],
        "automation_rules": {},
        "notification_prefs": {},
        "slack_webhook_url": None,
        "webhook_url": None,
        "webhook_secret": None,
        "created_at": "2026-03-01T00:00:00+00:00",
    }

    chain = MagicMock()
    chain.eq.return_value = chain
    chain.limit.return_value = chain
    chain.order.return_value = chain
    chain.execute.return_value.data = [row]
    db.table.return_value.select.return_value = chain
    return db


def test_clients_me_alias_resolves_to_authenticated_client():
    from app.main import app

    db = _make_db()
    with patch("app.core.database.get_supabase_client", return_value=db):
        with patch("app.api.deps.get_supabase_client", return_value=db):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/api/clients/me", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200, response.text
    assert response.json()["id"] == CLIENT_ID


def test_clients_foreign_path_returns_404_before_data_access():
    from app.main import app

    db = _make_db()
    with patch("app.core.database.get_supabase_client", return_value=db):
        with patch("app.api.deps.get_supabase_client", return_value=db):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get(f"/api/clients/{OTHER_CLIENT_ID}", headers={"Authorization": "Bearer token"})

    assert response.status_code == 404, response.text


def test_notification_settings_legacy_alias_still_works():
    from app.main import app

    db = _make_db()
    with patch("app.core.database.get_supabase_client", return_value=db):
        with patch("app.api.deps.get_supabase_client", return_value=db):
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get("/api/clients/me/notification-settings", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200, response.text
    assert response.json()["notification_prefs"] == {}
