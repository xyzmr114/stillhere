# Still Here — Judge Q&A Prep

## The Reframe

Don't pitch it as a death app. Pitch it as a **freedom app**.

> *"Still Here is what lets you live alone without apologizing for it. It's not about dying — it's about the peace of mind that lets you take the solo camping trip, move to a new city, live on your own terms. The safety net is what makes the independence possible."*

The stigma exists because people hear "check-in app" and think "medical alert for grandma." Flip it: this is for people who chose to live alone and want to keep doing it confidently. A smoke detector isn't morbid. A seatbelt isn't morbid. This is infrastructure for modern independent living.

---

## Stats to Know Cold

**The market:**
- 29% of all US households are now single-person — a record high, up from 8% in 1940
- 36M+ Americans live alone (US Census)
- ~1.3 million new solo households added in 2025 alone
- Solo living is now the single most common household type in the US
- Marriage rate dropped from 78.8% (1949) → 47% (2024)

**The problem is real:**
- Nearly 10% of people who die alone aren't discovered for over a month
- Joyce Vincent, London — found in her flat 2 years 9 months after death, TV still on
- Japan's *kodokushi* ("lonely death") phenomenon is spreading West
- 178 people killed by police during wellness checks between 2019–2021

**The audience isn't old:**
- 79% of Gen Z report feeling alone
- 44% of 18–24 year olds live alone or with a partner only
- 80% of Gen Z felt lonely in the past 12 months vs. 45% of boomers

---

## Competitive Landscape

### The Competitor Map

| Product | Target | Core Feature | Problem |
|---|---|---|---|
| **Life360** | Families / parents tracking kids | Real-time GPS location | Requires active sharing, surveillance-forward, $5–10/mo subscription |
| **Noonlight** | Women, personal safety | Panic button → 911 dispatch | Reactive only, no passive monitoring, no escalation chain |
| **bSafe** | Students, lone workers | SOS button + live stream | Reactive, requires you to press something when you're already in danger |
| **Medical alert (Life Alert etc.)** | Elderly | "I've fallen" button | Explicitly AARP-coded, hardware-dependent, $30–60/mo |
| **Apple Check In** | iPhone users | Notifies one person you arrived | iOS only, no grace period, no escalation, no contacts group |
| **Still Here** | Solo adults 20–50 | Daily ritual + full escalation chain | — |

### The One-Line Differentiator

> *"Every competitor assumes you can press a button when something goes wrong. Still Here is built for the scenario where you can't."*

Life360 tracks where you are. Noonlight responds when you panic. Neither handles the scenario where you're unconscious, had a medical episode, or are simply unreachable — and nobody knows yet.

---

## Q&A — Stigma & Pitch

**"This feels morbid. Who actually wants to download an app that's basically planning for their own death?"**

> Nobody buys a smoke detector because they're planning a house fire. Still Here is what lets you *not think about it* — you set it once, it runs quietly, and it only matters on the one day you need it. The users we talked to described it as the thing that finally made them comfortable living alone, not afraid of it.

**"Why not just text a friend every day? Why does this need to be a product?"**

> Because that burden destroys relationships. You either forget, or you feel guilty when you miss, or your friend starts to dread it. Still Here removes the social obligation entirely. Nobody gets a notification unless something is actually wrong. That's the product — making the safety net invisible until it's needed.

---

## Q&A — Product & Safety

**"The emergency services integration seems like a liability nightmare. What happens if you trigger a false wellness check?"**

> Two layers of protection before we ever call anyone. First: your own grace period — configurable, because if you're camping you set it to 10 days. Second: majority of emergency contacts must fail to confirm before we escalate. By the time we place a non-emergency call, a human has already tried to reach you and failed. Rate-limited to once per 72 hours per user. And it's non-emergency line only — never 911.

**"48 hours is not enough to validate safety-critical software. How do you know this actually works?"**

> We ran dry runs through the full escalation chain during the hackathon — every step fires against real infrastructure, real Twilio calls, real emails. It's not a mock. That said, fair point: safety-critical software needs a longer runway for edge case testing, and that's the roadmap. What we built is a working proof of concept with a real architecture, not a prototype that needs to be rewritten.

---

## Q&A — Tech Stack

**"Why FastAPI over Django or Node?"**

> FastAPI is async-native and gives us Pydantic validation for free. For a real-time escalation engine where timing matters — we're matching check-in windows to the minute — async I/O over Django's sync model was the right call. It's also lighter, which matters for a VPS deployment.

**"Why Celery Beat instead of a proper cron or APScheduler?"**

> Celery Beat gives us a distributed task queue and a scheduler in one. The polling approach — one task every 60 seconds matching `checkin_time = NOW()` — means we never need per-user scheduled tasks. No database-backed dynamic scheduler, no cron proliferation. It scales horizontally just by adding workers.

**"Why raw SQL instead of an ORM?"**

> We're doing a lot of multi-table queries with conditional logic in the escalation engine — majority-confirmation checks, dormancy detection, streak calculations. SQLAlchemy ORM generates ugly, slow queries for that. Raw SQL via `text()` keeps it readable and lets us optimize precisely. The tradeoff is no auto-migrations, but Supabase handles the schema.

**"Why a PWA instead of a native app?"**

> Push notifications, home screen install, offline caching — we get all of it without the App Store review cycle. For a hackathon especially, shipping on web means judges can open it on any device right now. Long-term, a native wrapper is on the roadmap, but the core experience doesn't need it.

---

## Q&A — Business Model

**"How do you monetize this without it being predatory?"**

> One-time purchase. A subscription to an app called Still Here would be genuinely evil — if you miss a payment your safety net disappears? No. Every competitor does this. It's one of the reasons we built it.

**"What's your moat? Apple or Google could build this into the OS."**

> They could, and Apple sort of has — iPhone's Check In feature. But it's buried, iOS-only, and has no escalation chain beyond texting one person. No contacts group, no grace period logic, no non-emergency fallback, no passive sensor integration, no family portal. The moat is the escalation engine and cross-platform reach. A 25-year-old with an Android who moved to Chicago alone isn't served by any of this today.

---

## Q&A — Social Good (Best Social Good / Bloomberg Philanthropies)

**"What's the social good case here?"**

> 29% of US households are now single-person — the fastest-growing household type in the country. That's not a niche, that's a structural shift in how Americans live. The existing safety infrastructure wasn't designed for it. Medical alert systems target the elderly. Family tracking apps assume you have a family tracking you. Still Here is the first product designed specifically for the person who chose independence and shouldn't have to trade safety for it.

**"How does this reach underserved communities?"**

> One-time purchase, no subscription, PWA so no app store required, works on any device with a browser. The biggest gap in safety tech is that it's priced as a luxury — $30–60/month for a medical alert, $10/month for Life360. We deliberately priced ourselves out of that model. The person most at risk from dying alone undiscovered isn't wealthy.

**"Is this scalable as a social good, or is it just a product?"**

> Both. The product funds the infrastructure. Long-term, the non-emergency wellness check integration is the piece with real public health implications — routing structured, pre-qualified wellness check requests instead of ad-hoc 911 calls reduces police response burden and the associated risks. 178 people were killed during wellness checks between 2019–2021. A better-designed escalation chain that reaches non-emergency services first is genuinely safer for everyone.

---

## Q&A — The "Why You" Question

**"Why are you the right team to build this?"**

> Because we asked the question personally and didn't have an answer. The inspiration is real — my roommate asked me how long before anyone would notice, and I couldn't answer. That's not a market research finding, that's a lived experience. We're the demographic: young, living alone or close to it, not served by anything that exists. We built what we'd actually use.
