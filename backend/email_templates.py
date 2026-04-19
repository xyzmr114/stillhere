"""
Email template functions for Still Here.

All email HTML is centralized here. Templates use a consistent base layout
with the Still Here branding, header, and footer.
"""

from constants import (
    EMAIL_BRAND_PRIMARY,
    EMAIL_BRAND_SECONDARY,
    EMAIL_BACKGROUND_DARK,
    EMAIL_TEXT_PRIMARY,
    EMAIL_TEXT_SECONDARY,
    EMAIL_TEXT_TERTIARY,
    EMAIL_CARD_BACKGROUND,
    EMAIL_BORDER_COLOR,
    EMAIL_HEADER_BACKGROUND,
    EMAIL_FONT_STACK,
)


def base_email(content: str, brand_color: str = EMAIL_BRAND_PRIMARY) -> str:
    """
    Wraps content in the standard Still Here email chrome.

    Args:
        content: The main email content (inner HTML)
        brand_color: Hex color for header accent (default: red)

    Returns:
        Complete email HTML with header, content, and footer
    """
    return f"""<div style="font-family:{EMAIL_FONT_STACK};max-width:520px;margin:0 auto;background:{EMAIL_BACKGROUND_DARK};color:{EMAIL_TEXT_PRIMARY};border-radius:12px;overflow:hidden">
  <div style="background:{EMAIL_HEADER_BACKGROUND};border-bottom:1px solid {EMAIL_BORDER_COLOR};padding:28px 32px;text-align:center">
    <div style="font-size:22px;font-weight:800;color:{brand_color};letter-spacing:-0.5px">Still Here</div>
  </div>
  <div style="padding:36px 32px">
    {content}
  </div>
  <div style="padding:20px 32px;text-align:center;border-top:1px solid {EMAIL_BORDER_COLOR}">
    <div style="font-size:11px;color:rgba(255,255,255,0.2);letter-spacing:0.08em">STILL HERE · SOMEONE ALWAYS KNOWS</div>
  </div>
</div>"""


def checkin_reminder(user_name: str, checkin_url: str) -> str:
    """
    Email sent when user is due for daily check-in.

    Args:
        user_name: User's display name
        checkin_url: URL to complete check-in via email

    Returns:
        HTML email content
    """
    content = f"""<h1 style="font-size:22px;font-weight:700;color:{EMAIL_TEXT_PRIMARY};margin:0 0 12px">Still Here?</h1>
    <p style="font-size:14px;color:{EMAIL_TEXT_SECONDARY};line-height:1.6;margin:0 0 28px">Hey {user_name}, it's time for your daily check-in. Tap below to confirm you're okay.</p>
    <a href="{checkin_url}" style="display:block;text-align:center;padding:14px 28px;background:{EMAIL_BRAND_SECONDARY};color:#0f0f1a;text-decoration:none;border-radius:6px;font-size:14px;font-weight:600;margin-bottom:24px">I'm Still Here →</a>
    <p style="font-size:12px;color:{EMAIL_TEXT_TERTIARY};line-height:1.6">This link expires in 24 hours.</p>"""
    return base_email(content)


def welcome(user_name: str) -> str:
    """
    Onboarding email sent after successful signup.

    Args:
        user_name: User's display name

    Returns:
        HTML email content
    """
    from config import settings
    app_url = f"{settings.base_url}/app"
    content = f"""<h1 style="font-size:24px;font-weight:700;color:{EMAIL_TEXT_PRIMARY};margin:0 0 8px">Welcome, {user_name}.</h1>
    <p style="font-size:14px;color:{EMAIL_TEXT_SECONDARY};line-height:1.6;margin:0 0 28px">You're all set up. Here's how to make Still Here actually work for you.</p>
    <div style="background:{EMAIL_CARD_BACKGROUND};border:1px solid {EMAIL_BORDER_COLOR};border-radius:10px;padding:20px 24px;margin-bottom:16px">
      <div style="font-size:11px;color:{EMAIL_BRAND_PRIMARY};letter-spacing:0.15em;text-transform:uppercase;margin-bottom:10px">Step 1</div>
      <div style="font-size:14px;font-weight:600;color:{EMAIL_TEXT_PRIMARY};margin-bottom:4px">Add your emergency contacts</div>
      <div style="font-size:13px;color:rgba(255,255,255,0.5);line-height:1.5">These are the people we'll alert if you miss a check-in.</div>
    </div>
    <div style="background:{EMAIL_CARD_BACKGROUND};border:1px solid {EMAIL_BORDER_COLOR};border-radius:10px;padding:20px 24px;margin-bottom:16px">
      <div style="font-size:11px;color:{EMAIL_BRAND_PRIMARY};letter-spacing:0.15em;text-transform:uppercase;margin-bottom:10px">Step 2</div>
      <div style="font-size:14px;font-weight:600;color:{EMAIL_TEXT_PRIMARY};margin-bottom:4px">Set your check-in time</div>
      <div style="font-size:13px;color:rgba(255,255,255,0.5);line-height:1.5">Pick a time you'll reliably be awake. 9 AM is a good default.</div>
    </div>
    <div style="background:{EMAIL_CARD_BACKGROUND};border:1px solid {EMAIL_BORDER_COLOR};border-radius:10px;padding:20px 24px;margin-bottom:28px">
      <div style="font-size:11px;color:{EMAIL_BRAND_PRIMARY};letter-spacing:0.15em;text-transform:uppercase;margin-bottom:10px">Step 3</div>
      <div style="font-size:14px;font-weight:600;color:{EMAIL_TEXT_PRIMARY};margin-bottom:4px">Check in tomorrow</div>
      <div style="font-size:13px;color:rgba(255,255,255,0.5);line-height:1.5">We'll send a push, email, or SMS. One tap. Done.</div>
    </div>
    <a href="{app_url}" style="display:block;text-align:center;padding:14px 28px;background:{EMAIL_BRAND_PRIMARY};color:#fff;text-decoration:none;border-radius:6px;font-size:14px;font-weight:600">Open the App →</a>"""
    return base_email(content)


