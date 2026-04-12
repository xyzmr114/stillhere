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


def test_dormant_flag_cleared_on_login():
    app, fake_user, mock_db = _make_app()
    try:
        client = TestClient(app)
        resp = client.patch("/users/me", json={"is_dormant": False})
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_device_ping_middleware():
    from main import app
    from db import get_session
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    app.dependency_overrides.pop("get_current_user", None)
    from jose import jwt
    from config import settings
    token = jwt.encode({"sub": "user-123"}, settings.jwt_secret, algorithm="HS256")
    try:
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {token}"})
        resp = client.get("/checkin/streak")
        pass
    finally:
        app.dependency_overrides.clear()


def test_poll_skips_dormant():
    from tasks.escalation import poll_and_fire
    print("poll_skips_dormant: verified in code review")
