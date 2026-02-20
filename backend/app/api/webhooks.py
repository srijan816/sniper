"""Stripe webhook handlers"""
from fastapi import APIRouter, Request, HTTPException
from app.core.config import get_settings
import json

router = APIRouter()

TIER_LIMITS = {
    "FREE": 0,
    "STARTER": 50,
    "GROWTH": 500,
    "AGENCY": 5000,
}


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhooks:
    - invoice.payment_succeeded → reset monthly count
    - customer.subscription.deleted → downgrade to FREE
    - checkout.session.completed → activate subscription
    """
    settings = get_settings()
    payload = await request.body()

    # In production: verify webhook signature with stripe.Webhook.construct_event()
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid payload")

    event_type = event.get("type", "")

    if event_type == "invoice.payment_succeeded":
        # Reset monthly threat count
        customer_id = event.get("data", {}).get("object", {}).get("customer")
        if customer_id:
            # In production: UPDATE clients SET current_month_count = 0 WHERE stripe_customer_id = customer_id
            return {"status": "monthly_count_reset", "customer": customer_id}

    elif event_type == "customer.subscription.deleted":
        # Downgrade to FREE
        customer_id = event.get("data", {}).get("object", {}).get("customer")
        if customer_id:
            # In production: UPDATE clients SET subscription_tier = 'FREE', monthly_threat_limit = 0
            return {"status": "downgraded_to_free", "customer": customer_id}

    elif event_type == "checkout.session.completed":
        # Activate subscription
        session = event.get("data", {}).get("object", {})
        customer_id = session.get("customer")
        # In production: parse the price ID to determine tier, update client record
        return {"status": "subscription_activated", "customer": customer_id}

    return {"status": "ignored", "event_type": event_type}
