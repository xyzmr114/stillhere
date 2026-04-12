from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


def _make_app():
    from main import app
    from dependencies import get_current_user
    from db import get_session
    fake_user = {"id": "user-123", "email": "a@b.com", "name": "Test User", "password_hash": "x"}
    mock_db = MagicMock()
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: mock_db
    return app, fake_user, mock_db


def test_dry_run_with_contacts():
    app, fake_user, mock_db = _make_app()
    with patch("routes.demo.get_contacts", return_value=[
        {"name": "Mom", "phone": "+15551234567", "id": "c1"},
        {"name": "Dad", "phone": "+15559876543", "id": "c2"},
    ]), patch("routes.demo.log_escalation_event", return_value="evt-1"):
        client = TestClient(app)
        resp = client.post("/api/demo/dry-run")
        assert resp.status_code == 200
        data = resp.json()
        assert data["contacts_count"] == 2
        assert len(data["preview"]) == 2
        assert "Mom" in data["preview"][0]["sms_text"]
    app.dependency_overrides.clear()


def test_dry_run_no_contacts():
    app, fake_user, mock_db = _make_app()
    with patch("routes.demo.get_contacts", return_value=[]), \
         patch("routes.demo.log_escalation_event", return_value="evt-2"):
        client = TestClient(app)
        resp = client.post("/api/demo/dry-run")
        assert resp.status_code == 200
        assert resp.json()["contacts_count"] == 0
    app.dependency_overrides.clear()


def test_dry_run_no_auth():
    from main import app
    from db import get_session
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    app.dependency_overrides.pop("get_current_user", None)
    try:
        client = TestClient(app)
        resp = client.post("/api/demo/dry-run")
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()
