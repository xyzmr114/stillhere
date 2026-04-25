import uuid
import math
from datetime import datetime, timedelta, timezone

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config import settings
from constants import (
    SMS_DELAY_SECONDS,
    DEFAULT_GRACE_MINUTES,
    DEFAULT_CONTACT_GRACE_HOURS,
    CONTACT_CHECK_DELAY_SECONDS,
    CONTACT_RECHECK_DELAY_SECONDS,
    CONTACT_GRACE_TIMEOUT_RECHECK_SECONDS,
    NON_EMERGENCY_CALL_RATE_LIMIT_HOURS,
    DORMANT_ACCOUNT_THRESHOLD_DAYS,
    DORMANT_REENGAGEMENT_THRESHOLD_DAYS,
    REENGAGEMENT_EMAIL_RATE_LIMIT_DAYS,
    MIN_STREAK_FOR_REMINDER,
)

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
        # Compare checkin_time against each user's local time using their timezone
        rows = db.execute(
            text(
                "SELECT * FROM users "
                "WHERE checkin_time = (NOW() AT TIME ZONE COALESCE(timezone, 'UTC'))::time(0) "
                "AND is_dormant = FALSE "
                "AND email_verified = TRUE "
                "AND (has_paid = TRUE OR trial_ends_at > NOW())"
            ),
        ).mappings().all()
        for user in rows:
            u = dict(user)
            if u.get("snooze_until") and u["snooze_until"] > now_utc:
                continue
            if u.get("vacation_start") and u.get("vacation_end"):
                if u["vacation_start"] <= now_utc <= u["vacation_end"]:
                    continue
            # Check if already checked in today in user's local timezone
            user_tz = u.get("timezone") or "UTC"
            already = db.execute(
                text(
                    "SELECT 1 FROM checkins WHERE user_id::text = :uid "
                    "AND checked_in_at AT TIME ZONE :tz >= (NOW() AT TIME ZONE :tz)::date "
                    "LIMIT 1"
                ),
                {"uid": str(u["id"]), "tz": user_tz},
            ).first()
            if already:
                continue
            schedule_daily_checkin.delay(str(u["id"]))
    finally:
        db.close()


def _is_quiet_hours(user_dict: dict) -> bool:
    """Check if the current time in user's timezone falls within their quiet hours."""
    qh_start = user_dict.get("quiet_hours_start")
    qh_end = user_dict.get("quiet_hours_end")
    if not qh_start or not qh_end:
        return False
    from zoneinfo import ZoneInfo
    user_tz_name = user_dict.get("timezone") or "UTC"
    try:
        user_tz = ZoneInfo(user_tz_name)
    except (KeyError, Exception):
        user_tz = ZoneInfo("UTC")
    now_local = datetime.now(timezone.utc).astimezone(user_tz).time()
    if qh_start <= qh_end:
        return qh_start <= now_local <= qh_end
    # Wraps midnight (e.g. 22:00 - 07:00)
    return now_local >= qh_start or now_local <= qh_end


