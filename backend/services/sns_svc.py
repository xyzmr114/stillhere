import logging

from config import settings

logger = logging.getLogger(__name__)

_twilio_client = None


def _get_twilio():
    global _twilio_client
    if _twilio_client is None:
        if not settings.twilio_account_sid or not settings.twilio_auth_token:
            logger.warning("Twilio credentials not configured — SMS will be logged only")
            return None
        from twilio.rest import Client

        _twilio_client = Client(
            settings.twilio_account_sid,
            settings.twilio_auth_token,
        )
    return _twilio_client


def send_sms(to: str, body: str) -> bool:
    client = _get_twilio()
    if client is None:
        logger.info(f"[SMS STUB] To: {to} | Body: {body}")
        return True
    try:
        message = client.messages.create(
            to=to,
            from_=settings.twilio_phone_number,
            body=body,
        )
        logger.info(f"SMS sent to {to}: sid={message.sid}")
        return True
    except Exception as e:
        logger.error(f"SMS failed to {to}: {e}")
        return False


def call_contact(to: str, user_name: str) -> bool:
    """Call an emergency contact with a voice message about a missed check-in."""
    client = _get_twilio()
    if client is None:
        logger.info(f"[VOICE STUB] Would call {to} about {user_name}")
        return True
    try:
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            "<Pause length=\"1\"/>"
            "<Say voice=\"Polly.Joanna\">"
            f"Hello. This is an urgent message from Still Here. "
            f"{user_name} has missed their daily safety check-in "
            "and we have been unable to reach them. "
            "Please try to contact them and confirm their safety "
            f"as soon as possible. Again, {user_name} has missed their check-in. "
            "Please check on them. Thank you."
            "</Say>"
            "</Response>"
        )
        call = client.calls.create(
            to=to,
            from_=settings.twilio_phone_number,
            twiml=twiml,
        )
        logger.info(f"Contact voice call placed: sid={call.sid}, to={to}")
        return True
    except Exception as e:
        logger.error(f"Contact voice call failed to {to}: {e}")
        return False
