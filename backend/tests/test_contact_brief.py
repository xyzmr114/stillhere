from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from main import app
from db import get_session


def _make_app():
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    return app, mock_db


def test_brief_page():
    app, mock_db = _make_app()
    try:
        client = TestClient(app)
        resp = client.get("/brief")
        assert resp.status_code == 200
        assert "What to do" in resp.text
    finally:
        app.dependency_overrides.clear()


def test_confirm_page_shows_steps():
    app, mock_db = _make_app()
    with patch("routes.confirm.get_contact_confirmation_by_token", return_value={
        "escalation_event_id": "evt-1", "contact_name": "Mom", "confirmed_at": None,
    }), patch("routes.confirm.is_escalation_resolved", return_value=False), \
         patch("routes.confirm.get_escalation_by_id", return_value={"user_id": "u1"}), \
         patch("routes.confirm.get_user", return_value={"name": "Alex"}):
        client = TestClient(app)
        resp = client.get("/confirm/test-token-123")
        assert resp.status_code == 200
        assert "Mom" in resp.text
        assert "Step 1" in resp.text
    app.dependency_overrides.clear()


def test_do_confirm():
    app, mock_db = _make_app()
    with patch("routes.confirm.get_contact_confirmation_by_token", return_value={
        "escalation_event_id": "evt-1", "contact_name": "Mom", "confirmed_at": None,
    }), patch("routes.confirm.is_escalation_resolved", return_value=False), \
         patch("routes.confirm.confirm_contact", return_value="evt-1"), \
         patch("routes.confirm.count_contact_confirmations", return_value=(1, 2)), \
         patch("routes.confirm.get_escalation_by_id", return_value={"user_id": "u1"}), \
         patch("routes.confirm.log_audit_event"):
        client = TestClient(app)
        resp = client.post("/confirm/test-token/confirm")
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"
    app.dependency_overrides.clear()


def test_cant_reach():
    app, mock_db = _make_app()
    with patch("routes.confirm.get_contact_confirmation_by_token", return_value={
        "escalation_event_id": "evt-1", "contact_name": "Mom", "confirmed_at": None,
    }), patch("routes.confirm.get_escalation_by_id", return_value={"user_id": "u1"}), \
         patch("routes.confirm.log_audit_event"):
        client = TestClient(app)
        resp = client.post("/confirm/test-token/cant-reach")
        assert resp.status_code == 200
        assert resp.json()["status"] == "noted"
    app.dependency_overrides.clear()


def test_confirm_page_invalid_token():
    app, mock_db = _make_app()
    with patch("routes.confirm.get_contact_confirmation_by_token", return_value=None):
        client = TestClient(app)
        resp = client.get("/confirm/bad-token")
        assert resp.status_code == 404
    app.dependency_overrides.clear()