@celery_app.task
def schedule_daily_checkin(user_id: str):
    from db import log_escalation_event, get_random_checkin_message
    from services.push_svc import send_push
    from auth import create_jwt

    db = _db()
    try:
        user = db.execute(
            text("SELECT grace_minutes, confirm_by_minutes, device_token, "
                 "notify_push, notify_email, notify_sms, "
                 "quiet_hours_start, quiet_hours_end, timezone, token_version, "
                 "email_verified "
                 "FROM users WHERE id::text = :uid"),
            {"uid": user_id},
        ).mappings().first()
        u = dict(user) if user else {}
        if not u.get("email_verified"):
            return  # unverified accounts cannot trigger escalation
        grace = u.get("grace_minutes", DEFAULT_GRACE_MINUTES)
        confirm_by = u.get("confirm_by_minutes", 0) or 0
        total_grace = grace + confirm_by
        quiet = _is_quiet_hours(u)
        msg = get_random_checkin_message(db)
        push_enabled = u.get("notify_push", True) is not False
        if u.get("device_token") and push_enabled and not quiet:
            from db import get_random_prompt
            prompt = get_random_prompt(db)
            push_body = f"{msg}" if not prompt else f"{msg}\n💡 {prompt}"
            # Generate quick-checkin token (1 hour expiry)
            quick_token = create_jwt(user_id, token_version=u.get("token_version", 1))
            from jose import jwt
            payload = jwt.decode(quick_token, settings.jwt_secret, algorithms=["HS256"])
            payload["type"] = "quick_checkin"
            payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=1)
            quick_token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
            push_data = {"quick_checkin_token": quick_token}
            send_push(u["device_token"], "Still Here", push_body, settings.base_url, data=push_data)
        event_id = log_escalation_event(db, user_id, "checkin_requested")
        email_enabled = u.get("notify_email", True) is not False
        if email_enabled and not quiet:
            user_row = db.execute(
                text("SELECT email, name FROM users WHERE id::text = :uid"),
                {"uid": user_id},
            ).mappings().first()
            if user_row:
                ur = dict(user_row)
                from services.email_svc import send_checkin_email
                send_checkin_email(ur["email"], ur.get("name", ""), user_id)
        sms_enabled = u.get("notify_sms", True) is not False
        if sms_enabled:
            sms_to_user.apply_async(args=[user_id], countdown=SMS_DELAY_SECONDS)
        check_user_grace.apply_async(args=[user_id, str(event_id)], countdown=total_grace * 60)
    finally:
        db.close()


@celery_app.task
def sms_to_user(user_id: str):
    from db import has_checked_in_today
    from services.sns_svc import send_sms

    db = _db()
    try:
        if has_checked_in_today(db, user_id):
            return
        user = db.execute(
            text("SELECT phone, name, notify_sms, quiet_hours_start, quiet_hours_end, timezone FROM users WHERE id::text = :uid"),
            {"uid": user_id},
        ).mappings().first()
        if not user:
            return
        u = dict(user)
        if not u.get("phone"):
            return
        if u.get("notify_sms", True) is False:
            return
        if _is_quiet_hours(u):
            return
        checkin_url = f"{settings.base_url}/signin"
        send_sms(
            u["phone"],
            f"Hey {u.get('name', 'there')}, you haven't checked in yet today. "
            f"Tap to check in: {checkin_url}",
        )
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
    from services.email_svc import _send_email

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
            # Send email if contact has one
            if c.get("email"):
                from email_templates import contact_alert
                email_html = contact_alert(user_name, confirm_url)
                _send_email(
                    c["email"],
                    f"Emergency: {user_name} missed their check-in",
                    email_html,
                )
        from services.sns_svc import call_contact
        for c in contacts:
            if c.get("phone"):
                call_contact(c["phone"], user_name)
        if u.get("device_token"):
            send_push(u["device_token"], "Contacts Notified", "We've notified your emergency contacts.", settings.base_url)
        db.execute(
            text("UPDATE escalation_events SET stage = 'contacts_notified' WHERE id::text = :eid"),
            {"eid": escalation_event_id},
        )
        db.commit()
        contact_grace_hours = u.get("contact_grace_hours", DEFAULT_CONTACT_GRACE_HOURS)
        check_contact_majority.apply_async(args=[user_id, escalation_event_id], countdown=CONTACT_CHECK_DELAY_SECONDS)
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
            check_contact_majority.apply_async(args=[user_id, escalation_event_id], countdown=CONTACT_MAJORITY_CHECK_INTERVAL_SECONDS)
        else:
            user = db.execute(
                text("SELECT contact_grace_hours FROM users WHERE id::text = :uid"),
                {"uid": user_id},
            ).mappings().first()
            u = dict(user) if user else {}
            grace_hours = u.get("contact_grace_hours", DEFAULT_CONTACT_GRACE_HOURS)
            deadline = e["triggered_at"] + timedelta(hours=grace_hours)
            if datetime.now(timezone.utc) < deadline:
                check_contact_majority.apply_async(args=[user_id, escalation_event_id], countdown=CONTACT_RECHECK_DELAY_SECONDS)
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
                contact_grace_timeout.apply_async(args=[user_id, escalation_event_id], countdown=CONTACT_GRACE_TIMEOUT_RECHECK_SECONDS)
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
            text("SELECT 1 FROM escalation_events WHERE user_id::text = :uid AND stage = 'non_emergency_call' AND triggered_at > NOW() - INTERVAL '1 hour' * :hours LIMIT 1"),
            {"uid": user_id, "hours": NON_EMERGENCY_CALL_RATE_LIMIT_HOURS},
        ).first()
        if rate:
            return
        user = db.execute(
            text("SELECT name, phone, device_token, non_emergency_number, address, city, state FROM users WHERE id::text = :uid"),
            {"uid": user_id},
        ).mappings().first()
        if not user:
            return
        u = dict(user)
        if not u.get("non_emergency_number"):
            import logging
            logging.getLogger(__name__).warning(f"[ESCALATION] User {user_id} has no non-emergency number — skipping welfare call")
            return
        log_escalation_event(db, user_id, "non_emergency_call")
        address_parts = [p for p in [u.get("address"), u.get("city"), u.get("state")] if p]
        location = ", ".join(address_parts) if address_parts else None
        call_non_emergency(u.get("name", ""), u.get("non_emergency_number", ""), location)
        if u.get("device_token"):
            send_push(u["device_token"], "Wellness Check Requested", "A welfare check has been requested. Please check in if you are safe.", settings.base_url)
    finally:
        db.close()


