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


def test_create_family():
    app, fake_user, mock_db = _make_app()
    with patch("routes.family.create_family", return_value="fam-1") as mock_cf:
        try:
            client = TestClient(app)
            resp = client.post("/family", json={"name": "The Smiths"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == "fam-1"
            mock_cf.assert_called_once_with(mock_db, "The Smiths", "user-123")
        finally:
            app.dependency_overrides.clear()


def test_create_family_unpaid():
    app, fake_user, mock_db = _make_app()
    with patch("routes.family.create_family", side_effect=PermissionError("has_paid required")):
        try:
            client = TestClient(app)
            resp = client.post("/family", json={"name": "The Smiths"})
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.clear()


def test_invite_member():
    app, fake_user, mock_db = _make_app()
    with patch("routes.family.get_user_family", return_value={"id": "fam-1", "admin_user_id": "user-123"}), \
         patch("routes.family.create_family_invite", return_value="tok-abc"):
        try:
            client = TestClient(app)
            resp = client.post("/family/invite", json={"email": "mom@example.com"})
            assert resp.status_code == 200
            assert resp.json()["token"] == "tok-abc"
        finally:
            app.dependency_overrides.clear()


def test_join_family():
    app, fake_user, mock_db = _make_app()
    with patch("routes.family.join_family", return_value={"family_id": "fam-1"}):
        try:
            client = TestClient(app)
            resp = client.post("/family/join/tok-abc")
            assert resp.status_code == 200
            assert resp.json()["family_id"] == "fam-1"
        finally:
            app.dependency_overrides.clear()


def test_leave_family():
    app, fake_user, mock_db = _make_app()
    with patch("routes.family.get_user_family", return_value={"id": "fam-1", "admin_user_id": "other-user"}), \
         patch("routes.family.leave_family"):
        try:
            client = TestClient(app)
            resp = client.post("/family/leave")
            assert resp.status_code == 200
            assert resp.json()["message"] == "Left family"
        finally:
            app.dependency_overrides.clear()


def test_remove_member():
    app, fake_user, mock_db = _make_app()
    with patch("routes.family.get_user_family", return_value={"id": "fam-1", "admin_user_id": "user-123"}), \
         patch("routes.family.remove_family_member"):
        try:
            client = TestClient(app)
            resp = client.post("/family/members/user-456/remove")
            assert resp.status_code == 200
            assert resp.json()["message"] == "Member removed"
        finally:
            app.dependency_overrides.clear()


def test_disband_family():
    app, fake_user, mock_db = _make_app()
    with patch("routes.family.get_user_family", return_value={"id": "fam-1", "admin_user_id": "user-123"}), \
         patch("routes.family.disband_family"):
        try:
            client = TestClient(app)
            resp = client.delete("/family")
            assert resp.status_code == 200
            assert resp.json()["message"] == "Family disbanded"
        finally:
            app.dependency_overrides.clear()
