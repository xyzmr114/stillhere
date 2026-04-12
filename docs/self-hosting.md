# Self-Hosting Still Here

Still Here is fully self-hostable. You need a Linux server, Docker, and credentials for the services you want to use. Cloud services (Firebase, Twilio, Resend) are optional — self-hosted alternatives exist for each.

## Quick Start

```bash
git clone https://github.com/xyzmr114/stillhere.git
cd stillhere
nano .env          # see env-reference.md for all variables
docker-compose up -d --build
```

The app runs on port `8000`. Put it behind a reverse proxy (Caddy, nginx) for HTTPS.

---

## Minimum viable setup

To run with zero paid services:

```env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
JWT_SECRET=your-random-secret
REDIS_URL=redis://redis:6379
CELERY_BROKER=redis://redis:6379/0
BASE_URL=http://your-server-ip:8000

PUSH_PROVIDER=webpush
WEBPUSH_VAPID_PUBLIC_KEY=...   # generate below
WEBPUSH_VAPID_PRIVATE_KEY=...
WEBPUSH_VAPID_EMAIL=you@example.com

EMAIL_PROVIDER=smtp
SMTP_HOST=your-smtp-host
SMTP_PORT=587
SMTP_USER=you@example.com
SMTP_PASSWORD=yourpassword
EMAIL_FROM=Still Here <you@example.com>
```

**SMS requires Twilio** — there's no free self-hosted alternative for reliable SMS delivery. If you don't set Twilio credentials, the escalation chain will still send push and email; SMS steps are skipped.

**Non-emergency calls require Twilio** — the welfare check call step is skipped without it.

---

## Generating VAPID keys (Web Push)

```bash
pip install py-vapid
vapid --gen
```

This outputs a `vapid_private.pem` and `vapid_public.pem`. Extract the keys:

```bash
vapid --applicationServerKey
```

Copy the public key into `WEBPUSH_VAPID_PUBLIC_KEY` and the private key into `WEBPUSH_VAPID_PRIVATE_KEY`.

---

## Reverse proxy with Caddy

```
yourdomain.com {
    reverse_proxy localhost:8000
}
```

Update `BASE_URL` in `.env` to `https://yourdomain.com` — this is used for check-in links in emails and SMS.

---

## Private access with Netcore

If you want to give specific people (family, emergency contacts) access to your instance without a public URL, see [netcore.md](./netcore.md).

---

## Database

Still Here uses Supabase Postgres in production, but any PostgreSQL database works. The schema uses raw SQL — no ORM migrations. Find the schema in `docs/schema.sql` (or run against a fresh Supabase project which handles setup).

---

## Services

| Service | docker-compose name | Purpose |
|---------|-------------------|---------|
| `api` | FastAPI app | Port 8000, handles all HTTP |
| `worker` | Celery worker | Processes escalation tasks |
| `beat` | Celery beat | Polls every 60s, fires escalations |
| `redis` | Redis | Task broker and result backend |

Run individual services: `docker-compose up api worker beat redis`

---

## Updating

```bash
git pull
docker-compose up -d --build
```

No migration runner — if the schema changed, check the release notes for any SQL to run manually.
