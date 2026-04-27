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
    app_url = f"{settings.base_url}/signin"
    content = f"""<div style="text-align:center;margin-bottom:28px">
      <div style="font-size:48px;margin-bottom:12px">&#x1F6E1;&#xFE0F;</div>
      <h1 style="font-size:26px;font-weight:700;color:{EMAIL_TEXT_PRIMARY};margin:0 0 6px">Welcome, {user_name}.</h1>
      <p style="font-size:14px;color:{EMAIL_TEXT_SECONDARY};margin:0">Your account is live. Three steps to get fully set up.</p>
    </div>
    <div style="background:{EMAIL_CARD_BACKGROUND};border:1px solid {EMAIL_BORDER_COLOR};border-radius:10px;padding:20px 24px;margin-bottom:12px;display:flex;align-items:flex-start;gap:16px">
      <div style="flex-shrink:0;width:32px;height:32px;border-radius:50%;background:rgba(233,69,96,0.12);display:flex;align-items:center;justify-content:center;color:{EMAIL_BRAND_PRIMARY};font-weight:700;font-size:14px">1</div>
      <div>
        <div style="font-size:14px;font-weight:600;color:{EMAIL_TEXT_PRIMARY};margin-bottom:4px">Add your emergency contacts</div>
        <div style="font-size:13px;color:rgba(255,255,255,0.5);line-height:1.5">The people we'll alert if you miss a check-in. They'll get a heads-up email.</div>
      </div>
    </div>
    <div style="background:{EMAIL_CARD_BACKGROUND};border:1px solid {EMAIL_BORDER_COLOR};border-radius:10px;padding:20px 24px;margin-bottom:12px;display:flex;align-items:flex-start;gap:16px">
      <div style="flex-shrink:0;width:32px;height:32px;border-radius:50%;background:rgba(233,69,96,0.12);display:flex;align-items:center;justify-content:center;color:{EMAIL_BRAND_PRIMARY};font-weight:700;font-size:14px">2</div>
      <div>
        <div style="font-size:14px;font-weight:600;color:{EMAIL_TEXT_PRIMARY};margin-bottom:4px">Set your check-in time</div>
        <div style="font-size:13px;color:rgba(255,255,255,0.5);line-height:1.5">Pick a time you'll reliably be awake. Default is 9 AM your timezone.</div>
      </div>
    </div>
    <div style="background:{EMAIL_CARD_BACKGROUND};border:1px solid {EMAIL_BORDER_COLOR};border-radius:10px;padding:20px 24px;margin-bottom:28px;display:flex;align-items:flex-start;gap:16px">
      <div style="flex-shrink:0;width:32px;height:32px;border-radius:50%;background:rgba(233,69,96,0.12);display:flex;align-items:center;justify-content:center;color:{EMAIL_BRAND_PRIMARY};font-weight:700;font-size:14px">3</div>
      <div>
        <div style="font-size:14px;font-weight:600;color:{EMAIL_TEXT_PRIMARY};margin-bottom:4px">Check in tomorrow</div>
        <div style="font-size:13px;color:rgba(255,255,255,0.5);line-height:1.5">Push, email, or SMS — one tap, done. Miss it and we start the escalation chain.</div>
      </div>
    </div>
    <a href="{app_url}" style="display:block;text-align:center;padding:14px 28px;background:{EMAIL_BRAND_PRIMARY};color:#fff;text-decoration:none;border-radius:6px;font-size:14px;font-weight:600">Open Still Here →</a>
    <p style="font-size:12px;color:{EMAIL_TEXT_TERTIARY};text-align:center;margin-top:16px;line-height:1.6">Questions? Reply to this email or reach us at <a href="mailto:hello@stillherehq.com" style="color:{EMAIL_BRAND_PRIMARY};text-decoration:none">hello@stillherehq.com</a></p>"""
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


