import os
import uuid
from datetime import date, datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text

from config import settings
from db import get_session, SessionLocal, log_escalation_event, get_contacts, log_audit_event, log_checkin
from services.sns_svc import send_sms
from dependencies import get_current_user

router = APIRouter(prefix="/api/demo", tags=["demo"])

DEMO_EMAILS = ["demo1@stillhere.hack", "demo2@stillhere.hack"]
DEMO_DISPLAY = {
    "demo1@stillhere.hack": "Alice (Demo)",
    "demo2@stillhere.hack": "Bob (Demo)",
}


def seed_demo(db, phone1: str = None, phone2: str = None):
    phone1 = phone1 or os.getenv("DEMO_PHONE_1", "+15551234567")
    phone2 = phone2 or os.getenv("DEMO_PHONE_2", "+15559876543")

    now = datetime.now(timezone.utc)
    pw_hash = bcrypt.hashpw("demo1234".encode(), bcrypt.gensalt()).decode()

    users_cfg = [
        ("demo1@stillhere.hack", "Alice (Demo)", phone1, 60, 1),
        ("demo2@stillhere.hack", "Bob (Demo)", phone2, 1, 2),
    ]
    user_ids = {}
    for email, name, phone, grace, offset in users_cfg:
        ct = (now + timedelta(minutes=offset)).replace(second=0, microsecond=0).time()
        existing = db.execute(
            text("SELECT id FROM users WHERE email = :e"), {"e": email}
        ).mappings().first()
        if existing:
            user_ids[email] = existing["id"]
            db.execute(
                text("UPDATE users SET phone=:phone, grace_minutes=:grace, checkin_time=:ct WHERE id=:uid"),
                {"phone": phone, "grace": grace, "ct": ct, "uid": existing["id"]},
            )
            db.commit()
            continue
        result = db.execute(
            text(
                "INSERT INTO users (email, name, phone, password_hash, checkin_time, grace_minutes) "
                "VALUES (:email, :name, :phone, :hash, :ct, :grace) RETURNING id"
            ),
            {"email": email, "name": name, "phone": phone, "hash": pw_hash, "ct": ct, "grace": grace},
        ).first()
        db.commit()
        user_ids[email] = result[0]

    contacts_cfg = [
        (user_ids["demo1@stillhere.hack"], "Bob (Demo Contact)", phone2),
        (user_ids["demo2@stillhere.hack"], "Alice (Demo Contact)", phone1),
    ]
    for uid, cname, cphone in contacts_cfg:
        existing = db.execute(
            text("SELECT id FROM emergency_contacts WHERE user_id=:uid AND phone=:phone"),
            {"uid": uid, "phone": cphone},
        ).first()
        if not existing:
            db.execute(
                text("INSERT INTO emergency_contacts (user_id, name, phone, priority) VALUES (:uid, :name, :phone, 1)"),
                {"uid": uid, "name": cname, "phone": cphone},
            )
            db.commit()
    return user_ids["demo1@stillhere.hack"], user_ids["demo2@stillhere.hack"]


def reset_demo(db):
    uids = db.execute(
        text("SELECT id FROM users WHERE email = ANY(:emails)"),
        {"emails": DEMO_EMAILS},
    ).fetchall()
    uid_list = [str(r[0]) for r in uids]
    counts = {}
    if uid_list:
        for table in ("contact_confirmations", "escalation_events", "checkins", "audit_log", "emergency_contacts"):
            r = db.execute(text(f"DELETE FROM {table} WHERE user_id::text = ANY(:uids)"), {"uids": uid_list})
            counts[table] = r.rowcount
        r = db.execute(text("DELETE FROM users WHERE id::text = ANY(:uids)"), {"uids": uid_list})
        counts["users"] = r.rowcount
        db.commit()
    return counts


