import uuid
import math
from datetime import datetime, timedelta, timezone

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config import settings

celery_app = Celery("stillhere", broker=settings.celery_broker)
celery_app.conf.timezone = "UTC"

engine = create_engine(settings.database_url)
Session = sessionmaker(bind=engine)


def _db():
    return Session()


@celery_app.task
def poll_and_fire():
    db = _db()
    try:
        now_utc = datetime.now(timezone.utc)
        current_time = now_utc.time().replace(second=0, microsecond=0)
        rows = db.execute(
            text("SELECT * FROM users WHERE checkin_time = :t"),
            {"t": current_time},
        ).mappings().all()
        for user in rows:
            u = dict(user)
            if u.get("snooze_until") and u["snooze_until"] > now_utc:
                continue
            vac = db.execute(
                text("SELECT vacation_start, vacation_end FROM users WHERE id::text = :uid"),
                {"uid": str(u["id"])},
            ).mappings().first()
            v = dict(vac) if vac else {}
            if v.get("vacation_start") and v.get("vacation_end"):
                if v["vacation_start"] <= now_utc <= v["vacation_end"]:
                    continue
            today = now_utc.date()
            already = db.execute(
                text(
                    "SELECT 1 FROM checkins WHERE user_id::text = :uid AND checked_in_at::date = :d LIMIT 1"
                ),
                {"uid": str(u["id"]), "d": today},
            ).first()
            if already:
                continue
            if u.get("is_dormant"):
                continue
            schedule_daily_checkin.delay(str(u["id"]))
    finally:
        db.close()


@celery_app.task
def schedule_daily_checkin(user_id: str):
    from db import log_escalation_event, get_random_checkin_message
    from services.push_svc import send_push

    db = _db()
    try:
        user = db.execute(
            text("SELECT grace_minutes, confirm_by_minutes, device_token FROM users WHERE id::text = :uid"),
            {"uid": user_id},
        ).mappings().first()
        u = dict(user) if user else {}
        grace = u.get("grace_minutes", 120)
        confirm_by = u.get("confirm_by_minutes", 0) or 0
        total_grace = grace + confirm_by
        msg = get_random_checkin_message(db)
        if u.get("device_token"):
            from db import get_random_prompt
            prompt = get_random_prompt(db)
            push_body = f"{msg}" if not prompt else f"{msg}\n💡 {prompt}"
            send_push(u["device_token"], "Still Here", push_body, settings.base_url)
        event_id = log_escalation_event(db, user_id, "checkin_requested")
        user_row = db.execute(
            text("SELECT email, name FROM users WHERE id::text = :uid"),
            {"uid": user_id},
        ).mappings().first()
        if user_row:
            u = dict(user_row)
            from services.email_svc import send_checkin_email
            send_checkin_email(u["email"], u.get("name", ""), user_id)
        check_user_grace.apply_async(args=[user_id, str(event_id)], countdown=total_grace * 60)
    finally:
        db.close()


@celery_app.task
def check_user_grace(user_id: str, escalation_event_id: str):
    from db import has_checked_in_today

    db = _db()
    try:
        if has_checked_in_today(db, user_id):
            return
        row = db.execute(
            text("SELECT resolved FROM escalation_events WHERE id::text = :eid"),
            {"eid": escalation_event_id},
        ).first()
        if row and row[0]:
            return
        escalate_to_contacts.delay(user_id, escalation_event_id)
    finally:
        db.close()


@celery_app.task
def escalate_to_contacts(user_id: str, escalation_event_id: str):
    from db import get_contacts
    from services.sns_svc import send_sms
    from services.push_svc import send_push

    db = _db()
    try:
        user = db.execute(
            text("SELECT name, device_token, contact_grace_hours FROM users WHERE id::text = :uid"),
            {"uid": user_id},
        ).mappings().first()
        if not user:
            return
        u = dict(user)
        user_name = u.get("name", "Someone")
        contacts = get_contacts(db, user_id)
        tokens = {}
        for c in contacts:
            token = str(uuid.uuid4())
            tokens[str(c["id"])] = token
            db.execute(
                text(
                    "INSERT INTO contact_confirmations (escalation_event_id, contact_id, confirmation_token) VALUES (:eid, :cid, :token)"
                ),
                {"eid": escalation_event_id, "cid": str(c["id"]), "token": token},
            )
        db.commit()
        for c in contacts:
            confirm_url = f"{settings.base_url}/confirm/{tokens[str(c['id'])]}"
            send_sms(
                c["phone"],
                f"Hi {c['name']}, {user_name} missed their check-in. Are they safe? Confirm: {confirm_url}",
            )
        if u.get("device_token"):
            send_push(u["device_token"], "Contacts Notified", "We've notified your emergency contacts.", settings.base_url)
        db.execute(
            text("UPDATE escalation_events SET stage = 'contacts_notified' WHERE id::text = :eid"),
            {"eid": escalation_event_id},
        )
        db.commit()
        contact_grace_hours = u.get("contact_grace_hours", 48)
        check_contact_majority.apply_async(args=[user_id, escalation_event_id], countdown=600)
        contact_grace_timeout.apply_async(args=[user_id, escalation_event_id], countdown=contact_grace_hours * 3600)
    finally:
        db.close()