def payment_confirmation(user_name: str, email: str) -> str:
    """
    Payment confirmation email sent after successful Stripe payment.

    Args:
        user_name: User's display name
        email: User's email (for receipt reference)

    Returns:
        HTML email content
    """
    from config import settings
    app_url = f"{settings.base_url}/signin"
    content = f"""<div style="text-align:center;margin-bottom:28px">
      <div style="font-size:48px;margin-bottom:12px">&#x2705;</div>
      <h1 style="font-size:26px;font-weight:700;color:{EMAIL_BRAND_SECONDARY};margin:0 0 6px">Payment confirmed</h1>
      <p style="font-size:14px;color:{EMAIL_TEXT_SECONDARY};margin:0">You're all set, {user_name}.</p>
    </div>
    <div style="background:{EMAIL_CARD_BACKGROUND};border:1px solid {EMAIL_BORDER_COLOR};border-radius:10px;padding:24px;margin-bottom:24px">
      <table style="width:100%;border-collapse:collapse">
        <tr>
          <td style="font-size:13px;color:{EMAIL_TEXT_SECONDARY};padding:8px 0;border-bottom:1px solid {EMAIL_BORDER_COLOR}">Item</td>
          <td style="font-size:13px;color:{EMAIL_TEXT_PRIMARY};padding:8px 0;border-bottom:1px solid {EMAIL_BORDER_COLOR};text-align:right;font-weight:600">Still Here — Lifetime Access</td>
        </tr>
        <tr>
          <td style="font-size:13px;color:{EMAIL_TEXT_SECONDARY};padding:8px 0;border-bottom:1px solid {EMAIL_BORDER_COLOR}">Amount</td>
          <td style="font-size:13px;color:{EMAIL_BRAND_SECONDARY};padding:8px 0;border-bottom:1px solid {EMAIL_BORDER_COLOR};text-align:right;font-weight:600">$5.00 USD</td>
        </tr>
        <tr>
          <td style="font-size:13px;color:{EMAIL_TEXT_SECONDARY};padding:8px 0;border-bottom:1px solid {EMAIL_BORDER_COLOR}">Type</td>
          <td style="font-size:13px;color:{EMAIL_TEXT_PRIMARY};padding:8px 0;border-bottom:1px solid {EMAIL_BORDER_COLOR};text-align:right">One-time payment</td>
        </tr>
        <tr>
          <td style="font-size:13px;color:{EMAIL_TEXT_SECONDARY};padding:8px 0">Account</td>
          <td style="font-size:13px;color:{EMAIL_TEXT_PRIMARY};padding:8px 0;text-align:right">{email}</td>
        </tr>
      </table>
    </div>
    <p style="font-size:13px;color:{EMAIL_TEXT_SECONDARY};line-height:1.7;margin-bottom:24px">No subscriptions. No renewals. You own this forever. If you ever need help, reply to this email or reach us at <a href="mailto:hello@stillherehq.com" style="color:{EMAIL_BRAND_PRIMARY};text-decoration:none">hello@stillherehq.com</a>.</p>
    <a href="{app_url}" style="display:block;text-align:center;padding:14px 28px;background:{EMAIL_BRAND_PRIMARY};color:#fff;text-decoration:none;border-radius:6px;font-size:14px;font-weight:600">Open Still Here →</a>"""
    return base_email(content, brand_color=EMAIL_BRAND_SECONDARY)


