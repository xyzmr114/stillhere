# Still Here — Roadmap

> $5 lifetime per user. No subscriptions. Non-emergency line only, only as absolute last resort.

## Stack
Backend: FastAPI + Celery + Supabase + Redis
Frontend: Vanilla JS PWA
Deploy: Docker Compose (5 services)
Mobile: Capacitor (iOS + Android — wraps existing frontend, no rewrite)

---

## Phases 1–5 — Complete

Full escalation chain, contact voting, vacation mode, streaks, mutual check-ins, groups, family portal, API keys, Home Assistant / Alexa webhooks, Stripe skeleton, Web Push + SMTP self-hosting, Netcore P2P access.

---

## What's Next

### Tier 1 — Before real users ✅ Done

- [x] Rate-limit login/register endpoints
- [x] Email verification on signup
- [x] Delete account (GDPR baseline)
- [x] Contact confirm web screen
- [ ] Stripe go-live — `sk_test_` → `sk_live_`, wire up webhook in Stripe dashboard

### Tier 2 — Core UX gaps

- [x] Snooze / vacation UI — timezone fix, active states, status card
- [ ] Check-in history + streak display — tracked in DB, not shown in app
- [ ] Onboarding flow — new users land in blank state
- [ ] Push permission prompt — no fallback messaging if user blocks notifications

### Tier 3 — Growth & trust

- [ ] Privacy policy + Terms of service — required before public launch
- [ ] Landing page waitlist / contact form
- [ ] Mutual check-in UI — backend done (`mutual.py`), no frontend
- [ ] Family portal UI — backend done, portal page is minimal

### Tier 4 — Mobile apps (Capacitor)

Capacitor wraps the existing `frontend/` in a native shell — no rewrite needed.
Push notifications via Firebase (already wired). One codebase → iOS + Android.

- [ ] Capacitor project init (`npx cap init`)
- [ ] iOS target — configure bundle ID, signing, Firebase `GoogleService-Info.plist`
- [ ] Android target — configure package name, Firebase `google-services.json`
- [ ] Push notification plugin (`@capacitor/push-notifications`) replacing web push on native
- [ ] Splash screen + app icon assets
- [ ] App Store Connect submission
- [ ] Google Play Console submission

### Tier 5 — Self-hosting polish

- [ ] VAPID key auto-generation on first boot (currently manual)
- [ ] `netcore-start.sh` idempotency — errors if already initialized
- [ ] Docker healthchecks for API + worker (autoheal restarts but check is shallow)
- [ ] One-command install script for self-hosters

### Backlog

- [ ] Audit log UI (backend tracks events, no frontend)
- [ ] Alexa account linking (endpoint exists, no setup guide)
- [ ] i18n — escalation copy is English-only
- [ ] Shareable streak cards (social/viral)
- [ ] Multiple check-in windows (morning + night)

---

## Out of scope

- Live location tracking (privacy + battery)
- In-app messaging between contacts
- Video/voice check-ins
- Calling 911 — non-emergency line only, ever
