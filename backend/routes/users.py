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


@router.post("/register")
@limiter.limit("5/minute")
def register(request: Request, body: RegisterIn, db=Depends(get_session)):
    if not body.accepted_tos:
        raise HTTPException(status_code=400, detail="You must accept the Terms of Service")
    existing = get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    pw_hash = hash_password(body.password)
    result = db.execute(
        text(
            "INSERT INTO users (email, name, password_hash, phone, accepted_tos) VALUES (:email, :name, :pw, :phone, TRUE) RETURNING id"
        ),
        {"email": body.email, "name": body.name, "pw": pw_hash, "phone": body.phone},
    ).first()
    db.commit()
    token = create_jwt(str(result[0]))
    uid = str(result[0])
    try:
        from services.email_svc import send_welcome_email, send_verification_email
        send_welcome_email(body.email, body.name)
        send_verification_email(body.email, body.name, uid)
    except Exception:
        pass
    return {"token": token, "user_id": uid}


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, body: LoginIn, db=Depends(get_session)):
    user = get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_jwt(str(user["id"]))
    return {"token": token, "user_id": str(user["id"])}


@router.post("/device-token")
def register_device_token(body: DeviceTokenIn, user=Depends(get_current_user), db=Depends(get_session)):
    db.execute(
        text("UPDATE users SET device_token = :token WHERE id = :uid"),
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
        text("UPDATE users SET device_token = :token WHERE id = :uid"),
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


@router.patch("/me")
def update_me(body: UserPatch, user=Depends(get_current_user), db=Depends(get_session)):
    raw = body.model_dump(exclude_unset=True)
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
    fields = {k: v for k, v in raw.items() if v is not None or (k in ("vacation_start", "vacation_end") and clearing)}
    if not fields:
        return user
    if fields.get("is_dormant") is False:
        fields["last_device_ping"] = "NOW()"
    sets = ", ".join(f"{k} = :{k}" if k != "last_device_ping" else "last_device_ping = NOW()" for k in fields)
    fields["uid"] = str(user["id"])
    db.execute(text(f"UPDATE users SET {sets} WHERE id = :uid"), fields)
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
    return RedirectResponse("/app?verified=1")


@router.post("/resend-verification")
@limiter.limit("3/minute")
def resend_verification(request: Request, user=Depends(get_current_user)):
    if user.get("email_verified"):
        return {"ok": True, "already_verified": True}
    try:
        from services.email_svc import send_verification_email
        send_verification_email(user["email"], user["name"], str(user["id"]))
    except Exception:
        pass
    return {"ok": True}


@router.delete("/me")
def delete_account(user=Depends(get_current_user), db=Depends(get_session)):
    from db import delete_user_account
    delete_user_account(db, str(user["id"]))
    return {"ok": True}


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
            pass
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
    db.execute(text("UPDATE users SET password_hash = :pw WHERE id = :uid"), {"pw": pw_hash, "uid": uid})
    db.commit()
    return {"message": "Password updated successfully"}


from db import get_user