def trial_expiring(user_name: str, days_left: int) -> str:
    """
    Email sent when trial is about to expire (1-2 days left).

    Args:
        user_name: User's display name
        days_left: Number of days remaining in trial

    Returns:
        HTML email content
    """
    from config import settings
    app_url = f"{settings.base_url}/signin"
    urgency = "tomorrow" if days_left <= 1 else f"in {days_left} days"
    content = f"""<div style="text-align:center;margin-bottom:28px">
      <div style="font-size:48px;margin-bottom:12px">&#x23F3;</div>
      <h1 style="font-size:24px;font-weight:700;color:{EMAIL_TEXT_PRIMARY};margin:0 0 6px">Your trial ends {urgency}</h1>
      <p style="font-size:14px;color:{EMAIL_TEXT_SECONDARY};margin:0">{user_name}, your free trial is almost up.</p>
    </div>
    <div style="background:{EMAIL_CARD_BACKGROUND};border:1px solid {EMAIL_BORDER_COLOR};border-radius:10px;padding:24px;margin-bottom:24px">
      <p style="font-size:14px;color:{EMAIL_TEXT_SECONDARY};line-height:1.7;margin:0">When your trial ends, check-in reminders and escalation alerts stop firing. Your contacts won't be notified if you miss a check-in.</p>
    </div>
    <p style="font-size:13px;color:{EMAIL_TEXT_SECONDARY};line-height:1.7;margin-bottom:24px;text-align:center"><strong style="color:{EMAIL_BRAND_SECONDARY}">$5, one time, forever.</strong> No subscriptions. No renewals.</p>
    <a href="{app_url}" style="display:block;text-align:center;padding:14px 28px;background:{EMAIL_BRAND_PRIMARY};color:#fff;text-decoration:none;border-radius:6px;font-size:14px;font-weight:600;margin-bottom:12px">Upgrade Now →</a>
    <p style="font-size:12px;color:{EMAIL_TEXT_TERTIARY};text-align:center;line-height:1.6">Reply to this email if you have questions.</p>"""
    return base_email(content)


def trial_expired(user_name: str) -> str:
    """
    Email sent when trial has expired.

    Args:
        user_name: User's display name

    Returns:
        HTML email content
    """
    from config import settings
    app_url = f"{settings.base_url}/signin"
    content = f"""<div style="text-align:center;margin-bottom:28px">
      <div style="font-size:48px;margin-bottom:12px">&#x1F6D1;</div>
      <h1 style="font-size:24px;font-weight:700;color:{EMAIL_TEXT_PRIMARY};margin:0 0 6px">Your trial has ended</h1>
      <p style="font-size:14px;color:{EMAIL_TEXT_SECONDARY};margin:0">{user_name}, your safety net is paused.</p>
    </div>
    <div style="background:{EMAIL_CARD_BACKGROUND};border:1px solid {EMAIL_BORDER_COLOR};border-radius:10px;padding:24px;margin-bottom:24px">
      <p style="font-size:14px;color:{EMAIL_TEXT_SECONDARY};line-height:1.7;margin:0 0 12px">Here's what stopped:</p>
      <div style="font-size:13px;color:{EMAIL_TEXT_SECONDARY};padding-left:16px;border-left:2px solid {EMAIL_BRAND_PRIMARY};margin-bottom:8px">Daily check-in reminders</div>
      <div style="font-size:13px;color:{EMAIL_TEXT_SECONDARY};padding-left:16px;border-left:2px solid {EMAIL_BRAND_PRIMARY};margin-bottom:8px">SMS and push notifications</div>
      <div style="font-size:13px;color:{EMAIL_TEXT_SECONDARY};padding-left:16px;border-left:2px solid {EMAIL_BRAND_PRIMARY};margin-bottom:8px">Emergency contact escalation</div>
      <div style="font-size:13px;color:{EMAIL_TEXT_SECONDARY};padding-left:16px;border-left:2px solid {EMAIL_BRAND_PRIMARY}">Welfare check calls</div>
    </div>
    <p style="font-size:14px;color:{EMAIL_TEXT_SECONDARY};text-align:center;margin-bottom:24px"><strong style="color:{EMAIL_BRAND_SECONDARY}">$5</strong> to turn it all back on. One payment, forever.</p>
    <a href="{app_url}" style="display:block;text-align:center;padding:14px 28px;background:{EMAIL_BRAND_PRIMARY};color:#fff;text-decoration:none;border-radius:6px;font-size:14px;font-weight:600">Reactivate Now →</a>"""
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


