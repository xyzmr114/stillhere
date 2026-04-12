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


def test_trusted_circle():
    app, fake_user, mock_db = _make_app()
    with patch("db.get_trusted_circle", return_value=[
        {"name": "Mom", "phone": "+15551234567", "times_confirmed": 3, "last_confirmed_at": "2026-04-01"},
    ]):
        client = TestClient(app)
        resp = client.get("/contacts/circle")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert "watching out" in data["message"]
    app.dependency_overrides.clear()


def test_annual_report():
    app, fake_user, mock_db = _make_app()
    with patch("db.get_annual_report", return_value={
        "year": 2026, "total_checkins": 100, "longest_streak": 45, "current_streak": 12,
        "by_month": {1: 31, 2: 28, 3: 31}, "milestones": [7, 30, 100],
    }):
        client = TestClient(app)
        resp = client.get("/checkin/report")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_checkins"] == 100
        assert data["milestones"] == [7, 30, 100]
    app.dependency_overrides.clear()


def test_annual_report_no_auth():
    from main import app
    from db import get_session
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    app.dependency_overrides.pop("get_current_user", None)
    try:
        client = TestClient(app)
        resp = client.get("/checkin/report")
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()
