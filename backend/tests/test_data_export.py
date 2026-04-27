from unittest.mock import MagicMock

from fastapi.testclient import TestClient


def _make_app(user_overrides=None):
    from main import app
    from dependencies import get_current_user
    from db import get_session

    fake_user = {
        "id": "user-123",
        "email": "a@b.com",
        "name": "Test User",
        "phone": "+1234567890",
        "password_hash": "secret",
        "token_version": 3,
        "device_token": "dev-token",
        "notify_push": True,
        "notify_email": False,
        "notify_sms": True,
        "quiet_hours_start": "22:00",
        "quiet_hours_end": "07:00",
    }
    if user_overrides:
        fake_user.update(user_overrides)

    mock_db = MagicMock()
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: mock_db
    return app, fake_user, mock_db


def _mock_query_result(rows):
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = rows
    return mock_result


def test_export_returns_all_sections():
    app, fake_user, mock_db = _make_app()
    checkin_row = {"id": "c1", "created_at": "2026-04-27", "note": "hi", "status": "checked_in", "streak": 5}
    contact_row = {"id": "ct1", "name": "Jane", "relationship": "sibling", "priority": 1}
    audit_row = {"id": "a1", "event": "checkin", "created_at": "2026-04-27", "details": {}}
    group_row = {"id": "g1", "name": "Family", "type": "family", "my_role": "admin"}

    mock_db.execute.side_effect = [
        _mock_query_result([checkin_row]),
        _mock_query_result([contact_row]),
        _mock_query_result([audit_row]),
        _mock_query_result([group_row]),
    ]

    try:
        client = TestClient(app)
        resp = client.get("/users/me/export")
        assert resp.status_code == 200
        data = resp.json()
        assert "exported_at" in data
        assert data["user"]["email"] == "a@b.com"
        assert "password_hash" not in data["user"]
        assert "token_version" not in data["user"]
        assert "device_token" not in data["user"]
        assert len(data["checkins"]) == 1
        assert data["checkins"][0]["streak"] == 5
        assert len(data["contacts"]) == 1
        assert "phone" not in data["contacts"][0]
        assert "email" not in data["contacts"][0]
        assert len(data["audit_log"]) == 1
        assert len(data["groups"]) == 1
        assert data["groups"][0]["my_role"] == "admin"
        assert data["notification_settings"]["notify_push"] is True
        assert data["notification_settings"]["notify_email"] is False
        assert data["notification_settings"]["quiet_hours_start"] == "22:00"
    finally:
        app.dependency_overrides.clear()


def test_export_no_auth_returns_401():
    from main import app
    from db import get_session

    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    app.dependency_overrides.pop("get_current_user", None)

    try:
        client = TestClient(app)
        resp = client.get("/users/me/export")
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_export_empty_data():
    app, fake_user, mock_db = _make_app()
    mock_db.execute.side_effect = [
        _mock_query_result([]),
        _mock_query_result([]),
        _mock_query_result([]),
        _mock_query_result([]),
    ]

    try:
        client = TestClient(app)
        resp = client.get("/users/me/export")
        assert resp.status_code == 200
        data = resp.json()
        assert data["checkins"] == []
        assert data["contacts"] == []
        assert data["audit_log"] == []
        assert data["groups"] == []
    finally:
        app.dependency_overrides.clear()


def test_export_contacts_no_phone_or_email():
    app, fake_user, mock_db = _make_app()
    contact_row = {"id": "ct1", "name": "Jane", "relationship": "friend", "priority": 2}
    mock_db.execute.side_effect = [
        _mock_query_result([]),
        _mock_query_result([contact_row]),
        _mock_query_result([]),
        _mock_query_result([]),
    ]

    try:
        client = TestClient(app)
        resp = client.get("/users/me/export")
        data = resp.json()
        contact = data["contacts"][0]
        assert set(contact.keys()) == {"id", "name", "relationship", "priority"}
    finally:
        app.dependency_overrides.clear()


def test_export_strips_sensitive_user_fields():
    app, fake_user, mock_db = _make_app()
    mock_db.execute.side_effect = [
        _mock_query_result([]),
        _mock_query_result([]),
        _mock_query_result([]),
        _mock_query_result([]),
    ]

    try:
        client = TestClient(app)
        resp = client.get("/users/me/export")
        data = resp.json()
        user = data["user"]
        assert "password_hash" not in user
        assert "token_version" not in user
        assert "device_token" not in user
    finally:
        app.dependency_overrides.clear()


def test_export_db_error_returns_500():
    app, fake_user, mock_db = _make_app()
    mock_db.execute.side_effect = Exception("DB connection lost")

    try:
        client = TestClient(app)
        resp = client.get("/users/me/export")
        assert resp.status_code == 500
    finally:
        app.dependency_overrides.clear()


def test_export_notification_settings_defaults():
    app, _, mock_db = _make_app(user_overrides={
        "notify_push": None,
        "notify_email": None,
        "notify_sms": None,
        "quiet_hours_start": None,
        "quiet_hours_end": None,
    })
    mock_db.execute.side_effect = [
        _mock_query_result([]),
        _mock_query_result([]),
        _mock_query_result([]),
        _mock_query_result([]),
    ]

    try:
        client = TestClient(app)
        resp = client.get("/users/me/export")
        data = resp.json()
        ns = data["notification_settings"]
        assert ns["notify_push"] is True
        assert ns["notify_email"] is True
        assert ns["notify_sms"] is True
        assert ns["quiet_hours_start"] is None
        assert ns["quiet_hours_end"] is None
    finally:
        app.dependency_overrides.clear()
