# Feature: Email Change Support

## What it does
Allows users to change their email address from the settings page. On change:
1. `email_verified` is reset to `FALSE`
2. A verification email is sent to the NEW address
3. Old address receives no notification (security: don't reveal whether an account exists at a given email)

## User-facing behavior
- User goes to settings, edits email field, saves
- UI shows "A verification email has been sent to [new email]" banner
- User cannot trigger escalation until new email is verified
- If user tries to check in with unverified new email, they see the same "verify your email" prompt as a new signup

## API / data model
- `UserPatch` gets new optional field: `email: str = None`
- `users.email_verified` (already exists) is set to `FALSE` on email change
- `users.email` (already exists) is updated
- JWT token version should be bumped on email change (like password reset) to invalidate old tokens
- New endpoint or reuse existing: `POST /users/resend-verification` already works for current user

## Backend changes (backend/routes/users.py)

### 1. Add `email` to UserPatch
```python
class UserPatch(BaseModel):
    email: str = None  # ADD THIS
    # ... existing fields ...
```

### 2. Modify `update_me()` to handle email change
In the `update_me()` function, after validating the email:
- Check if email is actually changing
- If email is new/changed:
  1. Validate uniqueness (new email must not already be registered)
  2. Validate email format
  3. Set `email_verified = FALSE` 
  4. Bump `token_version` (for security)
  5. Send verification email to the NEW address
  6. Update `email` field in DB

Add `email` to `ALLOWED_COLUMNS`.

### 3. Email uniqueness check
Before updating email, check if another user already has that email:
```python
if "email" in raw and raw["email"] is not None:
    existing = get_user_by_email(db, raw["email"])
    if existing and str(existing["id"]) != str(user["id"]):
        raise HTTPException(status_code=400, detail="Email already in use")
```

### 4. Invalidate old tokens on email change
When email changes, bump token version so old sessions are invalidated:
```python
# After email change, bump token version
db.execute(text("UPDATE users SET token_version = token_version + 1 WHERE id::text = :uid"), {"uid": str(user["id"])})
```

## Email templates (reuse existing)
Use existing `send_verification_email()` from `services/email_svc.py` — same template as new signup verification.

## Frontend changes (frontend/app.js)

### 1. Settings page email field
Find the settings form (look for `PATCH /users/me` or `update_me` patterns) and add an email input field.

### 2. Show pending verification state
After saving with a new email, the `email_verified` status in the user object will be `false`. The frontend should show a banner:
- "Please verify your new email — a verification link was sent to [email]"
- The existing `email_verified` check on check-in already handles blocking unverified users

### 3. Handle 400 error "Email already in use"
Show inline error under the email field: "This email is already registered."

## Acceptance criteria
1. User can change email from settings — `PUT /users/me` with `{email: "new@example.com"}` updates the DB
2. After email change, `email_verified = FALSE` in DB for that user
3. A verification email is sent ONLY to the new address (not the old one)
4. If new email is already in use, API returns 400 with "Email already in use"
5. After email change, old sessions are invalidated (token_version bumped)
6. User cannot pass the email verification gate for check-in escalation until they verify
7. Frontend shows appropriate success/error feedback

## Edge cases
| Scenario | Handling |
|----------|----------|
| User changes to same email | No-op, don't reset verification or bump token version |
| New email fails format validation | Reuse existing email validation in validators.py |
| Resend verification after email change | `POST /resend-verification` already works — sends to current (unverified) email |
| User changes email twice rapidly | Each change resets verification, only the latest email gets a verification email |
