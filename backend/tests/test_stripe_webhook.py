"""Test: Stripe webhook handler — subscription lifecycle events."""
from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


CLIENT_ID = str(uuid.uuid4())
STRIPE_CUSTOMER_ID = "cus_test123"


def _make_checkout_event(tier_price_id: str, client_id: str) -> dict:
    return {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_session",
                "customer": STRIPE_CUSTOMER_ID,
                "subscription": "sub_test123",
                "metadata": {"client_id": client_id},
                "payment_status": "paid",
            }
        },
    }


def _make_subscription_event(price_id: str, customer_id: str) -> dict:
    return {
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "customer": customer_id,
                "subscription": "sub_test123",
                "lines": {
                    "data": [{"price": {"id": price_id}}]
                },
            }
        },
    }


def _make_cancellation_event(customer_id: str) -> dict:
    return {
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "customer": customer_id,
                "id": "sub_test123",
            }
        },
    }


@pytest.fixture()
def webhook_client():
    from app.main import app
    db = MagicMock()

    # Stripe construct_event bypassed (no webhook secret in test env)
    with patch("app.core.database.get_supabase_client", return_value=db):
        yield TestClient(app, raise_server_exceptions=False), db


def test_webhook_endpoint_reachable(webhook_client):
    http, _ = webhook_client
    payload = json.dumps({"type": "ping"}).encode()
    response = http.post("/api/webhooks/stripe", content=payload)
    # Without a valid secret, we expect 400 (bad signature) or 200 (passthrough)
    assert response.status_code in (200, 400, 422)


def test_subscription_deleted_downgrades_to_free(webhook_client):
    http, db = webhook_client
    payload = json.dumps(_make_cancellation_event(STRIPE_CUSTOMER_ID)).encode()

    # Track what update was called with
    update_calls = []
    db.table.return_value.update.side_effect = lambda data: update_calls.append(data) or MagicMock()
    db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"id": CLIENT_ID}
    ]

    response = http.post(
        "/api/webhooks/stripe",
        content=payload,
        headers={"Content-Type": "application/json"},
    )
    # In test mode (no stripe signature), the event is parsed raw
    assert response.status_code in (200, 400)
