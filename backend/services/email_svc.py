import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date, datetime, timedelta, timezone

from jose import jwt

from config import settings

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
    "cpanel":   {"host": "mail.yourdomain.com",    "port": 587, "ssl": False, "tls": True},
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


def _generate_checkin_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "date": date.today().isoformat(),
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
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
    return _send_email(to_email, "Still Here? Tap to check in", f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:480px;margin:0 auto;padding:40px 20px;text-align:center;background:#0f0f1a;color:#eee">
  <h1 style="font-size:28px;font-weight:700;color:#4ecca3">Still Here?</h1>
  <p style="font-size:16px;line-height:1.6;opacity:.8">Hey {user_name}, it's time for your daily check-in. Tap below to confirm you're okay.</p>
  <a href="{checkin_url}" style="display:inline-block;padding:14px 32px;background:#4ecca3;color:#0f0f1a;text-decoration:none;border-radius:8px;font-weight:600;font-size:16px;margin:20px 0">I'm Still Here</a>
  <p style="font-size:13px;opacity:.5;margin-top:30px">This link expires in 24 hours.</p>
  <div style="font-size:12px;opacity:.3;letter-spacing:1px;margin-top:40px">STILL HERE</div>
</div>
""")


def send_welcome_email(to_email: str, user_name: str):
    app_url = f"{settings.base_url}/app"
    return _send_email(to_email, "Welcome to Still Here — you're set up", f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:520px;margin:0 auto;background:#080808;color:#F5F5F5;border-radius:12px;overflow:hidden">
  <div style="background:#111;border-bottom:1px solid rgba(255,255,255,0.08);padding:28px 32px;text-align:center">
    <div style="font-size:22px;font-weight:800;color:#FF3B3B;letter-spacing:-0.5px">Still Here</div>
  </div>
  <div style="padding:36px 32px">
    <h1 style="font-size:24px;font-weight:700;color:#F5F5F5;margin:0 0 8px">Welcome, {user_name}.</h1>
    <p style="font-size:14px;color:rgba(255,255,255,0.55);line-height:1.6;margin:0 0 28px">You're all set up. Here's how to make Still Here actually work for you.</p>
    <div style="background:#161616;border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:20px 24px;margin-bottom:16px">
      <div style="font-size:11px;color:#FF3B3B;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:10px">Step 1</div>
      <div style="font-size:14px;font-weight:600;color:#F5F5F5;margin-bottom:4px">Add your emergency contacts</div>
      <div style="font-size:13px;color:rgba(255,255,255,0.5);line-height:1.5">These are the people we'll alert if you miss a check-in.</div>
    </div>
    <div style="background:#161616;border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:20px 24px;margin-bottom:16px">
      <div style="font-size:11px;color:#FF3B3B;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:10px">Step 2</div>
      <div style="font-size:14px;font-weight:600;color:#F5F5F5;margin-bottom:4px">Set your check-in time</div>
      <div style="font-size:13px;color:rgba(255,255,255,0.5);line-height:1.5">Pick a time you'll reliably be awake. 9 AM is a good default.</div>
    </div>
    <div style="background:#161616;border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:20px 24px;margin-bottom:28px">
      <div style="font-size:11px;color:#FF3B3B;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:10px">Step 3</div>
      <div style="font-size:14px;font-weight:600;color:#F5F5F5;margin-bottom:4px">Check in tomorrow</div>
      <div style="font-size:13px;color:rgba(255,255,255,0.5);line-height:1.5">We'll send a push, email, or SMS. One tap. Done.</div>
    </div>
    <a href="{app_url}" style="display:block;text-align:center;padding:14px 28px;background:#FF3B3B;color:#fff;text-decoration:none;border-radius:6px;font-size:14px;font-weight:600">Open the App →</a>
  </div>
  <div style="padding:20px 32px;text-align:center;border-top:1px solid rgba(255,255,255,0.06)">
    <div style="font-size:11px;color:rgba(255,255,255,0.2);letter-spacing:0.08em">STILL HERE · SOMEONE ALWAYS KNOWS</div>
  </div>
</div>
""")


