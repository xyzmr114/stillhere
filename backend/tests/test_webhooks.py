import base64
import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


def _make_app():
    from main import app
    from dependencies import get_current_user
    from db import get_session
    fake_user = {"id": "user-123", "email": "a@b.com", "password_hash": "x"}
    mock_db = MagicMock()
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: mock_db
    return app, fake_user, mock_db


def test_sensor_motion_auto_checkin():
    app, fake_user, mock_db = _make_app()
    try:
        with patch("routes.webhooks.register_sensor"), \
             patch("routes.webhooks.update_sensor_reading"), \
             patch("routes.webhooks.auto_checkin_if_active", return_value=True):
            client = TestClient(app)
            resp = client.post("/webhooks/sensor", json={
                "sensor_type": "motion", "sensor_id": "ha_motion_1", "reading": {"motion": True}
            })
            assert resp.status_code == 200
            assert resp.json()["auto_checkin"] == True
            assert resp.json()["status"] == "recorded"
    finally:
        app.dependency_overrides.clear()


def test_sensor_health_auto_checkin():
    app, fake_user, mock_db = _make_app()
    try:
        with patch("routes.webhooks.register_sensor"), \
             patch("routes.webhooks.update_sensor_reading"), \
             patch("routes.webhooks.auto_checkin_if_active", return_value=True):
            client = TestClient(app)
            resp = client.post("/webhooks/sensor", json={
                "sensor_type": "health", "sensor_id": "fitbit_charge5", "reading": {"steps": 500}
            })
            assert resp.status_code == 200
            assert resp.json()["auto_checkin"] == True
    finally:
        app.dependency_overrides.clear()


def test_sensor_no_motion_no_checkin():
    app, fake_user, mock_db = _make_app()
    try:
        with patch("routes.webhooks.register_sensor"), \
             patch("routes.webhooks.update_sensor_reading"), \
             patch("routes.webhooks.auto_checkin_if_active", return_value=False):
            client = TestClient(app)
            resp = client.post("/webhooks/sensor", json={
                "sensor_type": "motion", "sensor_id": "ha_motion_1", "reading": {"motion": False}
            })
            assert resp.status_code == 200
            assert resp.json()["auto_checkin"] == False
    finally:
        app.dependency_overrides.clear()


def test_list_sensors():
    app, fake_user, mock_db = _make_app()
    try:
        with patch("routes.webhooks.get_user_sensors", return_value=[
            {"id": "s1", "sensor_type": "motion", "sensor_id": "ha_living", "last_reading": {"motion": True}, "last_reading_at": "2026-04-11T10:00:00Z"},
        ]):
            client = TestClient(app)
            resp = client.get("/webhooks/sensors")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["sensor_type"] == "motion"
    finally:
        app.dependency_overrides.clear()