@celery_app.task
def check_contact_majority(user_id: str, escalation_event_id: str):
    from services.push_svc import send_push

    db = _db()
    try:
        evt = db.execute(
            text("SELECT resolved, user_confirmed_at, triggered_at, user_id FROM escalation_events WHERE id::text = :eid"),
            {"eid": escalation_event_id},
        ).mappings().first()
        if not evt:
            return
        e = dict(evt)
        if e.get("resolved"):
            return
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
            if e.get("user_confirmed_at"):
                return
            user = db.execute(
                text("SELECT device_token FROM users WHERE id::text = :uid"),
                {"uid": user_id},
            ).mappings().first()
            u = dict(user) if user else {}
            if u.get("device_token"):
                send_push(
                    u["device_token"],
                    "Contacts Believe You're Safe",
                    f"Please confirm: {settings.base_url}/confirm-user/{escalation_event_id}",
                    f"{settings.base_url}/confirm-user/{escalation_event_id}",
                )
            check_contact_majority.apply_async(args=[user_id, escalation_event_id], countdown=3600)
        else:
            user = db.execute(
                text("SELECT contact_grace_hours FROM users WHERE id::text = :uid"),
                {"uid": user_id},
            ).mappings().first()
            u = dict(user) if user else {}
            grace_hours = u.get("contact_grace_hours", 48)
            deadline = e["triggered_at"] + timedelta(hours=grace_hours)
            if datetime.now(timezone.utc) < deadline:
                check_contact_majority.apply_async(args=[user_id, escalation_event_id], countdown=7200)
            else:
                call_non_emergency_task.delay(user_id)
    finally:
        db.close()


@celery_app.task
def contact_grace_timeout(user_id: str, escalation_event_id: str):
    from services.push_svc import send_push

    db = _db()
    try:
        evt = db.execute(
            text("SELECT resolved, user_confirmed_at FROM escalation_events WHERE id::text = :eid"),
            {"eid": escalation_event_id},
        ).mappings().first()
        if not evt:
            return
        e = dict(evt)
        if e.get("resolved"):
            return
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
            if not e.get("user_confirmed_at"):
                user = db.execute(
                    text("SELECT device_token FROM users WHERE id::text = :uid"),
                    {"uid": user_id},
                ).mappings().first()
                u = dict(user) if user else {}
                if u.get("device_token"):
                    send_push(
                        u["device_token"],
                        "Please Confirm",
                        f"Your contacts believe you're safe. Confirm: {settings.base_url}/confirm-user/{escalation_event_id}",
                        f"{settings.base_url}/confirm-user/{escalation_event_id}",
                    )
                contact_grace_timeout.apply_async(args=[user_id, escalation_event_id], countdown=14400)
        else:
            call_non_emergency_task.delay(user_id)
    finally:
        db.close()


@celery_app.task(name="tasks.escalation.call_non_emergency_task")
def call_non_emergency_task(user_id: str):
    from db import log_escalation_event
    from services.push_svc import send_push
    from services.non_emergency_svc import call_non_emergency

    db = _db()
    try:
        rate = db.execute(
            text("SELECT 1 FROM escalation_events WHERE user_id::text = :uid AND stage = 'non_emergency_call' AND triggered_at > NOW() - INTERVAL '72 hours' LIMIT 1"),
            {"uid": user_id},
        ).first()
        if rate:
            return
        user = db.execute(
            text("SELECT name, phone, device_token FROM users WHERE id::text = :uid"),
            {"uid": user_id},
        ).mappings().first()
        if not user:
            return
        u = dict(user)
        log_escalation_event(db, user_id, "non_emergency_call")
        call_non_emergency(u.get("name", ""), u.get("phone", ""))
        if u.get("device_token"):
            send_push(u["device_token"], "Wellness Check Requested", "Please check in if safe.", settings.base_url)
    finally:
        db.close()


