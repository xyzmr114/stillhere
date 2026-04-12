from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


def _make_app():
    from main import app
    from db import get_session
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    return app, mock_db


def test_portal_access():
    app, mock_db = _make_app()
    token_row = {"contact_id": "c-1", "token": "tok-abc", "revoked": False}
    status_data = {
        "user_name": "Alice",
        "last_checkin": "2026-04-11T10:00:00Z",
        "streak": 5,
        "escalation_active": False,
        "is_dormant": False,
    }
    with patch("routes.portal.get_portal_token", return_value=token_row), \
         patch("routes.portal.get_portal_status", return_value=status_data), \
         patch("routes.portal.update_portal_last_accessed"):
        try:
            client = TestClient(app)
            resp = client.get("/portal/tok-abc")
            assert resp.status_code == 200
            data = resp.json()
            assert data["user_name"] == "Alice"
            assert data["streak"] == 5
            assert data["escalation_active"] is False
        finally:
            app.dependency_overrides.clear()


def test_portal_refresh():
    app, mock_db = _make_app()
    with patch("routes.portal.refresh_portal_token", return_value="new-tok-xyz"):
        try:
            client = TestClient(app)
            resp = client.post("/portal/tok-abc/refresh")
            assert resp.status_code == 200
            data = resp.json()
            assert data["token"] == "new-tok-xyz"
        finally:
            app.dependency_overrides.clear()


def test_portal_revoke():
    app, mock_db = _make_app()
    with patch("routes.portal.revoke_portal_token"):
        try:
            client = TestClient(app)
            resp = client.post("/portal/tok-abc/revoke")
            assert resp.status_code == 200
            assert resp.json()["message"] == "Token revoked"
        finally:
            app.dependency_overrides.clear()


def test_portal_revoked_blocked():
    app, mock_db = _make_app()
    with patch("routes.portal.get_portal_token", return_value=None):
        try:
            client = TestClient(app)
            resp = client.get("/portal/tok-revoked")
            assert resp.status_code == 404
        finally:
            app.dependency_overrides.clear()
