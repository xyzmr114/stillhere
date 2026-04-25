# Fix: Stripe Webhook Signature Verification

## What it does (1 paragraph)

Fix the `/stripe/webhook` endpoint so it **unconditionally requires** a valid Stripe signature — no fallback to unsigned payload parsing when `STRIPE_WEBHOOK_SECRET` is unset. This closes a critical security hole where anyone could forge a `checkout.session.completed` event and grant paid access to any user.

## Current behavior (buggy)

```python
if settings.stripe_webhook_secret:
    event = stripe.Webhook.construct_event(body, sig, settings.stripe_webhook_secret)
else:
    event = json.loads(body)  # ← INSECURE: accepts ANY unsigned payload
```

When `STRIPE_WEBHOOK_SECRET` is not set, the webhook accepts raw JSON. A self-hosted deployer who hasn't configured the secret is vulnerable to payment fraud.

## Fixed behavior

- **If `stripe_webhook_secret` is set**: verify signature with `stripe.Webhook.construct_event` (existing path)
- **If `stripe_webhook_secret` is NOT set**: return HTTP 500 with `{"detail": "Stripe webhook secret not configured"}` and log a CRITICAL message — the service should not be processing payments without this configured
- The `json.loads` fallback for unverified payloads is **removed entirely**

## Acceptance criteria

1. `POST /stripe/webhook` with no `stripe-signature` header and no `STRIPE_WEBHOOK_SECRET` configured → HTTP 500 `{"detail": "Stripe webhook secret not configured"}`
2. `POST /stripe/webhook` with a valid Stripe signature and `STRIPE_WEBHOOK_SECRET` set → HTTP 200 `{"ok": true}` and payment recorded (existing behavior)
3. `POST /stripe/webhook` with an invalid/mismatched signature and `STRIPE_WEBHOOK_SECRET` set → HTTP 400 `{"detail": "Invalid signature"}` (existing behavior)
4. No code path exists that calls `json.loads(body)` to parse a Stripe event without signature verification
5. A CRITICAL-level log message is emitted when the webhook secret is missing on first request

## Edge cases

- If Stripe sends a webhook but the env var is unset in production → reject cleanly, not silently
- The public checkout (`/stripe/buy`) and authenticated checkout (`/stripe/checkout`) endpoints are **not** affected — only the webhook
- Running in test/dev without a webhook secret configured: developers must set `STRIPE_WEBHOOK_SECRET=whsec_...` even for local Stripe CLI forwarding (`stripe listen --forward-to localhost:8000/stripe/webhook` provides the secret)
- `stripe.Webhook.construct_event` handles the timestamp check automatically (5-minute tolerance)

## Files to change

- `/home/harsh/docker/stillhere/backend/routes/stripe_payments.py` — remove the `else: json.loads(body)` branch
- `/home/harsh/docker/stillhere/backend/tests/test_stripe.py` — add test for missing-secret rejection

## Verification

```bash
cd /home/harsh/docker/stillhere/backend
python -m pytest tests/test_stripe.py -v
```