@celery_app.task
def notify_contacts_all_clear(user_id: str, escalation_event_id: str):
    import logging
    from db import get_contacts, log_audit_event
    from services.sns_svc import send_sms
    from services.email_svc import _send_email
    from email_templates import contact_all_clear

    logger = logging.getLogger(__name__)
    db = _db()
    try:
        evt = db.execute(
            text("SELECT stage FROM escalation_events WHERE id::text = :eid"),
            {"eid": escalation_event_id},
        ).mappings().first()
        if not evt or evt["stage"] != "contacts_notified":
            return
        user = db.execute(
            text("SELECT name FROM users WHERE id::text = :uid"),
            {"uid": user_id},
        ).mappings().first()
        if not user:
            return
        user_name = user["name"] or "Someone"
        contacts = get_contacts(db, user_id)
        for c in contacts:
            if c.get("phone"):
                try:
                    send_sms(c["phone"], f"\u2705 {user_name} checked in \u2014 no action needed. They are safe.")
                except Exception:
                    logger.exception("Failed to send all-clear SMS to contact %s", c["id"])
            if c.get("email"):
                try:
                    email_html = contact_all_clear(user_name)
                    _send_email(c["email"], f"All Clear: {user_name} checked in", email_html)
                except Exception:
                    logger.exception("Failed to send all-clear email to contact %s", c["id"])
        log_audit_event(db, user_id, "escalation_cleared", {"escalation_event_id": escalation_event_id})
    except Exception:
        logger.exception("notify_contacts_all_clear failed for user=%s event=%s", user_id, escalation_event_id)
    finally:
        db.close()


