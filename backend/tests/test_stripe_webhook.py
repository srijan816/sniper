"""Test: Stripe webhook handler — subscription lifecycle events."""
from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.supabase_mock import make_chainable_table

CLIENT_ID = str(uuid.uuid4())
STRIPE_CUSTOMER_ID = "cus_test123"


def _make_cancellation_event(customer_id: str) -> dict:
    return {
        "type": "customer.subscription.deleted",
        "data": {"object": {"customer": customer_id, "id": "sub_test123"}},
    }


@pytest.fixture()
def webhook_client():
    from app.main import app

    db = MagicMock()
    clients_table = make_chainable_table(update_data=[{"id": CLIENT_ID}])
    db.table.return_value = clients_table

    with patch("app.api.webhooks.get_supabase_client", return_value=db):
        yield TestClient(app, raise_server_exceptions=False), db


def test_webhook_endpoint_reachable(webhook_client):
    http, _ = webhook_client
    payload = json.dumps({"type": "ping"}).encode()
    response = http.post("/api/webhooks/stripe", content=payload)
    assert response.status_code in (200, 400, 422)


def test_subscription_deleted_downgrades_to_free(webhook_client):
    http, db = webhook_client
    payload = json.dumps(_make_cancellation_event(STRIPE_CUSTOMER_ID)).encode()
    response = http.post("/api/webhooks/stripe", content=payload, headers={"Content-Type": "application/json"})
    assert response.status_code == 200
    assert response.json().get("status") == "downgraded_to_free"
    db.table.return_value.update.assert_called()


def test_stripe_webhook_requires_signature_in_production(webhook_client):
    http, _ = webhook_client
    payload = json.dumps(_make_cancellation_event(STRIPE_CUSTOMER_ID)).encode()
    with patch("app.api.webhooks.get_settings") as mock_settings:
        mock_settings.return_value.environment = "production"
        mock_settings.return_value.stripe_webhook_secret = ""
        mock_settings.return_value.stripe_secret_key = "sk_test"
        response = http.post("/api/webhooks/stripe", content=payload, headers={"Content-Type": "application/json"})
    assert response.status_code == 400
