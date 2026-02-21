from __future__ import annotations

"""Stripe webhook handlers (real Stripe event handling + Supabase updates)."""
import json

import stripe
from fastapi import APIRouter, HTTPException, Request

from app.core.config import get_settings
from app.core.database import get_supabase_client

router = APIRouter()

TIER_LIMITS = {
    "FREE": 0,
    "STARTER": 50,
    "GROWTH": 500,
    "AGENCY": 5000,
}


def _db():
    db = get_supabase_client()
    if db is None:
        raise HTTPException(status_code=503, detail="Supabase is not configured.")
    return db


def _tier_from_price_id(price_id: str | None, settings) -> str:
    if not price_id:
        return "FREE"
    mapping = {
        settings.stripe_starter_price_id: "STARTER",
        settings.stripe_growth_price_id: "GROWTH",
        settings.stripe_agency_price_id: "AGENCY",
    }
    return mapping.get(price_id, "FREE")


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhooks:
    - invoice.payment_succeeded → reset monthly count
    - customer.subscription.deleted → downgrade to FREE
    - checkout.session.completed → activate subscription
    """
    settings = get_settings()
    if settings.stripe_secret_key:
        stripe.api_key = settings.stripe_secret_key

    payload = await request.body()
    signature = request.headers.get("stripe-signature")

    try:
        if signature and settings.stripe_webhook_secret:
            event = stripe.Webhook.construct_event(payload=payload, sig_header=signature, secret=settings.stripe_webhook_secret)
        else:
            event = json.loads(payload.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Stripe webhook payload: {exc}") from exc

    event_type = event.get("type", "")
    data_object = event.get("data", {}).get("object", {}) or {}

    if event_type == "invoice.payment_succeeded":
        customer_id = data_object.get("customer")
        if customer_id:
            _db().table("clients").update({"current_month_count": 0}).eq("stripe_customer_id", customer_id).execute()
            return {"status": "monthly_count_reset", "customer": customer_id}

    if event_type in {"customer.subscription.deleted", "customer.subscription.paused"}:
        customer_id = data_object.get("customer")
        if customer_id:
            _db().table("clients").update({"subscription_tier": "FREE", "monthly_threat_limit": 0}).eq(
                "stripe_customer_id", customer_id
            ).execute()
            return {"status": "downgraded_to_free", "customer": customer_id}

    if event_type in {"checkout.session.completed", "customer.subscription.created", "customer.subscription.updated"}:
        customer_id = data_object.get("customer")
        if not customer_id:
            return {"status": "ignored", "event_type": event_type, "reason": "No customer id"}

        tier = "FREE"
        if event_type == "checkout.session.completed":
            metadata = data_object.get("metadata") or {}
            requested_tier = (metadata.get("subscription_tier") or "").upper()
            if requested_tier in TIER_LIMITS:
                tier = requested_tier
            else:
                subscription_id = data_object.get("subscription")
                if subscription_id and settings.stripe_secret_key:
                    subscription = stripe.Subscription.retrieve(subscription_id, expand=["items.data.price"])
                    items = subscription.get("items", {}).get("data", [])
                    price_id = items[0].get("price", {}).get("id") if items else None
                    tier = _tier_from_price_id(price_id, settings)
        else:
            items = data_object.get("items", {}).get("data", [])
            price_id = items[0].get("price", {}).get("id") if items else None
            tier = _tier_from_price_id(price_id, settings)

        limit = TIER_LIMITS.get(tier, 0)
        updated = (
            _db()
            .table("clients")
            .update(
                {
                    "subscription_tier": tier,
                    "monthly_threat_limit": limit,
                    "stripe_customer_id": customer_id,
                }
            )
            .eq("stripe_customer_id", customer_id)
            .execute()
        )

        # First subscription may not have customer_id linked yet; fallback to email.
        if not (updated.data or []):
            customer_email = (
                data_object.get("customer_details", {}).get("email")
                or data_object.get("customer_email")
                or data_object.get("metadata", {}).get("legal_contact_email")
            )
            if customer_email:
                _db().table("clients").update(
                    {
                        "subscription_tier": tier,
                        "monthly_threat_limit": limit,
                        "stripe_customer_id": customer_id,
                    }
                ).eq("legal_contact_email", customer_email).execute()

        return {"status": "subscription_updated", "customer": customer_id, "tier": tier}

    return {"status": "ignored", "event_type": event_type}
