import logging
from datetime import date, datetime, timedelta, timezone

from jose import jwt

from config import settings

logger = logging.getLogger(__name__)


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
    if not settings.resend_api_key:
        logger.info("Resend not configured, skipping email to %s", to_email)
        return False

    token = _generate_checkin_token(user_id)
    checkin_url = f"{settings.base_url}/checkin/email/{token}"
    import resend

    resend.api_key = settings.resend_api_key
    try:
        resend.Emails.send(
            {
                "from": settings.email_from,
                "to": [to_email],
                "subject": "Still Here? Tap to check in",
                "html": f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:480px;margin:0 auto;padding:40px 20px;text-align:center;background:#0f0f1a;color:#eee">
  <h1 style="font-size:28px;font-weight:700;color:#4ecca3">Still Here?</h1>
  <p style="font-size:16px;line-height:1.6;opacity:.8">Hey {user_name}, it's time for your daily check-in. Tap below to confirm you're okay.</p>
  <a href="{checkin_url}" style="display:inline-block;padding:14px 32px;background:#4ecca3;color:#0f0f1a;text-decoration:none;border-radius:8px;font-weight:600;font-size:16px;margin:20px 0">I'm Still Here</a>
  <p style="font-size:13px;opacity:.5;margin-top:30px">This link expires in 24 hours.</p>
  <div style="font-size:12px;opacity:.3;letter-spacing:1px;margin-top:40px">STILL HERE</div>
</div>
""",
            }
        )
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False


def send_welcome_email(to_email: str, user_name: str):
    if not settings.resend_api_key:
        logger.info("Resend not configured, skipping welcome email to %s", to_email)
        return False
    import resend
    resend.api_key = settings.resend_api_key
    app_url = f"{settings.base_url}/app"
    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": "Welcome to Still Here — you're set up",
            "html": f"""
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
      <div style="font-size:13px;color:rgba(255,255,255,0.5);line-height:1.5">These are the people we'll alert if you miss a check-in. Add at least one.</div>
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
""",
        })
        return True
    except Exception:
        logger.exception("Failed to send welcome email to %s", to_email)
        return False


def send_contact_welcome_email(to_email: str, contact_name: str, user_name: str, portal_token: str):
    if not settings.resend_api_key:
        logger.info("Resend not configured, skipping contact welcome email to %s", to_email)
        return False
    import resend
    resend.api_key = settings.resend_api_key
    portal_url = f"{settings.base_url}/portal/{portal_token}" if portal_token else None
    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": f"{user_name} added you as their emergency contact",
            "html": f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:520px;margin:0 auto;background:#080808;color:#F5F5F5;border-radius:12px;overflow:hidden">
  <div style="background:#111;border-bottom:1px solid rgba(255,255,255,0.08);padding:28px 32px;text-align:center">
    <div style="font-size:22px;font-weight:800;color:#FF3B3B;letter-spacing:-0.5px">Still Here</div>
  </div>
  <div style="padding:36px 32px">
    <h1 style="font-size:22px;font-weight:700;color:#F5F5F5;margin:0 0 12px">Hey {contact_name},</h1>
    <p style="font-size:14px;color:rgba(255,255,255,0.55);line-height:1.6;margin:0 0 24px"><strong style="color:#F5F5F5">{user_name}</strong> has added you as an emergency contact on Still Here — a daily safety check-in app.</p>

    <div style="background:#161616;border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:24px;margin-bottom:24px">
      <div style="font-size:13px;font-weight:600;color:#F5F5F5;margin-bottom:12px">What this means for you</div>
      <div style="display:flex;flex-direction:column;gap:10px">
        <div style="font-size:13px;color:rgba(255,255,255,0.55);padding-left:16px;border-left:2px solid rgba(255,255,255,0.1)">
          {user_name} checks in every day with one tap.
        </div>
        <div style="font-size:13px;color:rgba(255,255,255,0.55);padding-left:16px;border-left:2px solid rgba(255,255,255,0.1)">
          If they miss a check-in and the grace period expires, <strong style="color:#F5F5F5">you'll receive an alert</strong> — by SMS, email, or push.
        </div>
        <div style="font-size:13px;color:rgba(255,255,255,0.55);padding-left:16px;border-left:2px solid rgba(255,255,255,0.1)">
          You'll be asked to confirm whether they're safe. That's it.
        </div>
        <div style="font-size:13px;color:rgba(255,255,255,0.55);padding-left:16px;border-left:2px solid rgba(255,255,255,0.1)">
          <strong style="color:#4ecca3">We will never call 911.</strong> A non-emergency welfare check is only ever the very last resort.
        </div>
      </div>
    </div>

    <p style="font-size:13px;color:rgba(255,255,255,0.4);line-height:1.6;margin-bottom:24px">Most days you'll hear nothing from us. You'll only ever hear from us if {user_name} needs help.</p>

    {f'<a href="{portal_url}" style="display:block;text-align:center;padding:14px 28px;background:#161616;color:#F5F5F5;text-decoration:none;border-radius:6px;font-size:14px;font-weight:600;border:1px solid rgba(255,255,255,0.12)">View {user_name}\'s Status →</a>' if portal_url else ""}
  </div>
  <div style="padding:20px 32px;text-align:center;border-top:1px solid rgba(255,255,255,0.06)">
    <div style="font-size:11px;color:rgba(255,255,255,0.2);letter-spacing:0.08em">STILL HERE · SOMEONE ALWAYS KNOWS</div>
  </div>
</div>
""",
        })
        return True
    except Exception:
        logger.exception("Failed to send contact welcome email to %s", to_email)
        return False


