# Feature: Gate Escalation on Email Verification

## What it does
Blocks the check-in reminder and escalation pipeline for users who have not verified their email address. This prevents bogus accounts (e.g., signup typos) from ever triggering scary alerts to real emergency contacts.

## User-facing behavior
- A user who signs up with a typo in their email never receives push/email/SMS check-in reminders and can never trigger escalation to contacts.
- Once they verify their email, the full check-in pipeline activates.
- No changes to UX — this is a silent backend guard.

## API / data model
- `users.email_verified` BOOLEAN NOT NULL DEFAULT FALSE (already exists)
- No new columns or endpoints needed.

## Fix 1: poll_and_fire SQL query
File: `backend/tasks/escalation.py`, function `poll_and_fire()`, lines 42-49

Add `AND email_verified = TRUE` to the WHERE clause:
```python
rows = db.execute(
    text(
        "SELECT * FROM users "
        "WHERE checkin_time = (NOW() AT TIME ZONE COALESCE(timezone, 'UTC'))::time(0) "
        "AND is_dormant = FALSE "
        "AND email_verified = TRUE "
        "AND (has_paid = TRUE OR trial_ends_at > NOW())"
    ),
).mappings().all()
```

## Fix 2: schedule_daily_checkin guard
File: `backend/tasks/escalation.py`, function `schedule_daily_checkin()`, lines 101-107

After fetching the user row, add an early return if `email_verified` is FALSE. Add `email_verified` to the SELECT list and guard:
```python
user = db.execute(
    text("SELECT grace_minutes, confirm_by_minutes, device_token, "
         "notify_push, notify_email, notify_sms, "
         "quiet_hours_start, quiet_hours_end, timezone, token_version, "
         "email_verified "
         "FROM users WHERE id::text = :uid"),
    {"uid": user_id},
).mappings().first()
u = dict(user) if user else {}
if not u.get("email_verified"):
    return  # unverified accounts cannot trigger escalation
```

## Fix 3: Clean dead JS listeners
File: `frontend/app.js`, lines 867-871

Remove the block that attaches Enter-key handlers to `#reg-name`, `#reg-email`, `#reg-phone`, `#reg-password` — these IDs no longer exist (registration was moved to a separate `/signup` page). This removes silent JS exceptions on every page load.

Delete:
```javascript
["reg-name", "reg-email", "reg-phone", "reg-password"].forEach((id) => {
    document.getElementById(id).addEventListener("keydown", (e) => {
        if (e.key === "Enter") document.getElementById("register-btn").click();
    });
});
```

## Acceptance criteria
1. `poll_and_fire` never schedules check-ins for unverified users.
2. `schedule_daily_checkin` exits early if `email_verified = FALSE`.
3. No JavaScript exceptions are thrown on page load due to missing `#reg-*` elements.
4. Existing tests still pass (`pytest` in backend/).
5. No new TODO/FIXME comments introduced.
