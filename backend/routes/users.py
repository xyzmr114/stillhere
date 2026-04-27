import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy import text

from auth import create_jwt, hash_password, verify_password
from config import settings
from dependencies import get_current_user
from db import get_session, get_user_by_email
from limiter import limiter
from validators import validate_phone, validate_timezone, validate_checkin_time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


class RegisterIn(BaseModel):
    email: EmailStr
    name: str
    password: str
    phone: str = None
    accepted_tos: bool = False


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class DeviceTokenIn(BaseModel):
    token: str


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str


def _generate_reset_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "reset",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _decode_reset_token(token: str):
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        if payload.get("type") != "reset":
            return None
        return payload
    except JWTError:
        return None


class UserPatch(BaseModel):
    email: EmailStr = None
    name: str = None
    phone: str = None
    checkin_time: str = None
    grace_minutes: int = None
    retry_count: int = None
    retry_interval_hours: int = None
    device_token: str = None
    snooze_until: str = None
    confirm_by_minutes: int = None
    streak_reminder_hours: int = None
    vacation_start: Optional[str] = None
    vacation_end: Optional[str] = None
    is_dormant: bool = None
    accepted_tos: bool = None
    address: str = None
    city: str = None
    state: str = None
    zip_code: str = None
    timezone: str = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    notify_push: bool = None
    notify_email: bool = None
    notify_sms: bool = None
    notify_weekly_digest: bool = None


@router.post("/register")
@limiter.limit("5/minute")
def register(request: Request, body: RegisterIn, db=Depends(get_session)):
    if not body.accepted_tos:
        raise HTTPException(status_code=400, detail="You must accept the Terms of Service")
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if body.phone:
        valid_phone = validate_phone(body.phone)
        if not valid_phone:
            raise HTTPException(status_code=400, detail="Invalid phone number")
    existing = get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    pw_hash = hash_password(body.password)
    result = db.execute(
        text(
            "INSERT INTO users (email, name, password_hash, phone, accepted_tos, trial_ends_at) "
            "VALUES (:email, :name, :pw, :phone, TRUE, NOW() + INTERVAL '7 days') RETURNING id"
        ),
        {"email": body.email, "name": body.name, "pw": pw_hash, "phone": body.phone},
    ).first()
    db.commit()
    uid = str(result[0])
    token = create_jwt(uid, token_version=1)
    try:
        from services.email_svc import send_welcome_email, send_verification_email
        send_welcome_email(body.email, body.name)
        send_verification_email(body.email, body.name, uid)
    except Exception:
        logger.exception("Failed to send welcome/verification emails during registration for user %s", uid)
    return {"token": token, "user_id": uid}


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, body: LoginIn, db=Depends(get_session)):
    user = get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_jwt(str(user["id"]), token_version=user.get("token_version", 1))
    return {"token": token, "user_id": str(user["id"])}


@router.post("/device-token")
def register_device_token(body: DeviceTokenIn, user=Depends(get_current_user), db=Depends(get_session)):
    db.execute(
        text("UPDATE users SET device_token = :token WHERE id::text = :uid"),
        {"token": body.token, "uid": str(user["id"])},
    )
    db.commit()
    return {"ok": True}


class WebPushSubscribeIn(BaseModel):
    subscription: dict


@router.post("/web-push-subscribe")
def register_web_push(body: WebPushSubscribeIn, user=Depends(get_current_user), db=Depends(get_session)):
    import json
    db.execute(
        text("UPDATE users SET device_token = :token WHERE id::text = :uid"),
        {"token": json.dumps(body.subscription), "uid": str(user["id"])},
    )
    db.commit()
    return {"ok": True}


@router.get("/vapid-public-key")
def get_vapid_public_key():
    from config import settings
    return {"publicKey": settings.webpush_vapid_public_key}


@router.get("/me")
def get_me(user=Depends(get_current_user)):
    user.pop("password_hash", None)
    return user