def send_password_reset_email(to_email: str, user_name: str, reset_token: str):
    if not settings.resend_api_key:
        logger.info("Resend not configured, skipping reset email to %s", to_email)
        return False
    import resend
    resend.api_key = settings.resend_api_key
    reset_url = f"{settings.base_url}/reset-password?token={reset_token}"
    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": "Reset your Still Here password",
            "html": f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:520px;margin:0 auto;background:#080808;color:#F5F5F5;border-radius:12px;overflow:hidden">
  <div style="background:#111;border-bottom:1px solid rgba(255,255,255,0.08);padding:28px 32px;text-align:center">
    <div style="font-size:22px;font-weight:800;color:#FF3B3B;letter-spacing:-0.5px">Still Here</div>
  </div>
  <div style="padding:36px 32px">
    <h1 style="font-size:22px;font-weight:700;color:#F5F5F5;margin:0 0 12px">Password reset</h1>
    <p style="font-size:14px;color:rgba(255,255,255,0.55);line-height:1.6;margin:0 0 28px">Hey {user_name}, we got a request to reset your password. Click the button below — this link expires in 1 hour.</p>
    <a href="{reset_url}" style="display:block;text-align:center;padding:14px 28px;background:#FF3B3B;color:#fff;text-decoration:none;border-radius:6px;font-size:14px;font-weight:600;margin-bottom:24px">Reset Password →</a>
    <p style="font-size:12px;color:rgba(255,255,255,0.3);line-height:1.6">If you didn't request this, you can safely ignore this email. Your password won't change.</p>
  </div>
  <div style="padding:20px 32px;text-align:center;border-top:1px solid rgba(255,255,255,0.06)">
    <div style="font-size:11px;color:rgba(255,255,255,0.2);letter-spacing:0.08em">STILL HERE · SOMEONE ALWAYS KNOWS</div>
  </div>
</div>
""",
        })
        return True
    except Exception:
        logger.exception("Failed to send reset email to %s", to_email)
        return False


def send_reengagement_email(to_email: str, user_name: str):
    if not settings.resend_api_key:
        logger.info("Resend not configured, skipping re-engagement email to %s", to_email)
        return False
    import resend
    resend.api_key = settings.resend_api_key
    try:
        resend.Emails.send({
            "from": settings.email_from,
            "to": [to_email],
            "subject": "We miss you — is everything okay?",
            "html": f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:480px;margin:0 auto;padding:40px 20px;text-align:center;background:#0f0f1a;color:#eee">
<h1 style="font-size:28px;font-weight:700;color:#5bc0de">Hey {user_name}</h1>
<p style="font-size:16px;line-height:1.6;opacity:.8">We haven't seen you in a while. Just a friendly check — is everything okay?</p>
<p style="font-size:14px;opacity:.6">If you're doing fine, just open the app to check in. Your safety matters.</p>
<p style="font-size:13px;opacity:.5;margin-top:20px">If you no longer want to use Still Here, you can ignore this email and your account will eventually be marked inactive.</p>
<div style="font-size:12px;opacity:.3;letter-spacing:1px;margin-top:40px">STILL HERE</div></div>""",
        })
        return True
    except Exception:
        logger.exception("Failed to send re-engagement email to %s", to_email)
        return False