def contact_all_clear(user_name: str) -> str:
    """
    All-clear email sent to contacts when user checks in after escalation.

    Args:
        user_name: User who checked in

    Returns:
        HTML email content
    """
    content = f"""<h1 style="font-size:22px;font-weight:700;color:{EMAIL_BRAND_SECONDARY};margin:0 0 12px">All Clear</h1>
    <p style="font-size:14px;color:{EMAIL_TEXT_SECONDARY};line-height:1.6;margin:0 0 28px">{user_name} checked in — no action needed. They are safe.</p>
    <p style="font-size:12px;color:{EMAIL_TEXT_TERTIARY};line-height:1.6">The earlier alert was a false alarm. You don't need to do anything.</p>"""
    return base_email(content, brand_color=EMAIL_BRAND_SECONDARY)


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


def account_deletion_confirmation(user_name: str, deletion_url: str) -> str:
    """
    Account deletion confirmation email sent to user when they request deletion.

    Args:
        user_name: User's display name
        deletion_url: URL containing the time-limited deletion token

    Returns:
        HTML email content
    """
    content = f"""<h1 style="font-size:22px;font-weight:700;color:{EMAIL_TEXT_PRIMARY};margin:0 0 12px">Confirm Account Deletion</h1>
    <p style="font-size:14px;color:{EMAIL_TEXT_SECONDARY};line-height:1.6;margin:0 0 28px">Hey {user_name}, you requested to delete your Still Here account. Click below to confirm — this link expires in 1 hour.</p>
    <a href="{deletion_url}" style="display:block;text-align:center;padding:14px 28px;background:{EMAIL_BRAND_PRIMARY};color:#fff;text-decoration:none;border-radius:6px;font-size:14px;font-weight:600;margin-bottom:24px">Delete My Account →</a>
    <p style="font-size:12px;color:{EMAIL_TEXT_TERTIARY};line-height:1.6">If you didn't request this, ignore this email. Your account will remain active.</p>"""
    return base_email(content)


def user_left_notification(contact_name: str, user_name: str) -> str:
    """
    Notification sent to emergency contacts when a user deletes their account.

    Args:
        contact_name: Contact's display name
        user_name: Name of the user who deleted their account

    Returns:
        HTML email content
    """
    content = f"""<h1 style="font-size:22px;font-weight:700;color:{EMAIL_TEXT_PRIMARY};margin:0 0 12px">Someone left Still Here</h1>
    <p style="font-size:14px;color:{EMAIL_TEXT_SECONDARY};line-height:1.6;margin:0 0 28px">Hi {contact_name}, {user_name} has deleted their Still Here account. You're no longer their emergency contact.</p>
    <p style="font-size:13px;color:{EMAIL_TEXT_SECONDARY};line-height:1.7;margin:0 0 24px">This means their daily check-ins have stopped, and you will no longer receive alerts on their behalf.</p>
    <p style="font-size:12px;color:{EMAIL_TEXT_TERTIARY};line-height:1.6">If you believe this was done in error, you can reach out to {user_name} directly.</p>"""
    return base_email(content)


def contact_removed_notification(contact_name: str, user_name: str) -> str:
    """
    Notification sent to an emergency contact when they are removed from a user's network.

    Args:
        contact_name: Contact's display name
        user_name: Name of the user who removed them

    Returns:
        HTML email content
    """
    content = f"""<h1 style="font-size:22px;font-weight:700;color:{EMAIL_TEXT_PRIMARY};margin:0 0 12px">You've been removed from a network</h1>
    <p style="font-size:14px;color:{EMAIL_TEXT_SECONDARY};line-height:1.6;margin:0 0 28px">Hi {contact_name}, you've been removed from {user_name}'s Still Here safety network.</p>
    <p style="font-size:13px;color:{EMAIL_TEXT_SECONDARY};line-height:1.7;margin:0 0 24px">You will no longer receive check-in alerts or emergency notifications on their behalf.</p>
    <p style="font-size:12px;color:{EMAIL_TEXT_TERTIARY};line-height:1.6">If you believe this was done in error, you can reach out to {user_name} directly.</p>"""
    return base_email(content)
