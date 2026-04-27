# Feature: Notify contacts when removed from a user's network

## What it does (1 paragraph)
When a user removes an emergency contact via the DELETE /contacts/{contact_id} endpoint, the platform sends the contact an email and SMS notification letting them know they've been removed from that user's safety network. This closes the trust gap where contacts silently disappear without explanation.

## User-facing behavior
- Contact receives email: "You've been removed from {user_name}'s Still Here network"
- Contact receives SMS: "You've been removed from {user_name}'s Still Here safety network. You'll no longer receive check-in alerts for them."
- Notification is sent asynchronously (Celery task) to avoid blocking the API response
- Failures in notification delivery are logged but do not fail the deletion itself

## API / data model
- `DELETE /contacts/{contact_id}` — existing endpoint modified
- New Celery task: `tasks.notifications.contact_removed(user_id, contact_name, contact_email, contact_phone)`
- New email template: `contact_removed_notification` in `email_templates.py`
- New SMS template: hardcoded in `sns_svc.py` or task

## Acceptance criteria
1. `DELETE /contacts/{contact_id}` returns 200 even if notification fails (deletion always succeeds)
2. Celery task `contact_removed` is called with contact details before deletion
3. Email is sent to contact's email if provided (using `send_contact_removed_email`)
4. SMS is sent to contact's phone if provided (using `sns_svc.send_sms`)
5. Task logs errors without raising (fire-and-forget with logging)
6. Unit test covers: notification called before deletion, email branch, SMS branch, graceful failure
7. Integration test: full delete flow with mock email/SMS

## Edge cases
- Contact has no email and no phone → skip both, still delete
- Email send fails → log exception, do not block deletion
- SMS send fails → log exception, do not block deletion
- User is not the owner of the contact → 403 from existing auth (no change)
- Contact already deleted (race) → no-op, return 200