def verification(user_name: str, verify_url: str) -> str:
    """
    Email verification message sent during signup.

    Args:
        user_name: User's display name
        verify_url: URL to verify email address

    Returns:
        HTML email content
    """
    content = f"""<h1 style="font-size:22px;font-weight:700;color:{EMAIL_TEXT_PRIMARY};margin:0 0 12px">Verify your email</h1>
    <p style="font-size:14px;color:{EMAIL_TEXT_SECONDARY};line-height:1.6;margin:0 0 28px">Hey {user_name}, tap below to verify your email address. This link expires in 48 hours.</p>
    <a href="{verify_url}" style="display:block;text-align:center;padding:14px 28px;background:{EMAIL_BRAND_PRIMARY};color:#fff;text-decoration:none;border-radius:6px;font-size:14px;font-weight:600;margin-bottom:24px">Verify Email →</a>
    <p style="font-size:12px;color:{EMAIL_TEXT_TERTIARY};line-height:1.6">If you didn't create a Still Here account, ignore this email.</p>"""
    return base_email(content)


def password_reset(user_name: str, reset_url: str) -> str:
    """
    Password reset email sent when user requests account recovery.

    Args:
        user_name: User's display name
        reset_url: URL to reset password

    Returns:
        HTML email content
    """
    content = f"""<h1 style="font-size:22px;font-weight:700;color:{EMAIL_TEXT_PRIMARY};margin:0 0 12px">Password reset</h1>
    <p style="font-size:14px;color:{EMAIL_TEXT_SECONDARY};line-height:1.6;margin:0 0 28px">Hey {user_name}, we got a request to reset your password. This link expires in 1 hour.</p>
    <a href="{reset_url}" style="display:block;text-align:center;padding:14px 28px;background:{EMAIL_BRAND_PRIMARY};color:#fff;text-decoration:none;border-radius:6px;font-size:14px;font-weight:600;margin-bottom:24px">Reset Password →</a>
    <p style="font-size:12px;color:{EMAIL_TEXT_TERTIARY};line-height:1.6">If you didn't request this, ignore this email.</p>"""
    return base_email(content)


def contact_alert(user_name: str, confirm_url: str) -> str:
    """
    Emergency alert sent to emergency contacts when user misses check-in.

    Args:
        user_name: User who missed check-in
        confirm_url: URL for contact to confirm user is safe

    Returns:
        HTML email content
    """
    content = f"""<h1 style="font-size:22px;font-weight:700;color:{EMAIL_TEXT_PRIMARY};margin:0 0 12px">Emergency Alert</h1>
    <p style="font-size:14px;color:{EMAIL_TEXT_SECONDARY};line-height:1.6;margin:0 0 28px">{user_name} has missed their daily check-in. Please try to contact them to make sure they're okay.</p>
    <a href="{confirm_url}" style="display:block;text-align:center;padding:14px 28px;background:{EMAIL_BRAND_PRIMARY};color:#fff;text-decoration:none;border-radius:6px;font-size:14px;font-weight:600;margin-bottom:24px">Confirm They're Safe →</a>
    <p style="font-size:12px;color:{EMAIL_TEXT_TERTIARY};line-height:1.6">If you've already confirmed they're safe, you can ignore this message.</p>"""
    return base_email(content)


