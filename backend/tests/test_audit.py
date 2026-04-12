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


def test_get_audit_log():
    app, fake_user, mock_db = _make_app()
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = [
        {"event_type": "checkin", "details": {"method": "app"}, "created_at": "2026-04-11T09:00:00"},
    ]
    mock_db.execute.return_value = mock_result
    try:
        client = TestClient(app)
        resp = client.get("/checkin/audit")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["events"]) == 1
        assert data["events"][0]["event_type"] == "checkin"
    finally:
        app.dependency_overrides.clear()


def test_audit_log_no_auth():
    from main import app
    from db import get_session
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    app.dependency_overrides.pop("get_current_user", None)
    try:
        client = TestClient(app)
        resp = client.get("/checkin/audit")
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_log_audit_event():
    mock_db = MagicMock()
    mock_db.execute.return_value = MagicMock()
    mock_db.commit.return_value = None
    from db import log_audit_event
    log_audit_event(mock_db, "user-123", "test_event", {"key": "value"})
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()