@router.get("/events")
def get_demo_events(db=Depends(get_session)):
    events_rows = db.execute(
        text(
            "SELECT e.id, e.stage, e.triggered_at, e.resolved, e.confirmation_token, "
            "e.user_confirmed_at, u.name AS user_name, u.email AS user_email "
            "FROM escalation_events e JOIN users u ON e.user_id = u.id "
            "WHERE u.email = ANY(:emails) ORDER BY e.triggered_at DESC"
        ),
        {"emails": DEMO_EMAILS},
    ).mappings().all()

    events = []
    for r in events_rows:
        row = dict(r)
        if row["triggered_at"]:
            row["triggered_at"] = row["triggered_at"].isoformat() if hasattr(row["triggered_at"], "isoformat") else str(row["triggered_at"])
        if row.get("user_confirmed_at"):
            row["user_confirmed_at"] = row["user_confirmed_at"].isoformat() if hasattr(row["user_confirmed_at"], "isoformat") else str(row["user_confirmed_at"])
        eid = row["id"]
        confirms = db.execute(
            text(
                "SELECT cc.confirmation_token, cc.confirmed_at, ec.name as contact_name "
                "FROM contact_confirmations cc JOIN emergency_contacts ec ON cc.contact_id = ec.id "
                "WHERE cc.escalation_event_id = :eid"
            ),
            {"eid": eid},
        ).mappings().all()
        row["contact_confirmations"] = [
            {
                "contact_name": c["contact_name"],
                "confirmed": c["confirmed_at"] is not None,
                "confirmed_at": c["confirmed_at"].isoformat() if c["confirmed_at"] and hasattr(c["confirmed_at"], "isoformat") else (str(c["confirmed_at"]) if c["confirmed_at"] else None),
            }
            for c in confirms
        ]
        events.append(row)

    users = []
    for email in DEMO_EMAILS:
        u = db.execute(text("SELECT id, name, email FROM users WHERE email = :e"), {"e": email}).mappings().first()
        if not u:
            users.append({"name": DEMO_DISPLAY[email], "email": email, "checked_in_today": False, "active_escalation": False})
            continue
        uid = str(u["id"])
        ck = db.execute(
            text("SELECT 1 FROM checkins WHERE user_id = :uid AND checked_in_at::date = :today LIMIT 1"),
            {"uid": uid, "today": date.today()},
        ).first()
        esc = db.execute(
            text("SELECT 1 FROM escalation_events WHERE user_id = :uid AND resolved = FALSE LIMIT 1"),
            {"uid": uid},
        ).first()
        users.append({
            "name": u["name"] or DEMO_DISPLAY[email],
            "email": email,
            "checked_in_today": ck is not None,
            "active_escalation": esc is not None,
        })

    return {"events": events, "users": users}


@router.get("/reset")
def do_reset():
    db = SessionLocal()
    try:
        counts = reset_demo(db)
        return {"status": "reset", "deleted": counts}
    finally:
        db.close()


@router.get("/seed")
def do_seed(
    phone1: str = Query("+15551234567"),
    phone2: str = Query("+15559876543"),
):
    db = SessionLocal()
    try:
        u1, u2 = seed_demo(db, phone1, phone2)
        return {"status": "seeded", "user_ids": [str(u1), str(u2)]}
    finally:
        db.close()


@router.post("/dry-run")
def dry_run(user=Depends(get_current_user), db=Depends(get_session)):
    uid = str(user["id"])
    contacts = get_contacts(db, uid)
    user_name = user.get("name", "Someone")
    event_id = log_escalation_event(db, uid, "dry_run")
    preview = []
    for c in contacts:
        token = str(uuid.uuid4())
        confirm_url = f"{settings.base_url}/confirm/{token}"
        sms_text = f"Hi {c['name']}, {user_name} missed their check-in. Are they safe? Confirm: {confirm_url}"
        preview.append({
            "contact_name": c["name"],
            "contact_phone": c["phone"],
            "sms_text": sms_text,
            "confirm_url": confirm_url,
        })
    db.execute(
        text("UPDATE escalation_events SET resolved = TRUE, resolved_at = NOW() WHERE id::text = :eid"),
        {"eid": str(event_id)},
    )
    db.commit()
    return {"preview": preview, "contacts_count": len(contacts), "event_id": str(event_id)}


@router.post("/sensor-fire")
def sensor_fire(user=Depends(get_current_user), db=Depends(get_session)):
    from db import register_sensor, update_sensor_reading, auto_checkin_if_active
    uid = str(user["id"])
    register_sensor(db, uid, "motion", "ha_demo_motion")
    update_sensor_reading(db, uid, "ha_demo_motion", {"motion": True})
    checked_in = auto_checkin_if_active(db, uid, "sensor")
    return {"status": "fired", "auto_checkin": checked_in}


@router.post("/step/checkin")
def step_checkin():
    db = SessionLocal()
    try:
        user = db.execute(
            text("SELECT id, name FROM users WHERE email = 'demo1@stillhere.hack'")
        ).mappings().first()
        if not user:
            return {"error": "Demo users not seeded"}
        uid = str(user["id"])
        log_checkin(db, uid)
        log_audit_event(db, uid, "checkin", {"source": "demo_step"})
        return {"step": "checkin", "user": "Alice", "message": "Alice checked in. Someone always knows she's here."}
    finally:
        db.close()


@router.post("/step/send-prompt")
def step_send_prompt():
    db = SessionLocal()
    try:
        user = db.execute(
            text("SELECT id FROM users WHERE email = 'demo1@stillhere.hack'")
        ).mappings().first()
        if not user:
            return {"error": "Demo users not seeded"}
        uid = str(user["id"])
        log_audit_event(db, uid, "prompt_sent")
        return {"step": "send_prompt", "user": "Alice", "message": "Push notification sent to Alice: 'Still here? Tap to check in.'"}
    finally:
        db.close()


