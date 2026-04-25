import base64
import hashlib
import hmac
import logging
import urllib.parse

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from db import get_session, register_sensor, update_sensor_reading, get_user_sensors, delete_sensor, get_user_by_alexa_id, auto_checkin_if_active, get_user
from db import text  # for raw SQL in Twilio webhook
from dependencies import get_current_user
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class SensorReading(BaseModel):
    sensor_type: str
    sensor_id: str
    reading: dict = {}


class AlexaRequest(BaseModel):
    session: dict = {}
    request: dict = {}


@router.post("/sensor")
def receive_sensor(body: SensorReading, api_key: str = Header(None, alias="X-API-Key"), user=Depends(get_current_user), db=Depends(get_session)):
    effective_user = None
    if api_key:
        try:
            from api_key_auth import hash_api_key
            from db import lookup_api_key
            key_row = lookup_api_key(db, hash_api_key(api_key))
            if key_row:
                from db import touch_api_key
                effective_user = get_user(db, str(key_row["user_id"]))
                touch_api_key(db, str(key_row["id"]))
        except Exception:
            logger.exception("Failed to authenticate sensor webhook via API key")
    if not effective_user:
        effective_user = user
    if not effective_user:
        raise HTTPException(status_code=401)
    uid = str(effective_user["id"])
    register_sensor(db, uid, body.sensor_type, body.sensor_id)
    update_sensor_reading(db, uid, body.sensor_id, body.reading)
    auto_checkin = False
    reading = body.reading or {}
    if body.sensor_type == "motion" and reading.get("motion"):
        auto_checkin = auto_checkin_if_active(db, uid, "sensor")
    elif body.sensor_type == "door" and reading.get("opened"):
        auto_checkin = auto_checkin_if_active(db, uid, "sensor")
    elif body.sensor_type == "health" and reading.get("steps", 0) > 100:
        auto_checkin = auto_checkin_if_active(db, uid, "health")
    return {"status": "recorded", "auto_checkin": auto_checkin}


@router.get("/sensors")
def list_sensors(user=Depends(get_current_user), db=Depends(get_session)):
    uid = str(user["id"])
    sensors = get_user_sensors(db, uid)
    for s in sensors:
        if s.get("last_reading_at") and hasattr(s["last_reading_at"], "isoformat"):
            s["last_reading_at"] = s["last_reading_at"].isoformat()
        if s.get("created_at") and hasattr(s["created_at"], "isoformat"):
            s["created_at"] = s["created_at"].isoformat()
        if "id" in s:
            s["id"] = str(s["id"])
        if "user_id" in s:
            s["user_id"] = str(s["user_id"])
    return sensors


@router.delete("/sensors/{sensor_id}")
def remove_sensor(sensor_id: str, user=Depends(get_current_user), db=Depends(get_session)):
    uid = str(user["id"])
    delete_sensor(db, sensor_id, uid)
    return {"status": "deleted"}


@router.post("/alexa")
def alexa_webhook(body: AlexaRequest, db=Depends(get_session)):
    session = body.session or {}
    request_data = body.request or {}
    user_id_raw = session.get("user", {}).get("userId", "")
    intent_name = request_data.get("intent", {}).get("name", "")
    if not user_id_raw:
        return _alexa_response("I couldn't identify you. Please link your account in the Alexa app.")
    user = get_user_by_alexa_id(db, user_id_raw)
    if not user:
        return _alexa_response("I couldn't find your Still Here account. Please link your account in the Alexa app.")
    uid = str(user["id"])
    if intent_name == "CheckInIntent":
        checked = auto_checkin_if_active(db, uid, "alexa")
        if checked:
            return _alexa_response("You're checked in. Someone always knows you're here.")
        else:
            return _alexa_response("You've already checked in today. Great job staying consistent!")
    return _alexa_response("I'm not sure what you asked. Try saying 'check in'.")


def _alexa_response(text: str):
    return {
        "version": "1.0",
        "response": {
            "outputSpeech": {"type": "PlainText", "text": text},
            "shouldEndSession": True,
        },
    }


# ---------------------------------------------------------------------------
# Twilio inbound SMS webhook
# ---------------------------------------------------------------------------

OPT_OUT_KEYWORDS = {"STOP", "STOPALL", "UNSUBSCRIBE", "CANCEL", "END"}
OPT_IN_KEYWORDS = {"START", "YES", "UNSTOP"}
HELP_KEYWORD = "HELP"


def _validate_twilio_signature(full_url: str, form_data: dict, signature: str) -> bool:
    """Validate X-Twilio-Signature using HMAC-SHA1."""
    if not signature or not settings.twilio_auth_token:
        return False
    # Build sorted param string from form fields
    sorted_keys = sorted(form_data.keys())
    pairs = []
    for k in sorted_keys:
        v = form_data.get(k, "")
        pairs.append(f"{k}={urllib.parse.unquote_plus(str(v))}")
    param_str = "&".join(pairs)
    # Prepend URL with &
    data = f"{full_url}&{param_str}"
    # Compute HMAC-SHA1
    mac = hmac.new(
        settings.twilio_auth_token.encode(),
        data.encode(),
        hashlib.sha1,
    ).digest()
    expected = base64.b64encode(mac).decode()
    return hmac.compare_digest(expected, signature)


def _twiml_response(message: str) -> Response:
    """Return a TwiML XML response."""
    from fastapi.responses import Response
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message>{message}</Message></Response>"
    )
    return Response(content=xml, media_type="text/xml")


@router.post("/twilio/sms")
async def twilio_sms_webhook(request: Request, db=Depends(get_session)):
    # Validate signature
    signature = request.headers.get("X-Twilio-Signature", "")
    # Parse form data (must happen before signature validation which reads _form)
    form_data = await request.form()
    form_dict = dict(form_data)

    if not _validate_twilio_signature(full_url=str(request.url).split("?")[0], form_data=form_dict, signature=signature):
        logger.warning("Twilio SMS webhook received with invalid signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    from_phone = form_dict.get("From", "")
    body = (form_dict.get("Body", "") or "").strip()

    # Handle empty body
    if not body:
        return _twiml_response("OK")

    body_upper = body.upper()

    # Help keyword
    if body_upper == HELP_KEYWORD:
        return _twiml_response(
            "Still Here: Reply CHECKIN to confirm you're safe. "
            "Reply STOP to unsubscribe, START to re-subscribe."
        )

    # Determine notify_sms value
    if body_upper in OPT_OUT_KEYWORDS:
        notify_sms = False
    elif body_upper in OPT_IN_KEYWORDS:
        notify_sms = True
    else:
        notify_sms = None  # acknowledge silently, no DB update

    # Update DB if we have a decision
    if notify_sms is not None and from_phone:
        try:
            db.execute(
                text("UPDATE users SET notify_sms = :val WHERE phone = :phone"),
                {"val": notify_sms, "phone": from_phone},
            )
            db.commit()
        except Exception:
            logger.exception("Failed to update notify_sms for %s", from_phone)

    # Always return TwiML acknowledgement
    if notify_sms is False:
        return _twiml_response("You have been unsubscribed. To re-subscribe, reply START.")
    elif notify_sms is True:
        return _twiml_response("You are resubscribed. You'll receive SMS notifications again.")
    else:
        return _twiml_response("OK")
