from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


def _make_app():
    from main import app
    from dependencies import get_current_user
    from db import get_session
    fake_user = {"id": "user-123", "email": "a@b.com", "name": "Test", "password_hash": "x"}
    mock_db = MagicMock()
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: mock_db
    return app, fake_user, mock_db


def test_create_api_key():
    app, fake_user, mock_db = _make_app()
    with patch("db.create_api_key", return_value=("key-id-1", "sh_live_" + "a" * 64)):
        client = TestClient(app)
        resp = client.post("/api-keys", json={"name": "Home Assistant"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"].startswith("sh_live_")
        assert data["id"] == "key-id-1"
        assert data["name"] == "Home Assistant"
    app.dependency_overrides.clear()


def test_list_api_keys():
    app, fake_user, mock_db = _make_app()
    fake_keys = [
        {"id": "k1", "name": "Home Assistant", "last_used": None, "created_at": "2026-04-11T00:00:00"},
        {"id": "k2", "name": "Zapier", "last_used": "2026-04-10T12:00:00", "created_at": "2026-04-09T00:00:00"},
    ]
    with patch("db.get_api_keys", return_value=fake_keys):
        client = TestClient(app)
        resp = client.get("/api-keys")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["keys"]) == 2
        assert all("key_hash" not in k for k in data["keys"])
    app.dependency_overrides.clear()


def test_delete_api_key():
    app, fake_user, mock_db = _make_app()
    with patch("db.delete_api_key", return_value=True):
        client = TestClient(app)
        resp = client.delete("/api-keys/key-id-1")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"
    app.dependency_overrides.clear()


def test_checkin_with_api_key():
    from main import app
    from api_key_auth import get_api_key_user, get_optional_user
    from db import get_session

    fake_user = {"id": "api-user-1", "email": "api@test.com", "password_hash": "x"}
    mock_db = MagicMock()
    mock_db.execute.return_value.fetchone.return_value = None
    app.dependency_overrides[get_optional_user] = lambda: fake_user
    app.dependency_overrides[get_api_key_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: mock_db

    try:
        with patch("routes.checkin.has_checked_in_today", return_value=False), \
             patch("routes.checkin.log_checkin"), \
             patch("db.log_audit_event"), \
             patch("db.resolve_escalations"):
            client = TestClient(app)
            resp = client.post("/checkin", json={}, headers={"X-API-Key": "sh_live_testkey123"})
            assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()
