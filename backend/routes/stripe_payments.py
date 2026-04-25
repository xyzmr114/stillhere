import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from config import settings
from db import SessionLocal, get_session
from dependencies import get_current_user
from limiter import limiter

logger = logging.getLogger(__name__)

stripe.api_key = settings.stripe_secret_key

router = APIRouter(prefix="/stripe", tags=["stripe"])

SUCCESS_URL = settings.base_url + "/signin?paid=1"
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
@limiter.limit("5/minute")
def create_checkout_session(request: Request, user=Depends(get_current_user)):
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
@limiter.limit("5/minute")
def public_checkout(request: Request):
    """Unauthenticated checkout — anyone can pay directly. Webhook matches by email."""
    if not settings.stripe_secret_key:
        return RedirectResponse("/signin")
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
        return RedirectResponse("/signin")


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
        logger.critical("Stripe webhook secret not configured - rejecting webhook")
        raise HTTPException(status_code=500, detail="Stripe webhook secret not configured")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("client_reference_id")
        session_id = session.get("id")
        customer_email = session.get("customer_email") or (
            session.get("customer_details") or {}
        ).get("email")
        db = SessionLocal()
        try:
            if user_id:
                row = db.execute(
                    text(
                        "UPDATE users SET has_paid = true, paid_at = NOW(), "
                        "stripe_session_id = :sid, stripe_customer_email = :email "
                        "WHERE id::text = :uid AND has_paid = false "
                        "RETURNING email, name"
                    ),
                    {"uid": user_id, "sid": session_id, "email": customer_email},
                ).first()
                db.commit()
                if row:
                    logger.info("Payment recorded for user_id=%s session=%s", user_id, session_id)
                    try:
                        from services.email_svc import send_payment_confirmation_email
                        send_payment_confirmation_email(row.email, row.name or "there")
                    except Exception:
                        logger.exception("Failed to send payment confirmation email for user_id=%s", user_id)
            elif customer_email:
                result = db.execute(
                    text(
                        "UPDATE users SET has_paid = true, paid_at = NOW(), "
                        "stripe_session_id = :sid, stripe_customer_email = :email "
                        "WHERE email = :match_email AND has_paid = false "
                        "RETURNING id, name"
                    ),
                    {"sid": session_id, "email": customer_email, "match_email": customer_email},
                ).first()
                db.commit()
                if result:
                    logger.info("Payment recorded via email match=%s session=%s", customer_email, session_id)
                    try:
                        from services.email_svc import send_payment_confirmation_email
                        send_payment_confirmation_email(customer_email, result.name or "there")
                    except Exception:
                        logger.exception("Failed to send payment confirmation email for email=%s", customer_email)
                else:
                    logger.warning("Payment received but no matching unpaid user for email=%s session=%s", customer_email, session_id)
            else:
                logger.warning("Payment received with no user_id or email, session=%s", session_id)
        finally:
            db.close()

    return {"ok": True}
