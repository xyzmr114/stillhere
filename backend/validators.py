import re
from zoneinfo import ZoneInfo


def validate_phone(phone: str) -> str | None:
    """Validate and normalize phone number. Returns E.164 format or None if invalid."""
    if not phone:
        return None
    # Strip whitespace, dashes, parens
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    # Must start with + and have 10-15 digits
    if re.match(r'^\+\d{10,15}$', cleaned):
        return cleaned
    # Try adding +1 for US numbers
    if re.match(r'^\d{10}$', cleaned):
        return '+1' + cleaned
    return None


def validate_timezone(tz: str) -> str | None:
    """Validate IANA timezone string. Returns the timezone or None if invalid."""
    if not tz:
        return None
    try:
        ZoneInfo(tz)
        return tz
    except (KeyError, Exception):
        return None


def validate_checkin_time(time_str: str) -> str | None:
    """Validate HH:MM format. Returns the time string or None if invalid."""
    if not time_str:
        return None
    if not re.match(r'^([01]\d|2[0-3]):[0-5]\d$', time_str):
        return None
    return time_str