@celery_app.task
def send_weekly_digest():
    from services.email_svc import _send_email
    from email_templates import weekly_digest

    db = _db()
    try:
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        rows = db.execute(
            text("SELECT id, email, name FROM users WHERE created_at < :week_ago AND (notify_weekly_digest IS NULL OR notify_weekly_digest = TRUE)"),
            {"week_ago": week_ago},
        ).mappings().all()
        for user in rows:
            u = dict(user)
            uid = str(u["id"])
            count = db.execute(
                text("SELECT COUNT(*) FROM checkins WHERE user_id::text = :uid AND checked_in_at > :week_ago"),
                {"uid": uid, "week_ago": week_ago},
            ).scalar()
            try:
                html = weekly_digest(u.get('name', ''), count)
                _send_email(
                    u["email"],
                    f"Your weekly Still Here report — {count}/7 days",
                    html,
                )
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
            text("SELECT id, checkin_time, confirm_by_minutes, streak_reminder_hours, device_token, timezone FROM users WHERE device_token IS NOT NULL"),
        ).mappings().all()
        for user in rows:
            u = dict(user)
            uid = str(u["id"])
            if has_checked_in_today(db, uid):
                continue
            streak = get_streak(db, uid)
            if streak < MIN_STREAK_FOR_REMINDER:
                continue
            checkin_time = u.get("checkin_time")
            if not checkin_time:
                continue
            confirm_by = u.get("confirm_by_minutes", 0) or 0
            reminder_hours = u.get("streak_reminder_hours", DEFAULT_STREAK_REMINDER_HOURS) or DEFAULT_STREAK_REMINDER_HOURS
            # Calculate target time in user's local timezone
            from zoneinfo import ZoneInfo
            user_tz_name = u.get("timezone") or "UTC"
            try:
                user_tz = ZoneInfo(user_tz_name)
            except (KeyError, Exception):
                user_tz = ZoneInfo("UTC")
            now_local = now_utc.astimezone(user_tz)
            target_time = datetime.combine(now_local.date(), checkin_time) + timedelta(minutes=confirm_by) - timedelta(hours=reminder_hours)
            target_time = target_time.replace(tzinfo=user_tz)
            from constants import STREAK_REMINDER_WINDOW_SECONDS
            if abs((now_utc - target_time.astimezone(timezone.utc)).total_seconds()) < STREAK_REMINDER_WINDOW_SECONDS:
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
            if days_inactive >= DORMANT_ACCOUNT_THRESHOLD_DAYS:
                db.execute(
                    text("UPDATE users SET is_dormant = TRUE WHERE id::text = :uid"),
                    {"uid": uid},
                )
                db.commit()
            elif days_inactive >= DORMANT_REENGAGEMENT_THRESHOLD_DAYS:
                reengaged = db.execute(
                    text("SELECT 1 FROM audit_log WHERE user_id::text = :uid AND event_type = 'reengagement_email' AND created_at > NOW() - INTERVAL '1 day' * :days LIMIT 1"),
                    {"uid": uid, "days": REENGAGEMENT_EMAIL_RATE_LIMIT_DAYS},
                ).first()
                if not reengaged:
                    send_reengagement_email(u["email"], u.get("name", ""))
                    from db import log_audit_event
                    log_audit_event(db, uid, "reengagement_email", {"days_inactive": days_inactive})
    finally:
        db.close()


@celery_app.task
def check_activity_timers():
    """Check for expired activity timers and trigger escalation if necessary."""
    from db import log_escalation_event
    from services.push_svc import send_push

    db = _db()
    try:
        now_utc = datetime.now(timezone.utc)
        rows = db.execute(
            text(
                "SELECT id, device_token, activity_timer_label FROM users "
                "WHERE activity_timer_end IS NOT NULL "
                "AND activity_timer_end < :now "
                "AND is_dormant = FALSE"
            ),
            {"now": now_utc},
        ).mappings().all()

        for user in rows:
            u = dict(user)
            user_id = str(u["id"])
            timer_label = u.get("activity_timer_label", "Activity")

            # Check if user has already checked in today
            if db.execute(
                text(
                    "SELECT 1 FROM checkins c WHERE c.user_id::text = :uid "
                    "AND c.checked_in_at AT TIME ZONE 'UTC' >= NOW()::date LIMIT 1"
                ),
                {"uid": user_id},
            ).first():
                db.execute(
                    text("UPDATE users SET activity_timer_end = NULL, activity_timer_label = NULL WHERE id::text = :uid"),
                    {"uid": user_id},
                )
                db.commit()
                continue

            # Trigger escalation for missed activity timer
            log_escalation_event(db, user_id, "activity_timer_expired")
            if u.get("device_token"):
                send_push(
                    u["device_token"],
                    "Activity Timer Expired",
                    f"Your {timer_label} activity timer has expired. Please check in.",
                    settings.base_url,
                )

            # Clear the timer
            db.execute(
                text("UPDATE users SET activity_timer_end = NULL, activity_timer_label = NULL WHERE id::text = :uid"),
                {"uid": user_id},
            )
            db.commit()

            # Schedule escalation chain
            schedule_daily_checkin.delay(user_id)
    finally:
        db.close()


