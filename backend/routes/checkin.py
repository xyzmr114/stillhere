from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import text

from db import get_session, has_checked_in_today, log_checkin, get_today_checkin
from dependencies import get_current_user
from api_key_auth import get_api_key_user, get_optional_user
from auth import decode_jwt
from limiter import limiter

router = APIRouter(prefix="/checkin", tags=["checkin"])

_EMAIL_STYLE = "body{margin:0;padding:0;background:#0f0f1a;color:#eee;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh}.card{text-align:center;padding:40px 32px;max-width:480px;width:100%;animation:fadeIn .5s ease}@keyframes fadeIn{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}h1{font-size:28px;font-weight:700;margin:0 0 12px}p{font-size:16px;line-height:1.6;margin:0 0 40px;opacity:.8}.brand{font-size:13px;opacity:.4;letter-spacing:1px}"

_EMAIL_SUCCESS_PAGE = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Still Here — Checked In</title><style>{_EMAIL_STYLE}</style></head><body><div class="card"><h1 style="color:#4ecca3">Checked In ✓</h1><p>You're all good. Someone always knows you're here.</p><div class="brand">STILL HERE</div></div></body></html>"""

_EMAIL_ALREADY_PAGE = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Still Here — Already Checked In</title><style>{_EMAIL_STYLE}</style></head><body><div class="card"><h1 style="color:#5bc0de">Already Checked In</h1><p>You've already checked in today. See you tomorrow!</p><div class="brand">STILL HERE</div></div></body></html>"""

