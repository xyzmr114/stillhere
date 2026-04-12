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
        verification = client.verify.v2.services(
            settings.twilio_verify_sid
        ).verifications.create(to=to, channel="sms")
        logger.info(f"Verify SMS sent to {to}: status={verification.status}")
        return True
    except Exception as e:
        logger.error(f"SMS failed: {e}")
        return False


def send_sms_with_message(to: str, body: str) -> bool:
    return send_sms(to, body)
