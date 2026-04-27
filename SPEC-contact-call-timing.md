# Feature: Contact SMS → Call Sequential Timing

## What it does
When `escalate_to_contacts()` fires, contacts currently receive SMS/email AND phone calls at the same time (synchronous back-to-back loops). This change sequences them: SMS/email first, then phone call after a configurable delay.

## Problem
Contacts get a phone call the same instant they receive an SMS — before they have time to read or act on the SMS. A delayed call is less alarming and more likely to get a response.

## User-facing behavior
- Contact receives SMS: "Hi [Name], [User] missed their check-in. Are they safe? Confirm: [URL]"
- If contact doesn't confirm within `CONTACT_CALL_DELAY_SECONDS`, THEN they receive a phone call
- If contact confirms via SMS reply or the confirm link, the call is never made (handled by existing grace period logic)

## Implementation

### constants.py
Add:
```python
# Delay after SMS before making welfare check call to contacts
CONTACT_CALL_DELAY_SECONDS = 60  # 1 minute
```

### tasks/escalation.py
1. Create a new Celery task `notify_contacts_call`:
```python
@celery_app.task
def notify_contacts_call(user_id: str, escalation_event_id: str):
    """Make welfare check calls to contacts after SMS has been sent."""
    from services.sns_svc import call_contact
    
    db = _db()
    try:
        evt = db.execute(
            text("SELECT resolved, stage FROM escalation_events WHERE id::text = :eid"),
            {"eid": escalation_event_id},
        ).mappings().first()
        if not evt or evt["resolved"]:
            return
        # Don't call if contacts already confirmed majority
        confirmed_row = db.execute(
            text("SELECT COUNT(*) FROM contact_confirmations WHERE escalation_event_id::text = :eid AND confirmed_at IS NOT NULL"),
            {"eid": escalation_event_id},
        ).first()
        confirmed = confirmed_row[0] if confirmed_row else 0
        total_row = db.execute(
            text("SELECT COUNT(*) FROM emergency_contacts WHERE user_id::text = :uid"),
            {"uid": user_id},
        ).first()
        total = total_row[0] if total_row else 0
        majority = math.ceil(total / 2)
        if confirmed >= majority:
            return
        user = db.execute(
            text("SELECT name FROM users WHERE id::text = :uid"),
            {"uid": user_id},
        ).mappings().first()
        u = dict(user) if user else {}
        user_name = u.get("name", "Someone")
        contacts = get_contacts(db, user_id)
        for c in contacts:
            if c.get("phone"):
                call_contact(c["phone"], user_name)
    finally:
        db.close()
```

2. In `escalate_to_contacts()`, remove the direct `call_contact` loop and replace with async scheduling:
   - Remove lines 246-249 (the `for c in contacts: call_contact(...)` loop)
   - After the SMS/email loop (line 245), add:
     ```python
     notify_contacts_call.apply_async(
         args=[user_id, escalation_event_id],
         countdown=CONTACT_CALL_DELAY_SECONDS,
     )
     ```

## Acceptance criteria
1. Contacts receive SMS/email immediately when `escalate_to_contacts()` fires
2. `notify_contacts_call` task fires `CONTACT_CALL_DELAY_SECONDS` later
3. If user checks in before the call fires, `escalate_to_contacts` is resolved and `notify_contacts_call` exits early (it checks `evt["resolved"]`)
4. If contacts reach majority confirmation before call fires, `notify_contacts_call` exits early
5. Existing `call_non_emergency_task` behavior is unaffected
6. All existing tests pass

## Edge cases
- No contacts with phone numbers → `notify_contacts_call` calls nobody (skip gracefully)
- Contact grace timeout already fired before call delay expires → `notify_contacts_call` does nothing (handled by existing resolved/stage checks)
- `escalate_to_contacts` is called multiple times for same event → each schedules its own delayed call (acceptable — call is cheap)