def test_alexa_checkin():
    from main import app
    from db import get_session
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    try:
        with patch("routes.webhooks.get_user_by_alexa_id", return_value={"id": "user-123", "email": "a@b.com"}), \
             patch("routes.webhooks.auto_checkin_if_active", return_value=True):
            client = TestClient(app)
            resp = client.post("/webhooks/alexa", json={
                "session": {"user": {"userId": "amzn1.ask.account.12345"}},
                "request": {"intent": {"name": "CheckInIntent"}}
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["version"] == "1.0"
            assert "checked in" in data["response"]["outputSpeech"]["text"].lower()
            assert data["response"]["shouldEndSession"] == True
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Twilio SMS webhook tests
# ---------------------------------------------------------------------------

def _sign_twilio(url: str, params: dict, token: str) -> str:
    """Compute a valid X-Twilio-Signature for test requests.
    Algorithm: URL & sorted key=value pairs joined with &.
    """
    sorted_keys = sorted(params.keys())
    pairs = "&".join(f"{k}={params[k]}" for k in sorted_keys)
    data = f"{url}&{pairs}"
    mac = hmac.new(token.encode(), data.encode(), hashlib.sha1).digest()
    return base64.b64encode(mac).decode()


def test_twilio_stop_sets_notify_sms_false():
    """POST /webhooks/twilio/sms with Body=STOP sets notify_sms=False."""
    from main import app
    from db import get_session
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    try:
        with patch("routes.webhooks.settings") as mock_settings:
            mock_settings.twilio_auth_token = "test_token_123"
            mock_settings.twilio_account_sid = "AC123"
            url = "https://stillhere.example.com/webhooks/twilio/sms"
            params = {"From": "+15551234567", "Body": "STOP"}
            sig = _sign_twilio(url, params, "test_token_123")
            client = TestClient(app)
            resp = client.post(
                "/webhooks/twilio/sms",
                data=params,
                headers={"X-Twilio-Signature": sig},
            )
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "text/xml; charset=utf-8"
            assert "unsubscribed" in resp.text.lower()
            # Verify DB update call
            update_call = mock_db.execute.call_args
            assert update_call is not None
    finally:
        app.dependency_overrides.clear()


def test_twilio_start_sets_notify_sms_true():
    """POST /webhooks/twilio/sms with Body=START sets notify_sms=True."""
    from main import app
    from db import get_session
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    try:
        with patch("routes.webhooks.settings") as mock_settings:
            mock_settings.twilio_auth_token = "test_token_123"
            mock_settings.twilio_account_sid = "AC123"
            url = "https://stillhere.example.com/webhooks/twilio/sms"
            params = {"From": "+15551234567", "Body": "START"}
            sig = _sign_twilio(url, params, "test_token_123")
            client = TestClient(app)
            resp = client.post(
                "/webhooks/twilio/sms",
                data=params,
                headers={"X-Twilio-Signature": sig},
            )
            assert resp.status_code == 200
            assert "resubscribed" in resp.text.lower()
    finally:
        app.dependency_overrides.clear()


def test_twilio_invalid_signature_returns_403():
    """POST /webhooks/twilio/sms with bad signature returns 403."""
    from main import app
    from db import get_session
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    try:
        with patch("routes.webhooks.settings") as mock_settings:
            mock_settings.twilio_auth_token = "test_token_123"
            mock_settings.twilio_account_sid = "AC123"
            client = TestClient(app)
            resp = client.post(
                "/webhooks/twilio/sms",
                data={"From": "+15551234567", "Body": "STOP"},
                headers={"X-Twilio-Signature": "bad_signature"},
            )
            assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_twilio_unknown_keyword_acknowledges():
    """POST /webhooks/twilio/sms with unknown keyword returns OK acknowledgement."""
    from main import app
    from db import get_session
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    try:
        with patch("routes.webhooks.settings") as mock_settings:
            mock_settings.twilio_auth_token = "test_token_123"
            mock_settings.twilio_account_sid = "AC123"
            url = "https://stillhere.example.com/webhooks/twilio/sms"
            params = {"From": "+15551234567", "Body": "FOO"}
            sig = _sign_twilio(url, params, "test_token_123")
            client = TestClient(app)
            resp = client.post(
                "/webhooks/twilio/sms",
                data=params,
                headers={"X-Twilio-Signature": sig},
            )
            assert resp.status_code == 200
            assert "<Response>" in resp.text
    finally:
        app.dependency_overrides.clear()


def test_twilio_help_returns_help_message():
    """POST /webhooks/twilio/sms with HELP returns help text."""
    from main import app
    from db import get_session
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    try:
        with patch("routes.webhooks.settings") as mock_settings:
            mock_settings.twilio_auth_token = "test_token_123"
            mock_settings.twilio_account_sid = "AC123"
            url = "https://stillhere.example.com/webhooks/twilio/sms"
            params = {"From": "+15551234567", "Body": "HELP"}
            sig = _sign_twilio(url, params, "test_token_123")
            client = TestClient(app)
            resp = client.post(
                "/webhooks/twilio/sms",
                data=params,
                headers={"X-Twilio-Signature": sig},
            )
            assert resp.status_code == 200
            assert "STOP" in resp.text
    finally:
        app.dependency_overrides.clear()