_EMAIL_ERROR_PAGE = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Still Here — Link Expired</title><style>{_EMAIL_STYLE}</style></head><body><div class="card"><h1 style="color:#e94560">Link Expired</h1><p>This check-in link has expired or is invalid. Open the app to check in.</p><div class="brand">STILL HERE</div></div></body></html>"""


class CheckinRequest(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None


class NoteRequest(BaseModel):
    note: str


class QuickCheckinRequest(BaseModel):
    token: str


class ActivityTimerRequest(BaseModel):
    hours: float
    label: str


@router.post("")
@limiter.limit("30/minute")
def do_checkin(request: Request, body: CheckinRequest = None, user=Depends(get_optional_user), api_key_user=Depends(get_api_key_user), db=Depends(get_session)):
    effective_user = api_key_user if api_key_user else user
    if not effective_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    uid = str(effective_user["id"])
    row = db.execute(
        text("SELECT checked_in_at FROM checkins WHERE user_id::text = :uid ORDER BY checked_in_at DESC LIMIT 1"),
        {"uid": uid},
    ).fetchone()
    if row and row[0] is not None:
        elapsed = (datetime.now(timezone.utc) - row[0].replace(tzinfo=timezone.utc)).total_seconds()
        if elapsed < 10:
            raise HTTPException(status_code=429, detail="Please wait a moment before checking in again")
    if has_checked_in_today(db, uid):
        return {"status": "already_checked_in", "message": "You're already checked in today!"}
    log_checkin(db, uid)
    from db import log_audit_event
    log_audit_event(db, uid, "checkin", {"method": "api_key" if api_key_user else "app", "lat": body.lat if body else None, "lng": body.lng if body else None})
    if body and body.lat is not None and body.lng is not None:
        db.execute(
            text("UPDATE users SET last_known_lat = :lat, last_known_lng = :lng WHERE id::text = :uid"),
            {"lat": body.lat, "lng": body.lng, "uid": uid},
        )
        db.commit()
    from db import resolve_escalations

    resolve_escalations(db, uid)
    return {"status": "checked_in", "message": "Still Here ✓"}


@router.patch("/note")
def update_note(body: NoteRequest, user=Depends(get_current_user), db=Depends(get_session)):
    from db import update_checkin_note
    uid = str(user["id"])
    if not has_checked_in_today(db, uid):
        raise HTTPException(status_code=400, detail="No check-in to update today")
    update_checkin_note(db, uid, body.note)
    return {"status": "saved"}


@router.get("/email/{token}", response_class=HTMLResponse)
def email_checkin(token: str, db=Depends(get_session)):
    from services.email_svc import decode_checkin_token
    from db import resolve_escalations

    payload = decode_checkin_token(token)
    if not payload:
        return HTMLResponse(_EMAIL_ERROR_PAGE, status_code=400)
    uid = payload.get("sub")
    if not uid:
        return HTMLResponse(_EMAIL_ERROR_PAGE, status_code=400)
    if has_checked_in_today(db, uid):
        return HTMLResponse(_EMAIL_ALREADY_PAGE)
    log_checkin(db, uid, method="email")
    resolve_escalations(db, uid)
    return HTMLResponse(_EMAIL_SUCCESS_PAGE)


@router.get("/status")
def checkin_status(user=Depends(get_current_user), db=Depends(get_session)):
    checked = has_checked_in_today(db, str(user["id"]))
    checkin = get_today_checkin(db, str(user["id"]))
    from db import get_active_escalation

    escalation = get_active_escalation(db, str(user["id"]))
    from db import is_on_vacation
    on_vacation = is_on_vacation(db, str(user["id"]))
    return {
        "checked_in_today": checked,
        "last_checkin": checkin["checked_in_at"] if checkin else None,
        "active_escalation": bool(escalation),
        "on_vacation": on_vacation,
        "last_known_location": {
            "lat": user.get("last_known_lat"),
            "lng": user.get("last_known_lng"),
        } if user.get("last_known_lat") else None,
    }


@router.get("/history")
def checkin_history(user=Depends(get_current_user), db=Depends(get_session)):
    from db import get_checkin_history, get_active_escalation

    events = get_checkin_history(db, str(user["id"]))
    escalation = get_active_escalation(db, str(user["id"]))
    return {"checkins": events, "active_escalation": escalation}


@router.get("/streak")
def checkin_streak(user=Depends(get_current_user), db=Depends(get_session)):
    from db import get_streak

    streak = get_streak(db, str(user["id"]))
    return {"streak": streak}


@router.get("/prompt")
def get_prompt(user=Depends(get_current_user), db=Depends(get_session)):
    from db import get_random_prompt
    prompt = get_random_prompt(db)
    return {"prompt": prompt or "Still here? Time to check in!"}


@router.get("/audit")
def get_audit(user=Depends(get_current_user), db=Depends(get_session)):
    from db import get_audit_log
    events = get_audit_log(db, str(user["id"]))
    return {"events": events}


@router.get("/report")
def annual_report(user=Depends(get_current_user), db=Depends(get_session)):
    from db import get_annual_report
    report = get_annual_report(db, str(user["id"]))
    return report


@router.post("/quick")
@limiter.limit("30/minute")
def quick_checkin(request: Request, body: QuickCheckinRequest = None, db=Depends(get_session)):
    """One-tap check-in from push notification action using quick-checkin token."""
    try:
        payload = decode_jwt(body.token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        token_type = payload.get("type")
        if token_type != "quick_checkin":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token expired or invalid")

    if has_checked_in_today(db, user_id):
        return {"status": "already_checked_in", "message": "You're already checked in today!"}

    log_checkin(db, user_id, method="push_action")
    from db import log_audit_event, resolve_escalations
    log_audit_event(db, user_id, "checkin", {"method": "push_action"})
    resolve_escalations(db, user_id)
    return {"status": "checked_in", "message": "Still Here ✓"}


@router.post("/activity-timer")
def set_activity_timer(
    request: ActivityTimerRequest,
    user=Depends(get_current_user),
    db=Depends(get_session),
):
    """Set an activity-based safety timer (e.g., 'hiking in 4 hours')."""
    if request.hours <= 0:
        raise HTTPException(status_code=400, detail="Hours must be positive")
    if request.hours > 168:
        raise HTTPException(status_code=400, detail="Timer cannot exceed 7 days")
    if len(request.label.strip()) == 0 or len(request.label) > 100:
        raise HTTPException(status_code=400, detail="Label must be 1-100 characters")

    user_id = str(user["id"])
    timer_end = datetime.now(timezone.utc) + timedelta(hours=request.hours)

    db.execute(
        text(
            "UPDATE users SET activity_timer_end = :end, activity_timer_label = :label WHERE id::text = :uid"
        ),
        {"uid": user_id, "end": timer_end, "label": request.label},
    )
    db.commit()

    from db import log_audit_event
    log_audit_event(db, user_id, "activity_timer_start", {
        "hours": request.hours,
        "label": request.label,
    })

    return {
        "status": "timer_set",
        "message": f"Activity timer set: {request.label} in {request.hours} hours",
        "timer_end": timer_end.isoformat(),
    }


@router.delete("/activity-timer")
def cancel_activity_timer(
    user=Depends(get_current_user),
    db=Depends(get_session),
):
    """Cancel an active activity timer."""
    user_id = str(user["id"])

    db.execute(
        text(
            "UPDATE users SET activity_timer_end = NULL, activity_timer_label = NULL WHERE id::text = :uid"
        ),
        {"uid": user_id},
    )
    db.commit()

    from db import log_audit_event
    log_audit_event(db, user_id, "activity_timer_cancel", {})

    return {"status": "timer_cancelled", "message": "Activity timer cancelled"}


@router.get("/activity-timer")
def get_activity_timer(
    user=Depends(get_current_user),
    db=Depends(get_session),
):
    """Get current activity timer status."""
    user_id = str(user["id"])
    row = db.execute(
        text(
            "SELECT activity_timer_end, activity_timer_label FROM users WHERE id::text = :uid"
        ),
        {"uid": user_id},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    r = dict(row)
    timer_end = r.get("activity_timer_end")
    timer_label = r.get("activity_timer_label")

    if not timer_end:
        return {
            "active": False,
            "timer_end": None,
            "timer_label": None,
            "time_remaining_seconds": None,
        }

    now = datetime.now(timezone.utc)
    if timer_end <= now:
        return {
            "active": False,
            "timer_end": timer_end.isoformat() if timer_end else None,
            "timer_label": timer_label,
            "time_remaining_seconds": 0,
        }

    remaining = (timer_end - now).total_seconds()
    return {
        "active": True,
        "timer_end": timer_end.isoformat(),
        "timer_label": timer_label,
        "time_remaining_seconds": remaining,
    }
