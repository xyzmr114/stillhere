import json
import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from config import settings
from db import SessionLocal, get_session
from dependencies import get_current_user

logger = logging.getLogger(__name__)

stripe.api_key = settings.stripe_secret_key

router = APIRouter(prefix="/stripe", tags=["stripe"])

SUCCESS_URL = settings.base_url + "/app?paid=1"
CANCEL_URL = settings.base_url + "/"

LINE_ITEMS = [{
    "price_data": {
        "currency": "usd",
        "unit_amount": 500,
        "product_data": {
            "name": "Still Here — Lifetime Access",
            "description": "One payment. Yours forever. No subscriptions.",
        },
    },
    "quantity": 1,
}]


@router.post("/checkout")
def create_checkout_session(user=Depends(get_current_user)):
    if user.get("has_paid"):
        raise HTTPException(status_code=400, detail="Already paid")
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Payments not configured")
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=LINE_ITEMS,
            success_url=SUCCESS_URL,
            cancel_url=CANCEL_URL,
            client_reference_id=str(user["id"]),
            customer_email=user.get("email"),
        )
        return {"url": session.url}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/buy")
def public_checkout():
    """Unauthenticated checkout — anyone can pay directly. Webhook matches by email."""
    if not settings.stripe_secret_key:
        return RedirectResponse("/app")
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=LINE_ITEMS,
            success_url=SUCCESS_URL,
            cancel_url=CANCEL_URL,
        )
        return RedirectResponse(session.url)
    except stripe.error.StripeError as e:
        logger.error("Public checkout failed: %s", e)
        return RedirectResponse("/app")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("stripe-signature", "")

    if settings.stripe_webhook_secret:
        try:
            event = stripe.Webhook.construct_event(body, sig, settings.stripe_webhook_secret)
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
        except Exception:
            logger.exception("Failed to construct Stripe webhook event")
            raise HTTPException(status_code=400, detail="Webhook error")
    else:
        try:
            event = json.loads(body)
        except Exception:
            logger.exception("Failed to parse webhook payload as JSON")
            raise HTTPException(status_code=400, detail="Invalid payload")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("client_reference_id")
        customer_email = session.get("customer_email") or (
            session.get("customer_details") or {}
        ).get("email")
        db = SessionLocal()
        try:
            if user_id:
                db.execute(
                    text("UPDATE users SET has_paid = true WHERE id::text = :uid"),
                    {"uid": user_id},
                )
                db.commit()
            elif customer_email:
                db.execute(
                    text("UPDATE users SET has_paid = true WHERE email = :email"),
                    {"email": customer_email},
                )
                db.commit()
        finally:
            db.close()

    return {"ok": True}
