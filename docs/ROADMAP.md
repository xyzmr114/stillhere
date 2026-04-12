# Still Here — Roadmap

> $5 lifetime per user. No subscriptions. Non-emergency line only, only as absolute last resort.

## Stack
Backend: FastAPI + Celery + Supabase + Redis
Frontend: Vanilla JS PWA
Deploy: Docker Compose (5 services)

---

## Phases 1–5 — Complete

Full escalation chain, contact voting, vacation mode, streaks, mutual check-ins, groups, family portal, API keys, Home Assistant / Alexa webhooks, Stripe skeleton, Web Push + SMTP self-hosting, Netcore P2P access.

---

## What's Next

### Tier 1 — Before real users

- [ ] Rate-limit login/register endpoints
- [ ] Email verification on signup (currently none)
- [ ] Delete account (GDPR baseline — wipe user + all contact data)
- [ ] Contact confirm web screen — no-app-required page for contacts who just got an SMS
- [ ] Stripe go-live — `sk_test_` → `sk_live_`, wire up webhook in Stripe dashboard

### Tier 2 — Core UX gaps

- [ ] Snooze / vacation UI — backend supports it, no frontend controls yet
- [ ] Check-in history + streak display — tracked in DB, not shown in app
- [ ] Onboarding flow — new users land in blank state; welcome email covers it but in-app flow missing
- [ ] Push permission prompt — no fallback messaging if user blocks notifications

### Tier 3 — Growth & trust

- [ ] Privacy policy + Terms of service — required before public launch
- [ ] Landing page waitlist / contact form
- [ ] Mutual check-in UI — backend done (`mutual.py`), no frontend
- [ ] Family portal UI — backend done, portal page is minimal

### Tier 4 — Self-hosting polish

- [ ] VAPID key auto-generation on first boot (currently manual)
- [ ] `netcore-start.sh` idempotency — errors if already initialized
- [ ] Docker healthchecks for API + worker (autoheal restarts but check is shallow)
- [ ] One-command install script for self-hosters

### Backlog

- [ ] Audit log UI (backend tracks events, no frontend)
- [ ] Alexa account linking (endpoint exists, no setup guide)
- [ ] iOS/Android wrapper (PWA install works but app store presence helps trust)
- [ ] i18n — escalation copy is English-only
- [ ] Shareable streak cards (social/viral)
- [ ] Multiple check-in windows (morning + night)

---

## Out of scope

- Live location tracking (privacy + battery)
- In-app messaging between contacts
- Video/voice check-ins
- Calling 911 — non-emergency line only, ever
