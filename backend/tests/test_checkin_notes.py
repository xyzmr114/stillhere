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


def test_update_note_checked_in():
    app, fake_user, mock_db = _make_app()
    with patch("routes.checkin.has_checked_in_today", return_value=True), \
         patch("db.update_checkin_note"):
        client = TestClient(app)
        resp = client.patch("/checkin/note", json={"note": "Rough day but here."})
        assert resp.status_code == 200
        assert resp.json()["status"] == "saved"
    app.dependency_overrides.clear()


def test_update_note_not_checked_in():
    app, fake_user, mock_db = _make_app()
    with patch("routes.checkin.has_checked_in_today", return_value=False):
        client = TestClient(app)
        resp = client.patch("/checkin/note", json={"note": "Test"})
        assert resp.status_code == 400
    app.dependency_overrides.clear()


def test_update_note_no_auth():
    from main import app
    from db import get_session
    mock_db = MagicMock()
    app.dependency_overrides[get_session] = lambda: mock_db
    app.dependency_overrides.pop("get_current_user", None)
    try:
        client = TestClient(app)
        resp = client.patch("/checkin/note", json={"note": "Test"})
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()
