"""Shared fixtures for the SniperIP backend test suite."""
from __future__ import annotations

import os
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ── Minimal env vars so settings / imports don't crash ──────────────────────
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_DB_URL", "postgresql://postgres:password@localhost:5432/postgres")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_xxx")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test")
os.environ.setdefault("STRIPE_STARTER_PRICE_ID", "price_starter_test")
os.environ.setdefault("STRIPE_GROWTH_PRICE_ID", "price_growth_test")
os.environ.setdefault("ADMIN_EMAILS", "admin@test.com")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("STRIPE_WEBHOOK_ALLOW_UNSIGNED", "true")


CLIENT_A = str(uuid.uuid4())
CLIENT_B = str(uuid.uuid4())
USER_A = str(uuid.uuid4())
USER_B = str(uuid.uuid4())
ASSET_A = str(uuid.uuid4())
ASSET_B = str(uuid.uuid4())
THREAT_A = str(uuid.uuid4())
THREAT_B = str(uuid.uuid4())

TOKEN_A = "token-a"
TOKEN_B = "token-b"
ADMIN_TOKEN = "token-admin"


def _make_supabase_mock(client_id: str, user_id: str, is_admin: bool = False):
    """Return a MagicMock Supabase client scoped to one tenant."""
    db = MagicMock()

    # auth.get_user
    user = MagicMock()
    user.id = user_id
    user.email = "admin@test.com" if is_admin else f"user-{user_id[:8]}@test.com"
    db.auth.get_user.return_value = MagicMock(user=user)

    # clients table
    client_row = [{"id": client_id, "owner_id": user_id}]
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = client_row

    return db


@pytest.fixture()
def app():
    from app.main import app as fastapi_app
    return fastapi_app


@pytest.fixture()
def client_a(app):
    db_mock = _make_supabase_mock(CLIENT_A, USER_A)
    with patch("app.core.database.get_supabase_client", return_value=db_mock):
        with patch("app.api.deps.get_supabase_client", return_value=db_mock):
            yield TestClient(app), db_mock


@pytest.fixture()
def client_b(app):
    db_mock = _make_supabase_mock(CLIENT_B, USER_B)
    with patch("app.core.database.get_supabase_client", return_value=db_mock):
        with patch("app.api.deps.get_supabase_client", return_value=db_mock):
            yield TestClient(app), db_mock


@pytest.fixture()
def admin_client(app):
    db_mock = _make_supabase_mock(CLIENT_A, USER_A, is_admin=True)
    with patch("app.core.database.get_supabase_client", return_value=db_mock):
        with patch("app.api.deps.get_supabase_client", return_value=db_mock):
            yield TestClient(app), db_mock
