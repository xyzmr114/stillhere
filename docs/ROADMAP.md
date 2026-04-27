# Still Here — Roadmap

> 7-day free trial, then $5 lifetime. No subscriptions. Non-emergency line only, only as absolute last resort.

## Stack
Backend: FastAPI + Celery + Supabase + Redis
Frontend: Vanilla JS PWA
Deploy: Docker Compose (5 services)
Mobile: Capacitor (iOS + Android — wraps existing frontend, no rewrite)

---

## Completed

### Core — Phases 1-5
- [x] Full escalation chain (push, email, SMS, voice welfare check)
- [x] Contact voting / confirmation
- [x] Vacation mode with date range
- [x] Streaks with history display
- [x] Mutual check-ins (backend + frontend)
- [x] Groups
- [x] Family portal (backend + portal.html)
- [x] API keys for automation
- [x] Home Assistant / Alexa webhook endpoints
- [x] Stripe checkout (test mode)
- [x] Web Push (VAPID self-hosting) + SMTP support
- [x] Netcore P2P access

### Tier 1 — Pre-launch
- [x] Rate limiting on login/register + all sensitive endpoints
- [x] Email verification on signup
- [x] Delete account (GDPR)
- [x] Contact confirm web screen
- [x] TOS gate on registration

### Tier 2 — Core UX
- [x] Snooze / vacation UI with timezone-aware status
- [x] Check-in history + streak display (DB + frontend)
- [x] Onboarding flow (6-step wizard: why it matters, check-in time, contact, address, push, done)
- [x] Push permission prompt with denied/default fallback messaging
- [x] Activity timers ("hiking in 4 hours")
- [x] Dead letters (messages delivered after extended inactivity)

### Tier 3 — Growth & Trust
- [x] Privacy policy + Terms of service pages
- [x] Landing page with waitlist + contact form
- [x] Mutual check-in UI (frontend wired to mutual.py)
- [x] Family portal UI (portal.html with check-in status, escalation history)
- [x] Audit log UI (history tab shows events)
- [x] Interactive demo (demo.html)

### Security hardening (April 2026)
- [x] Supabase RLS enabled on all 23 tables, anon/authenticated grants revoked
- [x] JWT startup guard — refuses to start without JWT_SECRET
- [x] password_hash stripped from get_user() at the data layer
- [x] SQL injection prevention — column whitelists on dynamic UPDATE queries
- [x] CORS tightened to explicit methods/headers
- [x] Rate limiting on checkin, contacts, safety lookup, stripe endpoints
- [x] JWT token versioning — revocation on password reset + logout
- [x] Stripe payment audit trail (session ID, customer email, paid_at)
- [x] Notification preferences (quiet hours, push/email/SMS/digest toggles)
- [x] Contact priority ordering with drag-and-drop reorder

### Payment & trial (April 2026)
- [x] 7-day free trial on signup (trial_ends_at, no card required)
- [x] Trial banner in-app (green → urgent red at 2 days)
- [x] Paywall after trial expiry (escalation stops, app locks)
- [x] Trial expiring + expired email notifications (Celery beat daily)
- [x] Payment confirmation email from Stripe webhook
- [x] Polished welcome email with numbered setup steps
- [x] `/app` → `/signin` rename with 301 redirect for backwards compat

### Signup & compliance (April 2026)
- [x] Public signup page (`/signup`) with Twilio-compliant SMS consent
- [x] Phone number optional — SMS consent block only shows when phone entered
- [x] US-only phone field with 🇺🇸 +1 prefix and auto-formatting
- [x] Registration removed from SPA, consolidated to `/signup`
- [x] Landing page CTAs updated to "Start Free Trial"
- [x] Auth screen redesigned (brand header, gradient glow, footer)

### Mobile — Capacitor
- [x] Capacitor project init (mobile/ directory with config + package.json)
- [x] Config for iOS + Android targets

---

