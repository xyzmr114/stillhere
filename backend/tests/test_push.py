from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _reset_push_module():
    import services.push_svc as mod
    mod._firebase_app = None
    yield
    mod._firebase_app = None


def test_send_push_no_creds():
    with patch("services.push_svc.settings") as mock_settings:
        mock_settings.firebase_cred_path = ""
        import services.push_svc as mod
        mod._firebase_app = None
        result = mod.send_push("some-device-token", "Hi", "Body")
    assert result is True


def test_send_push_empty_token():
    import services.push_svc as mod
    assert mod.send_push("", "Hi", "Body") is False
    assert mod.send_push(None, "Hi", "Body") is False


def _make_app():
    from main import app
    from dependencies import get_current_user
    from db import get_session

    fake_user = {"id": "user-123", "email": "a@b.com", "password_hash": "x"}

    mock_db = MagicMock()
    mock_db.execute.return_value = MagicMock()
    mock_db.commit.return_value = None

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: mock_db

    return app, fake_user, mock_db


def test_register_device_token():
    from main import app
    from dependencies import get_current_user
    from db import get_session

    fake_user = {"id": "user-123", "email": "a@b.com", "password_hash": "x"}
    mock_db = MagicMock()
    mock_db.execute.return_value = MagicMock()
    mock_db.commit.return_value = None

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: mock_db

    try:
        client = TestClient(app)
        resp = client.post(
            "/users/device-token",
            json={"token": "firebase-token-abc"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_register_device_token_no_auth():
    from main import app
    from db import get_session

    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    app.dependency_overrides.pop("get_current_user", None)

    try:
        client = TestClient(app)
        resp = client.post(
            "/users/device-token",
            json={"token": "firebase-token-abc"},
        )
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()
