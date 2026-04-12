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


def test_invite_buddy():
    app, fake_user, mock_db = _make_app()
    with patch("db.get_user_by_email", return_value={"id": "buddy-456", "email": "buddy@test.com"}), \
         patch("db.get_mutual_pairs", return_value=[]), \
         patch("db.create_mutual_pair", return_value={"id": "pair-1", "user_a": "user-123", "user_b": "buddy-456", "status": "pending", "created_at": None, "accepted_at": None, "paused_at": None}):
        client = TestClient(app)
        resp = client.post("/mutual/invite", json={"email": "buddy@test.com"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "invited"
    app.dependency_overrides.clear()


def test_invite_self():
    app, fake_user, mock_db = _make_app()
    client = TestClient(app)
    resp = client.post("/mutual/invite", json={"email": "a@b.com"})
    assert resp.status_code == 400
    assert "yourself" in resp.json()["detail"].lower()
    app.dependency_overrides.clear()


def test_invite_not_found():
    app, fake_user, mock_db = _make_app()
    with patch("db.get_user_by_email", return_value=None):
        client = TestClient(app)
        resp = client.post("/mutual/invite", json={"email": "noone@test.com"})
        assert resp.status_code == 404
    app.dependency_overrides.clear()


def test_accept_invite():
    app, fake_user, mock_db = _make_app()
    with patch("db.accept_mutual_pair", return_value=True):
        client = TestClient(app)
        resp = client.post("/mutual/accept/pair-abc")
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"
    app.dependency_overrides.clear()


def test_pause_and_resume():
    app, fake_user, mock_db = _make_app()
    with patch("db.pause_mutual_pair", return_value=True):
        client = TestClient(app)
        resp = client.post("/mutual/pause/pair-abc")
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"
    with patch("db.resume_mutual_pair", return_value=True):
        client = TestClient(app)
        resp = client.post("/mutual/resume/pair-abc")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"
    app.dependency_overrides.clear()


def test_end_pair():
    app, fake_user, mock_db = _make_app()
    with patch("db.end_mutual_pair", return_value=True):
        client = TestClient(app)
        resp = client.post("/mutual/end/pair-abc")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ended"
    app.dependency_overrides.clear()