def weekly_digest(user_name: str, count: int) -> str:
    """
    Weekly check-in report sent to user every Monday.

    Args:
        user_name: User's display name
        count: Number of check-ins completed this week (out of 7)

    Returns:
        HTML email content
    """
    content = f"""<h1 style="font-size:28px;font-weight:700;color:{EMAIL_BRAND_SECONDARY}">Weekly Report</h1>
    <p style="font-size:16px;line-height:1.6;opacity:.8">Hey {user_name}, you checked in <strong>{count}/7</strong> days this week.</p>
    <p style="font-size:14px;opacity:.6">Keep going — someone always knows you're here.</p>
    <div style="font-size:12px;opacity:.3;letter-spacing:1px;margin-top:40px">STILL HERE</div>"""
    # Use simpler template for weekly digest (different styling)
    return f"""<div style="font-family:{EMAIL_FONT_STACK};max-width:480px;margin:0 auto;padding:40px 20px;text-align:center;background:#0f0f1a;color:#eee">
    {content}
    </div>"""


def reengagement(user_name: str) -> str:
    """
    Reengagement email sent to inactive users (14+ days no activity).

    Args:
        user_name: User's display name

    Returns:
        HTML email content
    """
    content = f"""<h1 style="font-size:28px;font-weight:700;color:#5bc0de">Hey {user_name}</h1>
    <p style="font-size:16px;line-height:1.6;opacity:.8">We haven't seen you in a while. Just a friendly check — is everything okay?</p>
    <p style="font-size:14px;opacity:.6">If you're doing fine, just open the app to check in.</p>
    <div style="font-size:12px;opacity:.3;letter-spacing:1px;margin-top:40px">STILL HERE</div>"""
    # Use simpler template for reengagement (different styling)
    return f"""<div style="font-family:{EMAIL_FONT_STACK};max-width:480px;margin:0 auto;padding:40px 20px;text-align:center;background:#0f0f1a;color:#eee">
    {content}
    </div>"""


def contact_welcome(contact_name: str, user_name: str, portal_url: str | None = None) -> str:
    """
    Welcome email sent to emergency contact when added by user.

    Args:
        contact_name: Contact's display name
        user_name: User who added the contact
        portal_url: Optional URL for contact to view user's status

    Returns:
        HTML email content
    """
    portal_btn = f'<a href="{portal_url}" style="display:block;text-align:center;padding:14px 28px;background:{EMAIL_CARD_BACKGROUND};color:{EMAIL_TEXT_PRIMARY};text-decoration:none;border-radius:6px;font-size:14px;font-weight:600;border:1px solid {EMAIL_BORDER_COLOR}">View {user_name}\'s Status →</a>' if portal_url else ""

    content = f"""<h1 style="font-size:22px;font-weight:700;color:{EMAIL_TEXT_PRIMARY};margin:0 0 12px">Hey {contact_name},</h1>
    <p style="font-size:14px;color:{EMAIL_TEXT_SECONDARY};line-height:1.6;margin:0 0 24px"><strong style="color:{EMAIL_TEXT_PRIMARY}">{user_name}</strong> has added you as an emergency contact on Still Here — a daily safety check-in app.</p>
    <div style="background:{EMAIL_CARD_BACKGROUND};border:1px solid {EMAIL_BORDER_COLOR};border-radius:10px;padding:24px;margin-bottom:24px">
      <div style="font-size:13px;font-weight:600;color:{EMAIL_TEXT_PRIMARY};margin-bottom:12px">What this means for you</div>
      <div style="font-size:13px;color:{EMAIL_TEXT_SECONDARY};padding-left:16px;border-left:2px solid {EMAIL_BORDER_COLOR};margin-bottom:8px">{user_name} checks in every day with one tap.</div>
      <div style="font-size:13px;color:{EMAIL_TEXT_SECONDARY};padding-left:16px;border-left:2px solid {EMAIL_BORDER_COLOR};margin-bottom:8px">If they miss a check-in, <strong style="color:{EMAIL_TEXT_PRIMARY}">you'll receive an alert</strong> — by SMS, email, or push.</div>
      <div style="font-size:13px;color:{EMAIL_TEXT_SECONDARY};padding-left:16px;border-left:2px solid {EMAIL_BORDER_COLOR};margin-bottom:8px">You'll be asked to confirm whether they're safe. That's it.</div>
      <div style="font-size:13px;color:{EMAIL_TEXT_SECONDARY};padding-left:16px;border-left:2px solid {EMAIL_BORDER_COLOR}"><strong style="color:{EMAIL_BRAND_SECONDARY}">We will never call 911.</strong> A non-emergency welfare check is only ever the very last resort.</div>
    </div>
    <p style="font-size:13px;color:rgba(255,255,255,0.4);line-height:1.6;margin-bottom:24px">Most days you'll hear nothing from us.</p>
    {portal_btn}"""
    return base_email(content)
