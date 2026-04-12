# Still Here

A safety check-in app. Set a daily check-in time — if you miss it, an escalation chain fires automatically.

**Escalation chain:** push notification → email → SMS to emergency contacts → non-emergency call

## Stack

- **Backend** — FastAPI + Celery (worker + beat scheduler)
- **Database** — Supabase Postgres (raw SQL, no ORM)
- **Frontend** — Vanilla JS PWA
- **Notifications** — Firebase Cloud Messaging
- **SMS** — Twilio
- **Email** — Resend
- **Auth** — JWT + Auth0 (optional) + API keys
- **Infra** — Docker Compose, Redis broker

## Running locally

Copy `.env.example` to `.env` and fill in credentials, then:

```bash
docker-compose up --build
```

| Service | URL |
|---------|-----|
| App | http://localhost:8000/app |
| API docs | http://localhost:8000/docs |

Individual services: `docker-compose up api` / `worker` / `beat`

## Tests

```bash
pytest backend/tests/
```

Tests hit a real database (configured in `.env`) — no mocks.

## Environment variables

See `.env.example` for all required variables. Key ones:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Supabase Postgres connection string |
| `JWT_SECRET` | Token signing secret |
| `REDIS_URL` | Redis broker |
| `FIREBASE_API_KEY` | FCM web client key |
| `FIREBASE_VAPID_KEY` | Push subscription key |
| `TWILIO_*` | SMS + voice calls |
| `RESEND_API_KEY` | Transactional email |
| `STRIPE_SECRET_KEY` | Payments |
