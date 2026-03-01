"""Stripe Checkout session creation endpoint."""
import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_client_id
from app.core.config import get_settings
from app.core.database import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()

PLAN_PRICE_MAP = {
    "STARTER": "stripe_starter_price_id",
    "GROWTH": "stripe_growth_price_id",
    "AGENCY": "stripe_agency_price_id",
}


class CheckoutRequest(BaseModel):
    plan: str  # STARTER | GROWTH | AGENCY
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    url: str


@router.post("/create", response_model=CheckoutResponse)
async def create_checkout_session(
    data: CheckoutRequest,
    client_id: str = Depends(get_current_client_id),
):
    """Create a Stripe Checkout session for the selected plan."""
    settings = get_settings()
    plan = data.plan.upper()
    if plan not in PLAN_PRICE_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {plan}. Must be STARTER, GROWTH, or AGENCY.")
    if plan == "AGENCY":
        raise HTTPException(status_code=400, detail="Agency plan requires contacting sales. Email sales@sniperip.com.")

    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured.")

    price_id = getattr(settings, PLAN_PRICE_MAP[plan], "")
    if not price_id:
        raise HTTPException(status_code=503, detail=f"Stripe price ID for {plan} is not configured.")

    stripe.api_key = settings.stripe_secret_key

    # Look up Stripe customer ID for this client if it exists
    db = get_supabase_client()
    customer_id = None
    if db:
        try:
            res = db.table("clients").select("stripe_customer_id").eq("id", client_id).limit(1).execute()
            rows = res.data or []
            if rows:
                customer_id = rows[0].get("stripe_customer_id")
        except Exception as exc:
            logger.warning("Could not load stripe_customer_id for client %s: %s", client_id, exc)

    try:
        session_kwargs = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": data.success_url,
            "cancel_url": data.cancel_url,
            "metadata": {"client_id": client_id},
            "allow_promotion_codes": True,
        }
        if customer_id:
            session_kwargs["customer"] = customer_id

        session = stripe.checkout.Session.create(**session_kwargs)
        return CheckoutResponse(url=session.url)
    except stripe.StripeError as exc:
        logger.error("Stripe checkout session creation failed for client %s: %s", client_id, exc)
        raise HTTPException(status_code=502, detail="Failed to create Stripe Checkout session.") from exc