@router.get("/me/export")
def export_user_data(user=Depends(get_current_user), db=Depends(get_session)):
    user_id = str(user["id"])
    try:
        profile = dict(user)
        profile.pop("password_hash", None)
        profile.pop("token_version", None)
        profile.pop("device_token", None)

        checkins = db.execute(
            text(
                "SELECT id, created_at, note, status, streak "
                "FROM checkins WHERE user_id = :uid "
                "ORDER BY created_at DESC LIMIT 1000"
            ),
            {"uid": user_id},
        ).mappings().all()

        contacts = db.execute(
            text(
                "SELECT id, name, relationship, priority "
                "FROM contacts WHERE user_id = :uid "
                "ORDER BY priority ASC"
            ),
            {"uid": user_id},
        ).mappings().all()

        audit = db.execute(
            text(
                "SELECT id, event, created_at, details "
                "FROM audit_log WHERE user_id = :uid "
                "ORDER BY created_at DESC LIMIT 500"
            ),
            {"uid": user_id},
        ).mappings().all()

        groups = db.execute(
            text(
                "SELECT g.id, g.name, g.type, gm.role as my_role "
                "FROM groups g "
                "JOIN group_members gm ON gm.group_id = g.id "
                "WHERE gm.user_id = :uid "
                "ORDER BY g.name"
            ),
            {"uid": user_id},
        ).mappings().all()

        export_data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "user": profile,
            "checkins": [dict(r) for r in checkins],
            "contacts": [dict(r) for r in contacts],
            "audit_log": [dict(r) for r in audit],
            "groups": [dict(r) for r in groups],
            "notification_settings": {
                "notify_push": user.get("notify_push") if user.get("notify_push") is not None else True,
                "notify_email": user.get("notify_email") if user.get("notify_email") is not None else True,
                "notify_sms": user.get("notify_sms") if user.get("notify_sms") is not None else True,
                "quiet_hours_start": user.get("quiet_hours_start"),
                "quiet_hours_end": user.get("quiet_hours_end"),
            },
        }
        return export_data
    except Exception:
        logger.exception("Failed to export data for user %s", user_id)
        raise HTTPException(status_code=500, detail="Failed to export data")


