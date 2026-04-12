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

## Self-hosting on a Linux VPS

### 1. Deploy the app

```bash
git clone https://github.com/xyzmr114/stillhere.git
cd stillhere
nano .env          # fill in your credentials
docker-compose up -d --build
```

Still Here is now running at `http://localhost:8000` on your VPS. The escalation chain (SMS, email, push) works over the public internet automatically via Twilio and Resend — no extra setup needed.

### 2. Give trusted contacts private access via Netcore

Rather than exposing your server to the public internet, Still Here uses [Netcore](https://www.netcore.network/) for private peer-to-peer access. This lets your emergency contacts and family reach your instance directly — no open ports, no domain, no reverse proxy.

**On Alice's VPS (the host):**

```bash
# Download the ncp2p binary from https://www.netcore.network/services
unzip ncp2p-linux-x86_64.zip
chmod +x ncp2p

./ncp2p initDb           # generates your identity + assigns internal IP
sudo ./ncp2p setup $USER # sets up WireGuard interface (re-run after reboot)
./ncp2p                  # starts the Netcore client
```

Open `http://127.0.0.1:8080/` → **Identity** tab → **Copy peer_user JSON** and send it to Bob.

**On Bob's machine (the contact):**

1. Download and run `ncp2p` from [netcore.network/services](https://www.netcore.network/services)
2. Open `http://127.0.0.1:8080/` → **Peer users** → paste Alice's JSON → **Add**
3. Copy his own peer_user JSON and send it back to Alice
4. Alice adds Bob the same way

Once both sides have added each other, Bob can open Alice's Still Here instance directly:

```
http://<alice-internal-ip>:8000/portal   # family portal — live check-in status
http://<alice-internal-ip>:8000/app      # full app
```

Alice's internal IP is shown in `http://127.0.0.1:8080/` under **Overview**.

> The connection is direct and encrypted — traffic goes machine-to-machine, never through a central server. Bob can only reach Alice's instance while both have `ncp2p` running.

### 3. Architecture with Netcore

```
Alice's VPS
├── docker-compose (Still Here on :8000)
└── ncp2p (WireGuard mesh, internal IP e.g. 10.202.48.44)
        │
        │  encrypted P2P tunnel
        │
Bob's laptop
└── ncp2p → browser → http://10.202.48.44:8000/portal
```

Twilio/Resend escalation still fires over the public internet as normal. Netcore is only for human access — family portal, setup, monitoring.

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
