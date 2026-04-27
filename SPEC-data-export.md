# Feature: GDPR Data Export Endpoint

## What it does
Provides authenticated users a way to download all their personal data in JSON format, per GDPR Article 20 (Right to Data Portability). Returns profile, check-ins, contacts, audit log, groups, and notification settings — but NEVER exports contacts' personal data (phone numbers, emails) belonging to other users.

## User-facing behavior
- Authenticated user calls `GET /users/me/export`
- Receives a JSON object containing all their data organized by category
- No changes to existing UX — this is a privacy compliance feature

## API / data model

### Endpoint
```
GET /users/me/export
Authorization: Bearer <jwt>
```

### Response (200 OK)
```json
{
  "exported_at": "2026-04-27T10:45:00Z",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "...",
    "phone": "+1...",
    "created_at": "...",
    "email_verified": true,
    "has_paid": true,
    "paid_at": "...",
    "timezone": "America/New_York"
  },
  "checkins": [
    {
      "id": "uuid",
      "created_at": "...",
      "note": "...",
      "status": "checked_in",
      "streak": 5
    }
  ],
  "contacts": [
    {
      "id": "uuid",
      "name": "Jane Doe",
      "relationship": "sibling",
      "priority": 1
    }
  ],
  "audit_log": [
    {
      "id": "uuid",
      "event": "checkin",
      "created_at": "...",
      "details": {}
    }
  ],
  "groups": [
    {
      "id": "uuid",
      "name": "Family",
      "type": "family",
      "my_role": "admin"
    }
  ],
  "notification_settings": {
    "notify_push": true,
    "notify_email": true,
    "notify_sms": true,
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "07:00"
  }
}
```

**Excluded (to protect third-party privacy):**
- Contacts' phone numbers and emails
- Device tokens
- JWT token versions
- `password_hash` field (never exported)

## Implementation

### File: `backend/routes/users.py`

Add a new function after the `get_me` function (around line 178):

```python
@router.get("/me/export")
def export_user_data(user=Depends(get_current_user), db=Depends(get_session)):
    """
    GDPR Article 20 — Right to Data Portability.
    Returns all personal data for the authenticated user.
    Excludes third-party personal data (contacts' phone/email) and sensitive fields.
    """
    user_id = str(user["id"])

    # User profile (strip sensitive fields)
    profile = dict(user)
    profile.pop("password_hash", None)
    profile.pop("token_version", None)
    profile.pop("device_token", None)
    # phone is the user's own phone (optional field), include it
    # email is the user's own email, include it
    export_data = {"user": profile}

    # Check-ins
    checkins = db.execute(
        text("""
            SELECT id, created_at, note, status, streak
            FROM checkins
            WHERE user_id = :uid
            ORDER BY created_at DESC
            LIMIT 1000
        """),
        {"uid": user_id}
    ).mappings().all()
    export_data["checkins"] = [dict(r) for r in checkins]

    # Contacts (strip third-party personal data — phone/email withheld)
    contacts = db.execute(
        text("""
            SELECT id, name, relationship, priority
            FROM contacts
            WHERE user_id = :uid
            ORDER BY priority ASC
        """),
        {"uid": user_id}
    ).mappings().all()
    export_data["contacts"] = [dict(r) for r in contacts]

    # Audit log
    audit = db.execute(
        text("""
            SELECT id, event, created_at, details
            FROM audit_log
            WHERE user_id = :uid
            ORDER BY created_at DESC
            LIMIT 500
        """),
        {"uid": user_id}
    ).mappings().all()
    export_data["audit_log"] = [dict(r) for r in audit]

    # Groups (only the user's groups)
    groups = db.execute(
        text("""
            SELECT g.id, g.name, g.type, gm.role as my_role
            FROM groups g
            JOIN group_members gm ON gm.group_id = g.id
            WHERE gm.user_id = :uid
            ORDER BY g.name
        """),
        {"uid": user_id}
    ).mappings().all()
    export_data["groups"] = [dict(r) for r in groups]

    # Notification settings
    export_data["notification_settings"] = {
        "notify_push": user.get("notify_push", True),
        "notify_email": user.get("notify_email", True),
        "notify_sms": user.get("notify_sms", True),
        "quiet_hours_start": user.get("quiet_hours_start"),
        "quiet_hours_end": user.get("quiet_hours_end"),
    }

    export_data["exported_at"] = datetime.now(timezone.utc).isoformat()

    return export_data
```

### Route registration
No changes needed — the `users.router` is already included in `main.py` and the `GET /users/me` pattern is already used. The new `/users/me/export` endpoint fits naturally.

## Acceptance criteria
1. `GET /users/me/export` with valid JWT returns 200 with all data categories
2. `GET /users/me/export` without auth returns 401
3. Contact exports contain only `id, name, relationship, priority` — NO `phone` or `email` fields
4. User export excludes `password_hash`, `token_version`, `device_token`
5. Check-ins limited to 1000 most recent
6. Audit log limited to 500 most recent
7. `exported_at` field in ISO 8601 format with timezone
8. No hardcoded secrets
9. Existing tests still pass

## Edge cases
- User with no checkins: return empty `[]` for checkins
- User with no contacts: return empty `[]` for contacts  
- User with no groups: return empty `[]` for groups
- User with no audit entries: return empty `[]` for audit_log
- Database query errors: return 500 with generic error message (no SQL details leaked)