@router.post("/step/miss-checkin")
def step_miss_checkin():
    db = SessionLocal()
    try:
        user = db.execute(
            text("SELECT id FROM users WHERE email = 'demo1@stillhere.hack'")
        ).mappings().first()
        if not user:
            return {"error": "Demo users not seeded"}
        uid = str(user["id"])
        result = db.execute(
            text("INSERT INTO escalation_events (user_id, stage, resolved) VALUES (:uid, 'grace_period', FALSE) RETURNING id"),
            {"uid": uid},
        ).first()
        db.commit()
        return {"step": "miss_checkin", "user": "Alice", "escalation_id": str(result[0]), "message": "Alice hasn't checked in. Grace period started. Waiting..."}
    finally:
        db.close()


@router.post("/step/grace-expire")
def step_grace_expire():
    db = SessionLocal()
    try:
        user = db.execute(
            text("SELECT id FROM users WHERE email = 'demo1@stillhere.hack'")
        ).mappings().first()
        if not user:
            return {"error": "Demo users not seeded"}
        uid = str(user["id"])
        esc = db.execute(
            text("SELECT id FROM escalation_events WHERE user_id = :uid AND resolved = FALSE ORDER BY triggered_at DESC LIMIT 1"),
            {"uid": uid},
        ).mappings().first()
        if not esc:
            return {"error": "No active escalation"}
        eid = esc["id"]
        db.execute(
            text("UPDATE escalation_events SET stage = 'contacts_alerted' WHERE id = :eid"),
            {"eid": eid},
        )
        contacts = db.execute(
            text("SELECT id, name, phone FROM emergency_contacts WHERE user_id = :uid ORDER BY priority"),
            {"uid": uid},
        ).mappings().all()
        contact_list = []
        for c in contacts:
            token = str(uuid.uuid4())
            db.execute(
                text("INSERT INTO contact_confirmations (escalation_event_id, contact_id, confirmation_token) VALUES (:eid, :cid, :token)"),
                {"eid": eid, "cid": c["id"], "token": token},
            )
            contact_list.append({
                "name": c["name"],
                "token": token,
                "sms": f"Hi {c['name']}, Alice missed their check-in. Are they safe? Confirm: {settings.base_url}/confirm/{token}",
            })
        log_audit_event(db, uid, "contacts_alerted")
        db.commit()
        if settings.demo_sms_to and contact_list:
            sms_body = f"Hi {contact_list[0]['name']}, Alice missed their check-in. Are they safe? Confirm: {settings.base_url}/confirm/{contact_list[0]['token']}"
            send_sms(settings.demo_sms_to, sms_body)
        return {"step": "grace_expire", "contacts": contact_list, "message": "Grace period expired. SMS sent to all emergency contacts."}
    finally:
        db.close()


@router.post("/step/contact-confirm")
def step_contact_confirm():
    db = SessionLocal()
    try:
        user = db.execute(
            text("SELECT id FROM users WHERE email = 'demo1@stillhere.hack'")
        ).mappings().first()
        if not user:
            return {"error": "Demo users not seeded"}
        uid = str(user["id"])
        esc = db.execute(
            text("SELECT id FROM escalation_events WHERE user_id = :uid AND resolved = FALSE ORDER BY triggered_at DESC LIMIT 1"),
            {"uid": uid},
        ).mappings().first()
        if not esc:
            return {"error": "No active escalation"}
        eid = esc["id"]
        cc = db.execute(
            text("SELECT id, contact_id FROM contact_confirmations WHERE escalation_event_id = :eid LIMIT 1"),
            {"eid": eid},
        ).mappings().first()
        if cc:
            db.execute(
                text("UPDATE contact_confirmations SET confirmed_at = NOW() WHERE id = :ccid"),
                {"ccid": cc["id"]},
            )
            db.commit()
        return {"step": "contact_confirm", "contact": "Bob", "message": "Bob confirmed: 'Yes, Alice is safe.' Waiting for Alice to confirm..."}
    finally:
        db.close()


@router.post("/step/contact-cant-reach")
def step_contact_cant_reach():
    db = SessionLocal()
    try:
        user = db.execute(
            text("SELECT id FROM users WHERE email = 'demo1@stillhere.hack'")
        ).mappings().first()
        if not user:
            return {"error": "Demo users not seeded"}
        uid = str(user["id"])
        log_audit_event(db, uid, "contact_cant_reach")
        return {"step": "contact_cant_reach", "contact": "Bob", "message": "Bob says: 'I can't reach Alice.' Concern growing..."}
    finally:
        db.close()


