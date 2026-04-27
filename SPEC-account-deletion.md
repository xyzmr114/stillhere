# Feature: Account Deletion Confirmation + Contact Notification

## What it does (1 paragraph)
When a user requests account deletion, they receive a confirmation email with a time-limited token. Clicking the link in the email completes deletion, notifies their emergency contacts that they've left the platform, and sends a final confirmation to the user's email (ifsmtp is configured). This prevents accidental deletions and ensures contacts aren't left wondering why a user disappeared.

## User-facing behavior
1. User clicks "Delete Account" in settings
2. A confirmation modal asks "Are you sure? This will send a confirmation email."
3. User clicks "Send confirmation email"
4. Backend sends email with a 1-hour expiry deletion link
5. User clicks the link in email
6. Account is deleted, contacts receive "user left Still Here" notification
7. Browser redirects to landing page with "Account deleted" message

## API / data model
### New endpoint: POST /users/me/delete/request
- Creates a `deletion_tokens` table entry with UUID token + 1h expiry
- Sends confirmation email to user's registered email
- Returns `{"message": "Confirmation email sent"}`

### New endpoint: GET /users/me/delete/confirm/{token}
- Validates token from email (checks expiry + not used)
- Deletes user account + all data
- **For each emergency contact:** sends SMS + email notification that user left Still Here
- Returns HTML page: "Your account has been deleted. We're sorry to see you go."
- Invalid/expired token: HTML page "Link expired or invalid"

### Database changes
- New table `deletion_tokens(id, user_id, token, created_at, expires_at, used_at)`

### Email templates
- **Confirmation email:** "Confirm Account Deletion — click within 1 hour"
- **Contact notification SMS:** "Hi {contact_name}, {user_name} has deleted their Still Here account. You're no longer their emergency contact."
- **Contact notification email:** HTML email with same content

## Acceptance criteria
1. POST /users/me/delete/request requires authentication → sends email with unique token
2. Token expires after 1 hour
3. Token can only be used once (idempotent — re-use shows "already deleted")
4. On successful deletion via token: user's row deleted from users table
5. On successful deletion: all emergency contacts receive SMS + email notification
6. Invalid/expired token → friendly HTML error page
7. Deleted user's contacts see the user removed from their portal

## Edge cases
- User has no email → still allow deletion (skip confirmation email step)
- SMTP fails → log error, don't block deletion (deletion still proceeds)
- User has no emergency contacts → skip contact notification step
- Contact has no phone → skip SMS, only send email
- Token requested twice before clicking → previous token invalidated, new token issued