def send_contact_welcome_email(to_email: str, contact_name: str, user_name: str, portal_token: str):
    portal_url = f"{settings.base_url}/portal/{portal_token}" if portal_token else None
    portal_btn = f'<a href="{portal_url}" style="display:block;text-align:center;padding:14px 28px;background:#161616;color:#F5F5F5;text-decoration:none;border-radius:6px;font-size:14px;font-weight:600;border:1px solid rgba(255,255,255,0.12)">View {user_name}\'s Status →</a>' if portal_url else ""
    return _send_email(to_email, f"{user_name} added you as their emergency contact", f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:520px;margin:0 auto;background:#080808;color:#F5F5F5;border-radius:12px;overflow:hidden">
  <div style="background:#111;border-bottom:1px solid rgba(255,255,255,0.08);padding:28px 32px;text-align:center">
    <div style="font-size:22px;font-weight:800;color:#FF3B3B;letter-spacing:-0.5px">Still Here</div>
  </div>
  <div style="padding:36px 32px">
    <h1 style="font-size:22px;font-weight:700;color:#F5F5F5;margin:0 0 12px">Hey {contact_name},</h1>
    <p style="font-size:14px;color:rgba(255,255,255,0.55);line-height:1.6;margin:0 0 24px"><strong style="color:#F5F5F5">{user_name}</strong> has added you as an emergency contact on Still Here — a daily safety check-in app.</p>
    <div style="background:#161616;border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:24px;margin-bottom:24px">
      <div style="font-size:13px;font-weight:600;color:#F5F5F5;margin-bottom:12px">What this means for you</div>
      <div style="font-size:13px;color:rgba(255,255,255,0.55);padding-left:16px;border-left:2px solid rgba(255,255,255,0.1);margin-bottom:8px">{user_name} checks in every day with one tap.</div>
      <div style="font-size:13px;color:rgba(255,255,255,0.55);padding-left:16px;border-left:2px solid rgba(255,255,255,0.1);margin-bottom:8px">If they miss a check-in, <strong style="color:#F5F5F5">you'll receive an alert</strong> — by SMS, email, or push.</div>
      <div style="font-size:13px;color:rgba(255,255,255,0.55);padding-left:16px;border-left:2px solid rgba(255,255,255,0.1);margin-bottom:8px">You'll be asked to confirm whether they're safe. That's it.</div>
      <div style="font-size:13px;color:rgba(255,255,255,0.55);padding-left:16px;border-left:2px solid rgba(255,255,255,0.1)"><strong style="color:#4ecca3">We will never call 911.</strong> A non-emergency welfare check is only ever the very last resort.</div>
    </div>
    <p style="font-size:13px;color:rgba(255,255,255,0.4);line-height:1.6;margin-bottom:24px">Most days you'll hear nothing from us.</p>
    {portal_btn}
  </div>
  <div style="padding:20px 32px;text-align:center;border-top:1px solid rgba(255,255,255,0.06)">
    <div style="font-size:11px;color:rgba(255,255,255,0.2);letter-spacing:0.08em">STILL HERE · SOMEONE ALWAYS KNOWS</div>
  </div>
</div>
""")


def send_password_reset_email(to_email: str, user_name: str, reset_token: str):
    reset_url = f"{settings.base_url}/reset-password?token={reset_token}"
    return _send_email(to_email, "Reset your Still Here password", f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:520px;margin:0 auto;background:#080808;color:#F5F5F5;border-radius:12px;overflow:hidden">
  <div style="background:#111;border-bottom:1px solid rgba(255,255,255,0.08);padding:28px 32px;text-align:center">
    <div style="font-size:22px;font-weight:800;color:#FF3B3B;letter-spacing:-0.5px">Still Here</div>
  </div>
  <div style="padding:36px 32px">
    <h1 style="font-size:22px;font-weight:700;color:#F5F5F5;margin:0 0 12px">Password reset</h1>
    <p style="font-size:14px;color:rgba(255,255,255,0.55);line-height:1.6;margin:0 0 28px">Hey {user_name}, we got a request to reset your password. This link expires in 1 hour.</p>
    <a href="{reset_url}" style="display:block;text-align:center;padding:14px 28px;background:#FF3B3B;color:#fff;text-decoration:none;border-radius:6px;font-size:14px;font-weight:600;margin-bottom:24px">Reset Password →</a>
    <p style="font-size:12px;color:rgba(255,255,255,0.3);line-height:1.6">If you didn't request this, ignore this email.</p>
  </div>
  <div style="padding:20px 32px;text-align:center;border-top:1px solid rgba(255,255,255,0.06)">
    <div style="font-size:11px;color:rgba(255,255,255,0.2);letter-spacing:0.08em">STILL HERE · SOMEONE ALWAYS KNOWS</div>
  </div>
</div>
""")


def send_reengagement_email(to_email: str, user_name: str):
    return _send_email(to_email, "We miss you — is everything okay?", f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:480px;margin:0 auto;padding:40px 20px;text-align:center;background:#0f0f1a;color:#eee">
  <h1 style="font-size:28px;font-weight:700;color:#5bc0de">Hey {user_name}</h1>
  <p style="font-size:16px;line-height:1.6;opacity:.8">We haven't seen you in a while. Just a friendly check — is everything okay?</p>
  <p style="font-size:14px;opacity:.6">If you're doing fine, just open the app to check in.</p>
  <div style="font-size:12px;opacity:.3;letter-spacing:1px;margin-top:40px">STILL HERE</div>
</div>
""")
