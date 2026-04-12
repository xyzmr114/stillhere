from unittest.mock import MagicMock
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


def test_get_prompt():
    app, fake_user, mock_db = _make_app()
    mock_result = MagicMock()
    mock_result.first.return_value = ("What made you smile today?",)
    mock_db.execute.return_value = mock_result
    try:
        client = TestClient(app)
        resp = client.get("/checkin/prompt")
        assert resp.status_code == 200
        assert "smile" in resp.json()["prompt"]
    finally:
        app.dependency_overrides.clear()


def test_get_prompt_no_auth():
    from main import app
    from db import get_session
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    app.dependency_overrides.pop("get_current_user", None)
    try:
        client = TestClient(app)
        resp = client.get("/checkin/prompt")
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_streak_reminder_in_patch():
    from main import app
    from dependencies import get_current_user
    from db import get_session
    fake_user = {"id": "user-123", "email": "a@b.com", "password_hash": "x"}
    mock_db = MagicMock()
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: mock_db
    try:
        client = TestClient(app)
        resp = client.patch("/users/me", json={"streak_reminder_hours": 4})
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()
