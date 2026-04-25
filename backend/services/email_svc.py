import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date, datetime, timedelta, timezone

from jose import jwt

from config import settings
from constants import (
    VERIFICATION_TOKEN_EXPIRATION_HOURS,
    CHECKIN_TOKEN_EXPIRATION_HOURS,
    PASSWORD_RESET_TOKEN_EXPIRATION_HOURS,
)
from email_templates import (
    verification,
    checkin_reminder,
    welcome,
    password_reset,
    contact_welcome,
    weekly_digest,
    reengagement,
)

logger = logging.getLogger(__name__)


def _send_email(to_email: str, subject: str, html: str) -> bool:
    provider = settings.email_provider.lower()
    if provider == "smtp" or (not settings.resend_api_key and settings.smtp_host):
        return _send_smtp(to_email, subject, html)
    if settings.resend_api_key:
        return _send_resend(to_email, subject, html)
    logger.info("No email provider configured — skipping email to %s", to_email)
    return False


def _send_resend(to_email: str, subject: str, html: str) -> bool:
    try:
        import resend
        resend.api_key = settings.resend_api_key
        resend.Emails.send({"from": settings.email_from, "to": [to_email], "subject": subject, "html": html})
        return True
    except Exception:
        logger.exception("Resend failed for %s", to_email)
        return False


_SMTP_PRESETS = {
    "brevo":    {"host": "smtp-relay.brevo.com",  "port": 587, "ssl": False, "tls": True},
    "resend":   {"host": "smtp.resend.com",        "port": 465, "ssl": True,  "tls": False},
    "gmail":    {"host": "smtp.gmail.com",         "port": 587, "ssl": False, "tls": True},
    "mailgun":  {"host": "smtp.mailgun.org",       "port": 587, "ssl": False, "tls": True},
    "mailjet":  {"host": "in-v3.mailjet.com",      "port": 587, "ssl": False, "tls": True},
    "sendgrid": {"host": "smtp.sendgrid.net",      "port": 587, "ssl": False, "tls": True},
    "zoho":     {"host": "smtp.zoho.com",          "port": 587, "ssl": False, "tls": True},
    "cpanel":   {"host": "mail.stillherehq.com",    "port": 587, "ssl": False, "tls": True},
    "local":    {"host": "localhost",              "port": 25,  "ssl": False, "tls": False},
}


def _resolve_smtp_config():
    preset_name = getattr(settings, "smtp_preset", "").lower()
    preset = _SMTP_PRESETS.get(preset_name, {})
    host = settings.smtp_host or preset.get("host", "")
    port = settings.smtp_port if settings.smtp_port != 587 else preset.get("port", 587)
    use_ssl = preset.get("ssl", False)
    use_tls = settings.smtp_tls if not preset else preset.get("tls", True)
    return host, port, use_ssl, use_tls


def _send_smtp(to_email: str, subject: str, html: str) -> bool:
    host, port, use_ssl, use_tls = _resolve_smtp_config()
    if not host:
        logger.warning("SMTP not configured — skipping email to %s", to_email)
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.email_from
        msg["To"] = to_email
        msg.attach(MIMEText(html, "html"))
        if use_ssl:
            import ssl as _ssl
            ctx = _ssl.create_default_context()
            server_cls = smtplib.SMTP_SSL(host, port, context=ctx)
        else:
            server_cls = smtplib.SMTP(host, port)
        with server_cls as server:
            if use_tls and not use_ssl:
                server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.email_from, to_email, msg.as_string())
        logger.info("SMTP email sent to %s via %s:%s", to_email, host, port)
        return True
    except Exception:
        logger.exception("SMTP failed for %s (host=%s)", to_email, host)
        return False


def _generate_verification_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "verify",
        "exp": datetime.now(timezone.utc) + timedelta(hours=VERIFICATION_TOKEN_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_verification_token(token: str):
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        if payload.get("type") != "verify":
            return None
        return payload
    except Exception:
        return None


def send_verification_email(to_email: str, user_name: str, user_id: str):
    token = _generate_verification_token(user_id)
    verify_url = f"{settings.base_url}/users/verify-email?token={token}"
    html = verification(user_name, verify_url)
    return _send_email(to_email, "Verify your Still Here email", html)


def _generate_checkin_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "date": date.today().isoformat(),
        "exp": datetime.now(timezone.utc) + timedelta(hours=CHECKIN_TOKEN_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_checkin_token(token: str):
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload
    except Exception:
        return None


def send_checkin_email(to_email: str, user_name: str, user_id: str):
    token = _generate_checkin_token(user_id)
    checkin_url = f"{settings.base_url}/checkin/email/{token}"
    html = checkin_reminder(user_name, checkin_url)
    return _send_email(to_email, "Still Here? Tap to check in", html)


def send_welcome_email(to_email: str, user_name: str):
    html = welcome(user_name)
    return _send_email(to_email, "Welcome to Still Here — you're set up", html)


def send_payment_confirmation_email(to_email: str, user_name: str):
    from email_templates import payment_confirmation
    html = payment_confirmation(user_name, to_email)
    return _send_email(to_email, "Payment confirmed — Still Here is yours", html)


def send_trial_expiring_email(to_email: str, user_name: str, days_left: int):
    from email_templates import trial_expiring
    html = trial_expiring(user_name, days_left)
    subject = "Your Still Here trial ends tomorrow" if days_left <= 1 else f"Your Still Here trial ends in {days_left} days"
    return _send_email(to_email, subject, html)


def send_trial_expired_email(to_email: str, user_name: str):
    from email_templates import trial_expired
    html = trial_expired(user_name)
    return _send_email(to_email, "Your Still Here trial has ended", html)


def send_contact_welcome_email(to_email: str, contact_name: str, user_name: str, portal_token: str):
    portal_url = f"{settings.base_url}/portal/{portal_token}" if portal_token else None
    html = contact_welcome(contact_name, user_name, portal_url)
    return _send_email(to_email, f"{user_name} added you as their emergency contact", html)


def send_password_reset_email(to_email: str, user_name: str, reset_token: str):
    reset_url = f"{settings.base_url}/reset-password?token={reset_token}"
    html = password_reset(user_name, reset_url)
    return _send_email(to_email, "Reset your Still Here password", html)


def send_reengagement_email(to_email: str, user_name: str):
    html = reengagement(user_name)
    return _send_email(to_email, "We miss you — is everything okay?", html)
