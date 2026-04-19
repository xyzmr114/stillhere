import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from db import get_session, register_sensor, update_sensor_reading, get_user_sensors, delete_sensor, get_user_by_alexa_id, auto_checkin_if_active, get_user
from dependencies import get_current_user

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
