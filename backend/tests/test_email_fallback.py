from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
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


def _generate_token(user_id: str = "user-123", days_offset: int = 0):
    from jose import jwt
    from config import settings

    payload = {
        "sub": user_id,
        "date": (date.today() + timedelta(days=days_offset)).isoformat(),
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def test_email_checkin_valid_token():
    app, fake_user, mock_db = _make_app()
    mock_db.execute.return_value = MagicMock()
    mock_db.commit.return_value = None
    with patch("routes.checkin.has_checked_in_today", return_value=False), patch(
        "routes.checkin.log_checkin"
    ), patch("db.resolve_escalations"):
        client = TestClient(app)
        token = _generate_token()
        resp = client.get(f"/checkin/email/{token}")
        assert resp.status_code == 200
        assert "Checked In" in resp.text
    app.dependency_overrides.clear()


def test_email_checkin_invalid_token():
    app, fake_user, mock_db = _make_app()
    client = TestClient(app)
    resp = client.get("/checkin/email/invalid-token-here")
    assert resp.status_code == 400
    assert "Expired" in resp.text or "Invalid" in resp.text
    app.dependency_overrides.clear()


def test_email_checkin_already_checked_in():
    app, fake_user, mock_db = _make_app()
    with patch("routes.checkin.has_checked_in_today", return_value=True):
        client = TestClient(app)
        token = _generate_token()
        resp = client.get(f"/checkin/email/{token}")
        assert resp.status_code == 200
        assert "Already" in resp.text
    app.dependency_overrides.clear()


def test_send_email_stub_mode():
    with patch("services.email_svc.settings") as mock_settings:
        mock_settings.resend_api_key = ""
        mock_settings.base_url = "http://localhost:8000"
        mock_settings.jwt_secret = "test"
        from services.email_svc import send_checkin_email

        result = send_checkin_email("test@test.com", "Test", "user-123")
        assert result is False