@celery_app.task
def send_weekly_digest():
    db = _db()
    try:
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        rows = db.execute(
            text("SELECT id, email, name FROM users WHERE created_at < :week_ago"),
            {"week_ago": week_ago},
        ).mappings().all()
        for user in rows:
            u = dict(user)
            uid = str(u["id"])
            count = db.execute(
                text("SELECT COUNT(*) FROM checkins WHERE user_id::text = :uid AND checked_in_at > :week_ago"),
                {"uid": uid, "week_ago": week_ago},
            ).scalar()
            import resend
            resend.api_key = settings.resend_api_key
            try:
                resend.Emails.send({
                    "from": settings.email_from,
                    "to": [u["email"]],
                    "subject": f"Your weekly Still Here report — {count}/7 days",
                    "html": f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:480px;margin:0 auto;padding:40px 20px;text-align:center;background:#0f0f1a;color:#eee">
<h1 style="font-size:28px;font-weight:700;color:#4ecca3">Weekly Report</h1>
<p style="font-size:16px;line-height:1.6;opacity:.8">Hey {u.get('name', '')}, you checked in <strong>{count}/7</strong> days this week.</p>
<p style="font-size:14px;opacity:.6">Keep going — someone always knows you're here.</p>
<div style="font-size:12px;opacity:.3;letter-spacing:1px;margin-top:40px">STILL HERE</div></div>""",
                })
            except Exception:
                pass
    finally:
        db.close()


@celery_app.task
def check_streak_reminders():
    db = _db()
    try:
        from db import has_checked_in_today, get_streak
        from services.push_svc import send_push
        now_utc = datetime.now(timezone.utc)
        rows = db.execute(
            text("SELECT id, checkin_time, confirm_by_minutes, streak_reminder_hours, device_token FROM users WHERE device_token IS NOT NULL"),
        ).mappings().all()
        for user in rows:
            u = dict(user)
            uid = str(u["id"])
            if has_checked_in_today(db, uid):
                continue
            streak = get_streak(db, uid)
            if streak < 3:
                continue
            checkin_time = u.get("checkin_time")
            if not checkin_time:
                continue
            confirm_by = u.get("confirm_by_minutes", 0) or 0
            reminder_hours = u.get("streak_reminder_hours", 2) or 2
            target_time = datetime.combine(now_utc.date(), checkin_time) + timedelta(minutes=confirm_by) - timedelta(hours=reminder_hours)
            target_time = target_time.replace(tzinfo=timezone.utc)
            if abs((now_utc - target_time).total_seconds()) < 1800:
                send_push(u["device_token"], f"{streak}-day streak at risk!", "Just a friendly reminder to check in today.", settings.base_url)
    finally:
        db.close()


@celery_app.task
def check_dormant_accounts():
    db = _db()
    try:
        from services.email_svc import send_reengagement_email
        now = datetime.now(timezone.utc)
        rows = db.execute(
            text("SELECT id, email, name, last_device_ping, is_dormant FROM users WHERE is_dormant = FALSE"),
        ).mappings().all()
        for user in rows:
            u = dict(user)
            uid = str(u["id"])
            last_ping = u.get("last_device_ping")
            if not last_ping:
                continue
            days_inactive = (now - last_ping.replace(tzinfo=timezone.utc)).days
            if days_inactive >= 30:
                db.execute(
                    text("UPDATE users SET is_dormant = TRUE WHERE id::text = :uid"),
                    {"uid": uid},
                )
                db.commit()
            elif days_inactive >= 14:
                reengaged = db.execute(
                    text("SELECT 1 FROM audit_log WHERE user_id::text = :uid AND event_type = 'reengagement_email' AND created_at > NOW() - INTERVAL '7 days' LIMIT 1"),
                    {"uid": uid},
                ).first()
                if not reengaged:
                    send_reengagement_email(u["email"], u.get("name", ""))
                    from db import log_audit_event
                    log_audit_event(db, uid, "reengagement_email", {"days_inactive": days_inactive})
    finally:
        db.close()


celery_app.conf.beat_schedule = {
    "poll-every-minute": {
        "task": "tasks.escalation.poll_and_fire",
        "schedule": crontab(minute="*"),
    },
    "weekly-digest": {
        "task": "tasks.escalation.send_weekly_digest",
        "schedule": crontab(day_of_week="mon", hour="9", minute="0"),
    },
    "streak-reminder": {
        "task": "tasks.escalation.check_streak_reminders",
        "schedule": crontab(minute="*/30"),
    },
    "dormant-check": {
        "task": "tasks.escalation.check_dormant_accounts",
        "schedule": crontab(hour="3", minute="0"),
    },
}
