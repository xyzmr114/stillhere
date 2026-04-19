import logging

from config import settings

logger = logging.getLogger(__name__)


def _get_twilio():
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        return None
    from twilio.rest import Client
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


def _build_twiml(user_name: str, user_address: str) -> str:
    address_part = f" at {user_address}" if user_address else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        "<Pause length=\"2\"/>"
        "<Say voice=\"Polly.Joanna\">"
        "Hello. This is an automated welfare check request from Still Here, "
        "a daily safety check-in service. "
        f"A registered user named {user_name}{address_part} "
        "has not responded to check-in attempts for over 48 hours. "
        "Multiple emergency contacts have also been unable to reach them. "
        "We are requesting a non-emergency wellness check at their residence. "
        "</Say>"
        "<Pause length=\"1\"/>"
        "<Say voice=\"Polly.Joanna\">"
        f"Again, the name is {user_name}{address_part}. "
        "This is an automated call from Still Here. "
        "For questions, contact us at hello@stillherehq.com. "
        "Thank you."
        "</Say>"
        "</Response>"
    )


def call_non_emergency(user_name: str, ne_number: str, user_address: str = None) -> bool:
    """
    Place a welfare check call to the user's local non-emergency line.
    Args:
        user_name: Name of the user to check on
        ne_number: The non-emergency phone number to call (E.164 format)
        user_address: User's address for the welfare check message
    """
    if not ne_number:
        logger.warning(f"[NON-EMERGENCY] No non-emergency number provided for {user_name}")
        return False

    client = _get_twilio()
    if client is None:
        logger.info(
            f"[NON-EMERGENCY STUB] Would call {ne_number} for welfare check on {user_name} at {user_address or 'unknown'}"
        )
        return True

    try:
        twiml = _build_twiml(user_name, user_address or "")
        call = client.calls.create(
            to=ne_number,
            from_=settings.twilio_phone_number,
            twiml=twiml,
        )
        logger.info(f"[NON-EMERGENCY] Welfare check call placed: sid={call.sid}, to={ne_number}, user={user_name}")
        return True
    except Exception as e:
        logger.error(f"[NON-EMERGENCY] Call failed for {user_name}: {e}")
        return False
