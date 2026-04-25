# Feature: Twilio Inbound STOP Webhook

## What it does
Handle Twilio's inbound SMS webhook so users can opt out of SMS notifications by texting STOP. Without this, the app violates Twilio's acceptable use policy and keeps sending SMS after users opt out.

## Background
- Twilio sends an inbound SMS webhook to the app when a user replies to an SMS
- Standard keywords: STOP, STOPALL, UNSUBSCRIBE, CANCEL, END (opt-out) and START, YES, UNSTOP (opt-in)
- The app must respond with valid TwiML XML
- Phone numbers in the DB are stored without formatting (e.g., `+15551234567`)

## API Endpoint

### `POST /webhooks/twilio/sms`

**Authentication:** None (Twilio webhooks are authenticated via signature header)

**Request (Twilio POST):**
| Field | Description |
|-------|-------------|
| `From` | Sender phone number |
| `To` | Recipient phone number (the Twilio number) |
| `Body` | Message text (e.g., "STOP") |

**Headers:**
| Field | Description |
|-------|-------------|
| `X-Twilio-Signature` | HMAC-SHA1 signature for request validation |

**Response:** `200 OK` with `text/xml` content (TwiML)

**TwiML Response:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>You have been unsubscribed. To re-subscribe, reply START.</Message>
</Response>
```

## Implementation

### Step 1 — Validate Twilio signature
Use `TWILIO_AUTH_TOKEN` from settings to validate `X-Twilio-Signature` on every request. If invalid, return `403 Forbidden`. This prevents spoofing of the webhook endpoint.

Signature validation:
1. Build the full URL (including scheme, host, and path)
2. Sort all POST parameters alphabetically
3. Concatenate them with `&` 
4. Prepend the full URL with `&` 
5. Compute HMAC-SHA1 using `TWILIO_AUTH_TOKEN` as key
6. Base64-encode the result
7. Compare against `X-Twilio-Signature` (constant-time comparison)

### Step 2 — Parse and normalize phone number
`From` phone comes as `+1XXXXXXXXXX` (E.164 format). The DB stores the same format. Normalize consistently.

### Step 3 — Handle opt-out keywords
| Keyword (case-insensitive) | Action |
|---------------------------|--------|
| `STOP`, `STOPALL`, `UNSUBSCRIBE`, `CANCEL`, `END` | Set `notify_sms = False` |
| `START`, `YES`, `UNSTOP` | Set `notify_sms = True` |
| `HELP` | Return help message |
| Anything else | Acknowledge silently |

### Step 4 — Update user in DB
Look up user by `phone` matching the `From` field. If found, update `notify_sms`. Use raw SQL with parameterized query.

### Step 5 — Return TwiML
Always return TwiML (200 OK), even if user not found. Twilio requires a 200 response.

## Data Model
No new tables. Updates `users.notify_sms` column.

## Files to Create/Modify
- `backend/routes/webhooks.py` — Add `POST /webhooks/twilio/sms` endpoint
- `backend/config.py` — Already has `twilio_auth_token` (line 45), confirm it's accessible

## Edge Cases
| Scenario | Handling |
|----------|----------|
| User not found by phone | Return TwiML acknowledgement, no DB update |
| Invalid Twilio signature | Return 403, log warning |
| Missing `From` or `Body` field | Return TwiML acknowledgement |
| DB error on update | Return TwiML acknowledgement, log error |
| Empty Body | Acknowledge silently |

## Acceptance Criteria
1. `POST /webhooks/twilio/sms` with valid signature and `Body=STOP` sets `notify_sms=False` for the user with matching phone
2. `POST /webhooks/twilio/sms` with valid signature and `Body=START` sets `notify_sms=True`
3. Invalid `X-Twilio-Signature` returns 403
4. Response is valid TwiML XML with `Content-Type: text/xml`
5. Unknown keywords are acknowledged without error
6. Missing user is acknowledged without error
7. The existing `/webhooks/alexa` and `/webhooks/sensor` routes are unaffected

## Verification
- Unit test: signature validation with known token
- Unit test: STOP keyword sets `notify_sms=False`
- Unit test: START keyword sets `notify_sms=True`  
- Unit test: invalid signature returns 403
- Unit test: unknown keyword returns TwiML acknowledgement
- Manual: send POST to `/webhooks/twilio/sms` with Twilio test credentials