@router.patch("/me")
def update_me(body: UserPatch, user=Depends(get_current_user), db=Depends(get_session)):
    raw = body.model_dump(exclude_unset=True)

    # Validate timezone if provided
    if "timezone" in raw and raw["timezone"] is not None:
        valid_tz = validate_timezone(raw["timezone"])
        if not valid_tz:
            raise HTTPException(status_code=400, detail="Invalid timezone")
        raw["timezone"] = valid_tz

    # Validate checkin_time if provided
    if "checkin_time" in raw and raw["checkin_time"] is not None:
        valid_time = validate_checkin_time(raw["checkin_time"])
        if not valid_time:
            raise HTTPException(status_code=400, detail="Invalid check-in time. Format: HH:MM (24-hour)")
        raw["checkin_time"] = valid_time

    # Validate phone if provided
    if "phone" in raw and raw["phone"] is not None:
        valid_phone = validate_phone(raw["phone"])
        if not valid_phone:
            raise HTTPException(status_code=400, detail="Invalid phone number")
        raw["phone"] = valid_phone

    # Handle email change
    if "email" in raw and raw["email"] is not None:
        if raw["email"] != user.get("email"):
            # Check uniqueness
            existing = get_user_by_email(db, raw["email"])
            if existing and str(existing["id"]) != str(user["id"]):
                raise HTTPException(status_code=400, detail="Email already in use")
            # Will send verification email and bump token_version after update

    # Validate quiet hours: both or neither
    qh_start = raw.get("quiet_hours_start")
    qh_end = raw.get("quiet_hours_end")
    if (qh_start is not None) != (qh_end is not None):
        # Allow clearing both
        if not (qh_start is None and qh_end is None):
            raise HTTPException(status_code=400, detail="Both quiet_hours_start and quiet_hours_end are required")

    has_start = "vacation_start" in raw and raw["vacation_start"] is not None
    has_end = "vacation_end" in raw and raw["vacation_end"] is not None
    has_start_null = "vacation_start" in raw and raw["vacation_start"] is None
    has_end_null = "vacation_end" in raw and raw["vacation_end"] is None
    clearing = has_start_null and has_end_null
    if has_start and not has_end:
        raise HTTPException(status_code=400, detail="Both vacation_start and vacation_end are required")
    if has_end and not has_start:
        raise HTTPException(status_code=400, detail="Both vacation_start and vacation_end are required")
    if has_start_null and not has_end_null:
        raise HTTPException(status_code=400, detail="Both vacation_start and vacation_end are required")
    if has_end_null and not has_start_null:
        raise HTTPException(status_code=400, detail="Both vacation_start and vacation_end are required")
    if has_start and has_end:
        from datetime import datetime
        try:
            start = datetime.fromisoformat(raw["vacation_start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(raw["vacation_end"].replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            raise HTTPException(status_code=400, detail="Invalid date format for vacation dates")
        if end <= start:
            raise HTTPException(status_code=400, detail="vacation_end must be after vacation_start")
    accept_tos = raw.pop("accepted_tos", None)
    fields = {k: v for k, v in raw.items() if v is not None or (k in ("vacation_start", "vacation_end") and clearing)}
    if accept_tos is True:
        fields["_accept_tos"] = True
    if not fields:
        return user
    if fields.get("is_dormant") is False:
        fields["last_device_ping"] = "NOW()"
    ALLOWED_COLUMNS = {
        "name", "phone", "email", "checkin_time", "grace_minutes", "retry_count",
        "retry_interval_hours", "device_token", "snooze_until",
        "confirm_by_minutes", "streak_reminder_hours", "vacation_start",
        "vacation_end", "is_dormant", "contact_grace_hours",
        "address", "city", "state", "zip_code", "timezone",
        "quiet_hours_start", "quiet_hours_end",
        "notify_push", "notify_email", "notify_sms", "notify_weekly_digest",
    }
    set_parts = []
    for k in fields:
        if k == "last_device_ping":
            set_parts.append("last_device_ping = NOW()")
        elif k == "_accept_tos":
            set_parts.append("accepted_tos = TRUE")
        elif k in ALLOWED_COLUMNS:
            set_parts.append(f"{k} = :{k}")
        else:
            continue
    sets = ", ".join(set_parts)
    clean_fields = {k: v for k, v in fields.items() if k != "_accept_tos"}
    clean_fields["uid"] = str(user["id"])
    db.execute(text(f"UPDATE users SET {sets} WHERE id::text = :uid"), clean_fields)

    # Handle email change side-effects: bump token, reset verified, send verification
    email_changed = "email" in raw and raw["email"] is not None and raw["email"] != user.get("email")
    if email_changed:
        db.execute(text("UPDATE users SET token_version = token_version + 1, email_verified = FALSE WHERE id::text = :uid"), {"uid": str(user["id"])})
        try:
            from services.email_svc import send_verification_email
            send_verification_email(raw["email"], user["name"], str(user["id"]))
        except Exception:
            logger.exception("Failed to send verification email for user %s after email change", str(user["id"]))

    db.commit()
    from db import get_user

    updated = get_user(db, str(user["id"]))
    updated.pop("password_hash", None)
    return updated


@router.get("/verify-email")
def verify_email(token: str, db=Depends(get_session)):
    from services.email_svc import decode_verification_token
    payload = decode_verification_token(token)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")
    uid = payload.get("sub")
    db.execute(text("UPDATE users SET email_verified = TRUE WHERE id::text = :uid"), {"uid": uid})
    db.commit()
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/signin?verified=1")


@router.post("/resend-verification")
@limiter.limit("3/minute")
def resend_verification(request: Request, user=Depends(get_current_user)):
    if user.get("email_verified"):
        return {"ok": True, "already_verified": True}
    try:
        from services.email_svc import send_verification_email
        send_verification_email(user["email"], user["name"], str(user["id"]))
    except Exception:
        logger.exception("Failed to send verification email for user %s", str(user["id"]))
    return {"ok": True}


@router.delete("/me")
def delete_account(user=Depends(get_current_user), db=Depends(get_session)):
    from db import delete_user_account
    delete_user_account(db, str(user["id"]))
    return {"ok": True}


@router.post("/me/delete/request")
@limiter.limit("3/minute")
def request_account_deletion(request: Request, user=Depends(get_current_user), db=Depends(get_session)):
    """Request a deletion confirmation email. Invalidates any previous pending token."""
    import uuid
    from datetime import timedelta
    from constants import DELETION_TOKEN_EXPIRATION_HOURS
    from db import create_deletion_token

    uid = str(user["id"])
    token = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(hours=DELETION_TOKEN_EXPIRATION_HOURS)

    create_deletion_token(db, uid, token, expires_at)

    try:
        from services.email_svc import send_deletion_confirmation_email
        deletion_url = f"{settings.base_url}/users/me/delete/confirm/{token}"
        send_deletion_confirmation_email(user["email"], user["name"], deletion_url)
    except Exception:
        logger.exception("Failed to send deletion confirmation email for user %s", uid)

    return {"message": "Confirmation email sent"}


@router.get("/me/delete/confirm/{token}")
def confirm_account_deletion(token: str, db=Depends(get_session)):
    """Validate token and delete account, notifying emergency contacts."""
    from db import get_deletion_token, mark_deletion_token_used, delete_user_account, get_contacts

    record = get_deletion_token(db, token)
    if not record:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content="<html><body><h1>Link expired or invalid</h1><p>This deletion link is invalid or has already been used.</p></body></html>",
            status_code=400,
        )

    # Check expiry
    if datetime.now(timezone.utc) > record["expires_at"]:
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content="<html><body><h1>Link expired or invalid</h1><p>This deletion link has expired. Please request a new one from your account settings.</p></body></html>",
            status_code=400,
        )

    # Check already-used
    if record.get("used_at"):
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            content="<html><body><h1>Account already deleted</h1><p>This link has already been used. Your account was deleted.</p></body></html>",
            status_code=400,
        )

    user_id = str(record["user_id"])

    # Fetch user info before deletion for contact notifications
    from db import get_user
    user = get_user(db, user_id)
    user_name = user["name"] if user else "A former user"

    # Mark token used FIRST to prevent double-deletion
    mark_deletion_token_used(db, token)

    # Notify contacts BEFORE deleting the user
    contacts = get_contacts(db, user_id)
    _notify_contacts_user_left(db, user_id, user_name, contacts)

    # Now delete the account
    delete_user_account(db, user_id)

    from fastapi.responses import HTMLResponse
    return HTMLResponse(
        content="<html><body><h1>Your account has been deleted.</h1><p>We're sorry to see you go. If you wish to rejoin, you may create a new account at any time.</p></body></html>",
        status_code=200,
    )


