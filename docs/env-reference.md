# Environment Variable Reference

Copy `.env.example` to `.env` and fill in the values you need.

---

## Core (required)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET` | Secret for signing auth tokens — use a long random string |
| `REDIS_URL` | Redis URL for Celery broker |
| `CELERY_BROKER` | Usually same as `REDIS_URL` with `/0` appended |
| `BASE_URL` | Public URL of your instance — used in email/SMS links |

---

## Push Notifications

### Option A — Firebase (cloud, default)

| Variable | Description |
|----------|-------------|
| `PUSH_PROVIDER` | Set to `firebase` (default) |
| `FIREBASE_CRED_PATH` | Path to your Firebase Admin SDK JSON file, relative to repo root |
| `FIREBASE_API_KEY` | Firebase web API key |
| `FIREBASE_AUTH_DOMAIN` | e.g. `your-project.firebaseapp.com` |
| `FIREBASE_PROJECT_ID` | Firebase project ID |
| `FIREBASE_STORAGE_BUCKET` | e.g. `your-project.firebasestorage.app` |
| `FIREBASE_MESSAGING_SENDER_ID` | Numeric sender ID |
| `FIREBASE_APP_ID` | Firebase app ID |
| `FIREBASE_MEASUREMENT_ID` | Optional, for Analytics |
| `FIREBASE_VAPID_KEY` | Web Push certificate from Firebase Console |

### Option B — Web Push (self-hosted)

| Variable | Description |
|----------|-------------|
| `PUSH_PROVIDER` | Set to `webpush` |
| `WEBPUSH_VAPID_PUBLIC_KEY` | VAPID public key (generate with `vapid --gen`) |
| `WEBPUSH_VAPID_PRIVATE_KEY` | VAPID private key |
| `WEBPUSH_VAPID_EMAIL` | Contact email for push service |

See [self-hosting.md](./self-hosting.md#generating-vapid-keys-web-push) for key generation.

---

## Email

### Option A — Resend (cloud, default)

| Variable | Description |
|----------|-------------|
| `EMAIL_PROVIDER` | Set to `resend` (default) |
| `RESEND_API_KEY` | Resend API key |
| `EMAIL_FROM` | Sender address, e.g. `Still Here <noreply@yourdomain.com>` |

### Option B — SMTP

Works with any SMTP provider. Set `SMTP_PRESET` to auto-fill host/port, or set `SMTP_HOST` manually.

| Variable | Description |
|----------|-------------|
| `EMAIL_PROVIDER` | Set to `smtp` |
| `SMTP_PRESET` | Provider shorthand — see table below |
| `SMTP_HOST` | Override host (leave blank if using a preset) |
| `SMTP_PORT` | Override port (leave blank if using a preset) |
| `SMTP_USER` | SMTP login (usually your email address) |
| `SMTP_PASSWORD` | SMTP password or API key |
| `SMTP_TLS` | `true` for STARTTLS, ignored when using SSL preset |
| `EMAIL_FROM` | Sender address, e.g. `Still Here <noreply@yourdomain.com>` |

**Presets:**

| `SMTP_PRESET` | Provider | Notes |
|---|---|---|
| `brevo` | Brevo (Sendinblue) | Use SMTP key as password |
| `resend` | Resend SMTP | Username is `resend`, password is your API key |
| `gmail` | Gmail | Requires an App Password, not your account password |
| `mailgun` | Mailgun | Use SMTP credentials from Mailgun dashboard |
| `mailjet` | Mailjet | Use API key as username, secret key as password |
| `sendgrid` | SendGrid | Username is `apikey`, password is your API key |
| `zoho` | Zoho Mail | Standard Zoho SMTP credentials |
| `cpanel` | cPanel / DirectAdmin | Set `SMTP_HOST=mail.yourdomain.com` alongside preset |
| `local` | Postfix / local MTA | No auth, port 25 — for self-hosted mail servers |

---

## SMS & Voice (Twilio)

Required for SMS escalation and non-emergency welfare calls. No self-hosted alternative.

| Variable | Description |
|----------|-------------|
| `TWILIO_ACCOUNT_SID` | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_VERIFY_SID` | Verify service SID (for phone verification) |
| `DEMO_SMS_TO` | Phone number for test SMS (optional) |

---

## Auth

| Variable | Description |
|----------|-------------|
| `AUTH0_DOMAIN` | Auth0 domain (optional — enables Google/social login) |
| `AUTH0_CLIENT_ID` | Auth0 client ID |

---

## Payments (optional)

| Variable | Description |
|----------|-------------|
| `STRIPE_SECRET_KEY` | Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |

---

## AWS (legacy, unused)

`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` — retained for compatibility, not used in current builds.