## What's Next

### Critical — blocks launch
- [x] Stripe webhook must reject unsigned payloads — if `STRIPE_WEBHOOK_SECRET` is empty, anyone can fake a payment. Require signature verification unconditionally in production
- [x] Gate escalation on `email_verified = TRUE` — typo at signup causes real contacts to be notified for a bogus account
- [x] Twilio inbound STOP webhook — no route handles opt-out replies. DB keeps `notify_sms = true`, sends keep firing. Compliance blocker (POST /webhooks/twilio/sms with HMAC-SHA1 signature validation, handles STOP/START keywords, updates users.notify_sms)
- [x] Clean dead JS listeners — `app.js` still attaches handlers to `#reg-name`, `#reg-email` etc. from removed register form. Silent exceptions on every page load

### High — before launch
- [x] Escalation resolved notice to contacts — contact gets scary "missed check-in" alert, user checks in, contact never hears back ✅
- [x] `/signin?verified=1` shows no feedback — email verification redirect lands silently ✅
- [x] Email change support — no `email` field in `UserPatch`, users can't update their email
- [x] Account deletion confirmation email + notice to contacts — POST /users/me/delete/request sends 1h expiry token email; GET /users/me/delete/confirm/{token} validates, deletes account, notifies contacts via SMS+email
- [x] Contact SMS + voice call timing — contacts SMS/email fire immediately, voice call fires 60s later via notify_contacts_call Celery task
- [ ] Stripe go-live — `sk_test_` to `sk_live_`, wire webhook in Stripe dashboard

### Twilio TFV — resubmit (April 2026)
- [ ] TFV rejected: business name mismatch with official records
- [ ] Fix: ensure TFV form business name exactly matches "Sahaj Tech LLC" as shown on stillherehq.com, /terms, /privacy, /consent
- [ ] Use case: Account Notifications (daily check-in reminders + emergency contact alerts)
- [ ] Consent page at stillherehq.com/consent already meets requirements
- [ ] Signup form at stillherehq.com/signup already mirrors Twilio's reference opt-in form
- [ ] After fixing business name on TFV form, resubmit

### Medium — should fix
- [x] No "escalation cancelled" notice to contacts on false alarm — contacts receive all-clear SMS + email via notify_contacts_all_clear when user checks in after escalation
- [x] Privacy policy says 30-day deletion delay, code deletes immediately — reconcile — updated privacy.html to say deletion is immediate upon confirmation link click
- [x] Weekly digest sends to expired trial users (add `has_paid OR trial_ends_at > NOW()` filter)
- [ ] No notice to contacts when removed from someone's network
- [ ] Onboarding overlay race condition with contact card loading
- [ ] Non-emergency numbers database — seed/expand beyond initial set

### Short-term
- [ ] iOS app submission (App Store Connect, bundle ID, signing, splash/icon assets)
- [ ] Android app submission (Google Play Console, google-services.json)
- [ ] Push notification plugin for native (`@capacitor/push-notifications`)
- [ ] Data export endpoint (`/users/me/export`) for GDPR
- [ ] Payment polling fallback if webhook is slow (support link instead of infinite reload)

### Self-hosting polish
- [ ] VAPID key auto-generation on first boot (currently manual)
- [ ] `netcore-start.sh` idempotency — errors if already initialized
- [ ] One-command install script for self-hosters

### Backlog
- [ ] Shareable streak cards (social/viral sharing)
- [ ] Multiple check-in windows (morning + night)
- [ ] Alexa account linking setup guide (endpoint exists)
- [ ] i18n — escalation copy is English-only
- [ ] Location-aware non-emergency lookup (auto-detect city from GPS)
- [ ] Caregiver dashboard — aggregate view for people monitoring multiple users

---

## Out of scope

- Live location tracking (privacy + battery)
- In-app messaging between contacts
- Video/voice check-ins
- Calling 911 — non-emergency line only, ever
