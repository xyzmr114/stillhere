"""
Centralized constants for Still Here application.

Organizes hardcoded values by category for easy configuration and maintenance.
"""

# ── Escalation Timing (seconds) ──────────────────────────────────────────────

# Delay after push notification before SMS to user
SMS_DELAY_SECONDS = 900  # 15 minutes

# Delay before first contact confirmation check
CONTACT_CHECK_DELAY_SECONDS = 600  # 10 minutes

# Recurring check interval for contact majority confirmation
CONTACT_MAJORITY_CHECK_INTERVAL_SECONDS = 3600  # 1 hour (recurring)

# Delay before contacting non-emergency service
NON_EMERGENCY_CONTACT_DELAY_SECONDS = 3600  # 1 hour (used after contact confirmation)

# Secondary contact majority check (if threshold not met)
CONTACT_RECHECK_DELAY_SECONDS = 7200  # 2 hours

# Recurring user confirmation prompt
CONTACT_GRACE_TIMEOUT_RECHECK_SECONDS = 14400  # 4 hours

# Delay after SMS/email before making welfare check call to contacts
CONTACT_CALL_DELAY_SECONDS = 60  # 1 minute


# ── Escalation Defaults (user-configurable, in minutes/hours) ───────────────

# Default grace period: time between checkin request and escalation to contacts
DEFAULT_GRACE_MINUTES = 120

# Default contact grace period: time before welfare check call
DEFAULT_CONTACT_GRACE_HOURS = 48

# Default streak reminder: how long before checkin deadline to remind user
DEFAULT_STREAK_REMINDER_HOURS = 2

# Default grace period for auto-checkin window (minutes after checkin time)
DEFAULT_AUTO_CHECKIN_GRACE_MINUTES = 60


# ── Data Limits ──────────────────────────────────────────────────────────────

# Maximum length for checkin notes
MAX_CHECKIN_NOTE_LENGTH = 280

# Maximum number of historical checkins to fetch
MAX_CHECKIN_HISTORY_LIMIT = 30

# Maximum lookahead for streak calculation (days)
MAX_STREAK_LOOKBACK_DAYS = 365

# Minimum streak count to trigger reminder
MIN_STREAK_FOR_REMINDER = 3

# Milestones for annual report
ANNUAL_REPORT_MILESTONES = [7, 30, 100, 365, 500, 1000]

# Maximum audit log entries to fetch
MAX_AUDIT_LOG_LIMIT = 100

# Non-emergency call rate limit: prevent within this window
NON_EMERGENCY_CALL_RATE_LIMIT_HOURS = 72


# ── Dormant Account Logic ────────────────────────────────────────────────────

# Days of inactivity before reengagement email
DORMANT_REENGAGEMENT_THRESHOLD_DAYS = 14

# Days of inactivity before marking account dormant
DORMANT_ACCOUNT_THRESHOLD_DAYS = 30

# Reengagement email rate limit (days)
REENGAGEMENT_EMAIL_RATE_LIMIT_DAYS = 7


# ── Email Token Expiration (timedelta args) ──────────────────────────────────

# Email verification token expiration
VERIFICATION_TOKEN_EXPIRATION_HOURS = 48

# Checkin email token expiration
CHECKIN_TOKEN_EXPIRATION_HOURS = 24

# Password reset token expiration
PASSWORD_RESET_TOKEN_EXPIRATION_HOURS = 1

# Deletion confirmation token expiration
DELETION_TOKEN_EXPIRATION_HOURS = 1


# ── UI/UX Constants ──────────────────────────────────────────────────────────

# Streak reminder window (only alert within this window of checkin deadline)
STREAK_REMINDER_WINDOW_SECONDS = 1800  # 30 minutes


# ── Email Template Branding ──────────────────────────────────────────────────

# Primary brand color (hex) used in email headers and CTAs
EMAIL_BRAND_PRIMARY = "#FF3B3B"  # Red

# Secondary brand color used for positive/confirmation messages
EMAIL_BRAND_SECONDARY = "#4ecca3"  # Teal

# Background color for dark mode emails
EMAIL_BACKGROUND_DARK = "#080808"

# Text color for dark mode emails
EMAIL_TEXT_PRIMARY = "#F5F5F5"

# Subtle text color
EMAIL_TEXT_SECONDARY = "rgba(255,255,255,0.55)"

# Very subtle text color
EMAIL_TEXT_TERTIARY = "rgba(255,255,255,0.3)"

# Card/box background color
EMAIL_CARD_BACKGROUND = "#161616"

# Border color for dark mode
EMAIL_BORDER_COLOR = "rgba(255,255,255,0.08)"

# Email header background
EMAIL_HEADER_BACKGROUND = "#111"

# Email font stack
EMAIL_FONT_STACK = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif"