@celery_app.task
def check_dead_letters():
    """Check for and send dead letter messages when users miss check-ins for N consecutive days."""
    from db import get_unsent_dead_letters, get_days_since_last_checkin, get_contacts, mark_dead_letter_sent
    from services.email_svc import _send_email

    db = _db()
    try:
        # Get all users (we'll check each one's unsent dead letters)
        rows = db.execute(
            text("SELECT id FROM users WHERE is_dormant = FALSE"),
        ).mappings().all()

        for user_row in rows:
            user_id = str(user_row["id"])
            days_since = get_days_since_last_checkin(db, user_id)

            # Get unsent dead letters for this user
            dead_letters = get_unsent_dead_letters(db, user_id)

            for letter in dead_letters:
                # Check if enough days have passed
                if days_since >= letter["trigger_days"]:
                    try:
                        # Get user info for email
                        user_info = db.execute(
                            text("SELECT name, email FROM users WHERE id::text = :uid"),
                            {"uid": user_id},
                        ).mappings().first()
                        user_info = dict(user_info) if user_info else {}

                        # Determine recipients
                        recipients = []
                        if letter["recipient_type"] == "contacts":
                            # Send to all emergency contacts with email
                            contacts = get_contacts(db, user_id)
                            recipients = [c["email"] for c in contacts if c.get("email")]
                        else:
                            # Custom email recipient
                            if letter["recipient_email"]:
                                recipients = [letter["recipient_email"]]

                        # Send email to each recipient
                        for recipient_email in recipients:
                            try:
                                subject = letter["subject"]
                                body_html = f"""
<p>You are receiving this because {user_info.get('name', 'a user')} has not checked in for {days_since} days.</p>
<p style="white-space: pre-wrap; margin: 20px 0;">{letter['body']}</p>
<p style="opacity: 0.6; font-size: 12px;">This is a pre-written message from Still Here.</p>
"""
                                _send_email(recipient_email, subject, body_html)
                            except Exception as e:
                                logger.exception("Failed to send dead letter to %s for user %s", recipient_email, user_id)
                                continue

                        # Mark letter as sent
                        mark_dead_letter_sent(db, str(letter["id"]))
                    except Exception as e:
                        logger.exception("Failed to process dead letter %s for user %s", str(letter["id"]), user_id)
    finally:
        db.close()


@celery_app.task
def check_trial_expiry():
    """Send trial expiring/expired emails. Runs daily."""
    import logging
    logger = logging.getLogger(__name__)
    db = _db()
    try:
        # Users whose trial expires in 1 or 2 days (not yet expired, not paid)
        expiring = db.execute(
            text(
                "SELECT id, email, name, trial_ends_at FROM users "
                "WHERE has_paid = FALSE AND trial_ends_at IS NOT NULL "
                "AND trial_ends_at > NOW() "
                "AND trial_ends_at <= NOW() + INTERVAL '2 days'"
            ),
        ).mappings().all()
        for u in expiring:
            days_left = max(1, (u["trial_ends_at"] - datetime.now(timezone.utc)).days)
            try:
                from services.email_svc import send_trial_expiring_email
                send_trial_expiring_email(u["email"], u["name"] or "there", days_left)
                logger.info("Sent trial expiring email to user=%s days_left=%d", u["id"], days_left)
            except Exception:
                logger.exception("Failed trial expiring email for user=%s", u["id"])

        # Users whose trial expired today (within last 24h, not paid)
        expired = db.execute(
            text(
                "SELECT id, email, name FROM users "
                "WHERE has_paid = FALSE AND trial_ends_at IS NOT NULL "
                "AND trial_ends_at <= NOW() "
                "AND trial_ends_at > NOW() - INTERVAL '1 day'"
            ),
        ).mappings().all()
        for u in expired:
            try:
                from services.email_svc import send_trial_expired_email
                send_trial_expired_email(u["email"], u["name"] or "there")
                logger.info("Sent trial expired email to user=%s", u["id"])
            except Exception:
                logger.exception("Failed trial expired email for user=%s", u["id"])
    finally:
        db.close()


celery_app.conf.beat_schedule = {
    "poll-every-minute": {
        "task": "tasks.escalation.poll_and_fire",
        "schedule": crontab(minute="*"),
    },
    "activity-timer-check": {
        "task": "tasks.escalation.check_activity_timers",
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
    "check-dead-letters": {
        "task": "tasks.escalation.check_dead_letters",
        "schedule": crontab(hour="0", minute="0"),
    },
    "check-trial-expiry": {
        "task": "tasks.escalation.check_trial_expiry",
        "schedule": crontab(hour="10", minute="0"),
    },
}
