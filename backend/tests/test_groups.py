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


def test_create_group():
    app, fake_user, mock_db = _make_app()
    with patch("routes.groups.create_group", return_value="grp-1") as mock_cg:
        try:
            client = TestClient(app)
            resp = client.post("/groups", json={"name": "Roommate Crew"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == "grp-1"
            mock_cg.assert_called_once_with(mock_db, "Roommate Crew", "user-123")
        finally:
            app.dependency_overrides.clear()


def test_list_groups():
    app, fake_user, mock_db = _make_app()
    groups = [{"id": "g1", "name": "Crew", "is_active": True}]
    with patch("routes.groups.get_user_groups", return_value=groups):
        try:
            client = TestClient(app)
            resp = client.get("/groups")
            assert resp.status_code == 200
            assert resp.json() == groups
        finally:
            app.dependency_overrides.clear()


def test_group_detail():
    app, fake_user, mock_db = _make_app()
    group = {"id": "g1", "name": "Crew", "is_active": True, "members": []}
    with patch("routes.groups.get_group", return_value=group):
        try:
            client = TestClient(app)
            resp = client.get("/groups/g1")
            assert resp.status_code == 200
            assert resp.json()["id"] == "g1"
        finally:
            app.dependency_overrides.clear()


def test_invite_member():
    app, fake_user, mock_db = _make_app()
    with patch("routes.groups.get_group", return_value={"id": "g1", "created_by": "user-123", "is_active": True}), \
         patch("routes.groups.get_group_member_count", return_value=3), \
         patch("routes.groups.get_user_by_email", return_value={"id": "user-456", "email": "f@b.com"}), \
         patch("routes.groups.add_group_member"):
        try:
            client = TestClient(app)
            resp = client.post("/groups/g1/invite", json={"email": "f@b.com"})
            assert resp.status_code == 200
            assert resp.json()["message"] == "Member added"
        finally:
            app.dependency_overrides.clear()


def test_invite_full_group():
    app, fake_user, mock_db = _make_app()
    with patch("routes.groups.get_group", return_value={"id": "g1", "created_by": "user-123", "is_active": True}), \
         patch("routes.groups.get_group_member_count", return_value=10):
        try:
            client = TestClient(app)
            resp = client.post("/groups/g1/invite", json={"email": "f@b.com"})
            assert resp.status_code == 400
        finally:
            app.dependency_overrides.clear()


def test_leave_group():
    app, fake_user, mock_db = _make_app()
    with patch("routes.groups.remove_group_member"):
        try:
            client = TestClient(app)
            resp = client.post("/groups/g1/leave")
            assert resp.status_code == 200
            assert resp.json()["message"] == "Left group"
        finally:
            app.dependency_overrides.clear()


def test_disband_group():
    app, fake_user, mock_db = _make_app()
    with patch("routes.groups.get_group", return_value={"id": "g1", "created_by": "user-123", "is_active": True}), \
         patch("routes.groups.disband_group"):
        try:
            client = TestClient(app)
            resp = client.delete("/groups/g1")
            assert resp.status_code == 200
            assert resp.json()["message"] == "Group disbanded"
        finally:
            app.dependency_overrides.clear()


def test_resolve_ping():
    app, fake_user, mock_db = _make_app()
    with patch("routes.groups.resolve_group_ping"):
        try:
            client = TestClient(app)
            resp = client.post("/groups/pings/ping-1/resolve")
            assert resp.status_code == 200
            assert resp.json()["message"] == "Ping resolved"
        finally:
            app.dependency_overrides.clear()
