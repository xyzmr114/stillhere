from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def test_get_random_checkin_message():
    mock_db = MagicMock()
    mock_db.execute.return_value.first.return_value = ("Hey there! Quick tap to confirm you're doing fine.",)
    from db import get_random_checkin_message
    msg = get_random_checkin_message(mock_db)
    assert "tap" in msg.lower() or "check" in msg.lower()


def test_get_random_checkin_message_fallback():
    mock_db = MagicMock()
    mock_db.execute.return_value.first.return_value = None
    from db import get_random_checkin_message
    msg = get_random_checkin_message(mock_db)
    assert msg == "Still Here? Time to check in!"


def test_confirm_by_minutes_in_patch():
    from main import app
    from dependencies import get_current_user
    from db import get_session
    fake_user = {"id": "user-123", "email": "a@b.com", "password_hash": "x"}
    mock_db = MagicMock()
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: mock_db
    try:
        client = TestClient(app)
        resp = client.patch("/users/me", json={"confirm_by_minutes": 240})
        assert resp.status_code == 200
        mock_db.execute.assert_called()
    finally:
        app.dependency_overrides.clear()