@router.post("/step/user-confirm")
def step_user_confirm():
    db = SessionLocal()
    try:
        user = db.execute(
            text("SELECT id FROM users WHERE email = 'demo1@stillhere.hack'")
        ).mappings().first()
        if not user:
            return {"error": "Demo users not seeded"}
        uid = str(user["id"])
        esc = db.execute(
            text("SELECT id FROM escalation_events WHERE user_id = :uid AND resolved = FALSE ORDER BY triggered_at DESC LIMIT 1"),
            {"uid": uid},
        ).mappings().first()
        if not esc:
            return {"error": "No active escalation"}
        eid = esc["id"]
        db.execute(
            text("UPDATE escalation_events SET user_confirmed_at = NOW(), resolved = TRUE, resolved_at = NOW() WHERE id = :eid"),
            {"eid": eid},
        )
        db.commit()
        log_checkin(db, uid, "escalation_confirm")
        log_audit_event(db, uid, "user_confirmed_escalation")
        return {"step": "user_confirm", "user": "Alice", "message": "Alice confirmed she's safe. Escalation resolved. Crisis averted."}
    finally:
        db.close()


@router.post("/step/welfare-check")
def step_welfare_check():
    db = SessionLocal()
    try:
        user = db.execute(
            text("SELECT id FROM users WHERE email = 'demo1@stillhere.hack'")
        ).mappings().first()
        if not user:
            return {"error": "Demo users not seeded"}
        uid = str(user["id"])
        esc = db.execute(
            text("SELECT id FROM escalation_events WHERE user_id = :uid AND resolved = FALSE ORDER BY triggered_at DESC LIMIT 1"),
            {"uid": uid},
        ).mappings().first()
        if not esc:
            return {"error": "No active escalation"}
        eid = esc["id"]
        db.execute(
            text("UPDATE escalation_events SET stage = 'non_emergency_called', resolved = TRUE, resolved_at = NOW() WHERE id = :eid"),
            {"eid": eid},
        )
        db.commit()
        log_audit_event(db, uid, "non_emergency_called")
        return {"step": "welfare_check", "user": "Alice", "message": "Non-emergency welfare check initiated. This is the last resort, only after every other step failed."}
    finally:
        db.close()


@router.post("/sample-email")
def send_sample_email(body: dict, db=Depends(get_session)):
    to_email = (body.get("email") or "").strip().lower()
    if not to_email or "@" not in to_email:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Valid email required")
    user = db.execute(
        text("SELECT id, name FROM users WHERE email = 'demo1@stillhere.hack'")
    ).mappings().first()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Demo not seeded — visit /demo first")
    from services.email_svc import send_checkin_email
    sent = send_checkin_email(to_email, "Alice", str(user["id"]))
    return {"sent": sent, "to": to_email, "note": "Real check-in email sent. The link in it actually works."}


@router.get("/state")
def get_demo_state():
    db = SessionLocal()
    try:
        user = db.execute(
            text("SELECT id, name FROM users WHERE email = 'demo1@stillhere.hack'")
        ).mappings().first()
        if not user:
            return {"seeded": False}
        uid = str(user["id"])
        state = {"seeded": True, "user": {"name": user["name"], "email": "demo1@stillhere.hack"}}
        ck = db.execute(
            text("SELECT 1 FROM checkins WHERE user_id = :uid AND checked_in_at::date = :today LIMIT 1"),
            {"uid": uid, "today": date.today()},
        ).first()
        state["checked_in_today"] = ck is not None
        esc = db.execute(
            text("SELECT id, stage, resolved, triggered_at FROM escalation_events WHERE user_id = :uid AND resolved = FALSE ORDER BY triggered_at DESC LIMIT 1"),
            {"uid": uid},
        ).mappings().first()
        state["active_escalation"] = esc is not None
        if esc:
            state["escalation"] = {
                "id": str(esc["id"]),
                "stage": esc["stage"],
                "triggered_at": esc["triggered_at"].isoformat() if esc["triggered_at"] and hasattr(esc["triggered_at"], "isoformat") else str(esc["triggered_at"]) if esc["triggered_at"] else None,
            }
            confirms = db.execute(
                text("SELECT cc.confirmation_token, cc.confirmed_at, ec.name FROM contact_confirmations cc JOIN emergency_contacts ec ON cc.contact_id = ec.id WHERE cc.escalation_event_id = :eid"),
                {"eid": esc["id"]},
            ).mappings().all()
            state["contact_confirmations"] = [
                {"contact_name": c["name"], "confirmed": c["confirmed_at"] is not None}
                for c in confirms
            ]
        else:
            state["escalation"] = None
            state["contact_confirmations"] = []
        return state
    finally:
        db.close()
