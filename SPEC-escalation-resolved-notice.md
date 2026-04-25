# Feature: Escalation Resolved — Notify Contacts of False Alarm

## What it does
When a user checks in after an escalation has been triggered (contacts were already notified),
contacts receive an SMS + email "all clear" message so they know it was a false alarm.

## User-facing behavior
- Contact receives: "✅ [User] checked in — no action needed. They're safe."
- This replaces the current behavior where contacts hear nothing after the scary alert.

## Why this matters
Currently: User misses check-in → contacts get scary "missed check-in" alert → user checks in → contacts never know it was a false alarm. This creates anxiety and erodes trust in the system.

## API / Data model
No new endpoints. Modifies `resolve_escalations()` in `backend/db.py` to also send notifications.

New email template: `contact_all_clear(user_name: str)` → HTML email
New SMS message: "✅ [Name] checked in — no action needed. They're safe."

Escalation event already has `resolved=TRUE, resolved_at=NOW()` set by `resolve_escalations()`.
Contacts are already stored in `emergency_contacts` table with `phone` and `email`.

## Implementation

### Step 1 — Add email template
In `backend/email_templates.py`, add:
```python
def contact_all_clear(user_name: str) -> str:
    """All-clear email sent to contacts when user checks in after escalation."""
    ...
```

### Step 2 — Modify resolve_escalations() in backend/db.py
Current behavior: marks DB resolved, nothing else.
New behavior:
1. Fetch all unresolved escalation events for the user
2. For each escalation event, get the list of contacts who were notified
3. Send SMS + email "all clear" to each contact
4. Keep the DB resolution (already there)

### Step 3 — Celery task (async)
Since we don't want to block the check-in response, the notification sending should be async.
Add a new Celery task `notify_contacts_all_clear.delay(user_id, escalation_event_id)` 
that gets called from `resolve_escalations()`.

### Step 4 — Deduplication
If `notify_contacts_all_clear` is called but contacts were never notified for that escalation 
(e.g., user checked in before escalation fired), send nothing. Check `escalation_events.stage`.

## Acceptance criteria
1. When user checks in after `escalate_to_contacts()` has fired, each contact receives an SMS "✅ [Name] checked in — no action needed."
2. Each contact also receives an email with the all-clear message.
3. If user checks in BEFORE contacts are notified (grace period not over), no all-clear is sent (contacts were never alerted).
4. Check-in itself is not blocked/delayed — notifications are sent async via Celery.
5. The DB `resolved=TRUE` is still set immediately (already working).

## Edge cases
| Scenario | Handling |
|----------|----------|
| User checks in before grace period ends | `resolve_escalations()` called but `escalate_to_contacts()` never fired → stage is NOT `contacts_notified` → skip notification |
| Multiple escalation events for same day | Only notify for events where contacts were actually notified |
| Contact has no phone or email | Skip that channel, send what they have |
| Celery task fails | Log error, do not retry (contacts may miss the all-clear but the primary check-in succeeds) |
| No contacts on file | No-op gracefully |