def _notify_contacts_user_left(db, user_id: str, user_name: str, contacts: list):
    """Send SMS and email to each emergency contact notifying them the user left."""
    if not contacts:
        return
    try:
        from services.sns_svc import send_sms
        from services.email_svc import send_user_left_notification_email
        for contact in contacts:
            contact_name = contact.get("name", "Your contact")
            msg = f"Hi {contact_name}, {user_name} has deleted their Still Here account. You're no longer their emergency contact."
            if contact.get("phone"):
                try:
                    send_sms(contact["phone"], msg)
                except Exception:
                    logger.exception("Failed to send SMS to contact %s", contact["id"])
            if contact.get("email"):
                try:
                    send_user_left_notification_email(contact["email"], contact_name, user_name)
                except Exception:
                    logger.exception("Failed to send email to contact %s", contact["id"])
    except Exception:
        logger.exception("Failed to notify contacts for user %s during deletion", user_id)


@router.post("/forgot-password")
@limiter.limit("3/minute")
def forgot_password(request: Request, body: ForgotPasswordIn, db=Depends(get_session)):
    user = get_user_by_email(db, body.email)
    if user:
        token = _generate_reset_token(str(user["id"]))
        try:
            from services.email_svc import send_password_reset_email
            send_password_reset_email(body.email, user["name"], token)
        except Exception:
            logger.exception("Failed to send password reset email for user %s", str(user["id"]))
    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(body: ResetPasswordIn, db=Depends(get_session)):
    payload = _decode_reset_token(body.token)
    if not payload:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    uid = payload.get("sub")
    if not uid:
        raise HTTPException(status_code=400, detail="Invalid token")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    pw_hash = hash_password(body.new_password)
    db.execute(
        text("UPDATE users SET password_hash = :pw, token_version = token_version + 1 WHERE id::text = :uid"),
        {"pw": pw_hash, "uid": uid},
    )
    db.commit()
    return {"message": "Password updated successfully"}


@router.post("/logout")
def logout(user=Depends(get_current_user), db=Depends(get_session)):
    """Invalidate all existing tokens by bumping token_version."""
    db.execute(
        text("UPDATE users SET token_version = token_version + 1 WHERE id::text = :uid"),
        {"uid": str(user["id"])},
    )
    db.commit()
    return {"ok": True}


from db import get_user
