from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_app():
    from main import app
    from api_key_auth import get_optional_user, get_api_key_user
    from db import get_session

    fake_user = {"id": "user-123", "email": "a@b.com", "password_hash": "x"}
    mock_db = MagicMock()
    app.dependency_overrides[get_optional_user] = lambda: fake_user
    app.dependency_overrides[get_api_key_user] = lambda: None
    app.dependency_overrides[get_session] = lambda: mock_db
    return app, fake_user, mock_db


def _teardown(app):
    app.dependency_overrides.clear()


def test_first_checkin_no_rate_limit():
    app, fake_user, mock_db = _make_app()
    mock_db.execute.return_value.fetchone.return_value = None
    with patch("routes.checkin.has_checked_in_today", return_value=False), \
         patch("routes.checkin.log_checkin"), \
         patch("db.resolve_escalations"):
        client = TestClient(app)
        resp = client.post("/checkin", json={})
        assert resp.status_code == 200
        assert resp.json()["status"] == "checked_in"
    _teardown(app)


def test_checkin_within_10s():
    app, fake_user, mock_db = _make_app()
    recent = datetime.now(timezone.utc) - timedelta(seconds=2)
    mock_db.execute.return_value.fetchone.return_value = (recent,)
    with patch("routes.checkin.has_checked_in_today", return_value=False), \
         patch("routes.checkin.log_checkin"), \
         patch("db.resolve_escalations"):
        client = TestClient(app)
        resp = client.post("/checkin", json={})
        assert resp.status_code == 429
        assert "wait" in resp.json()["detail"].lower()
    _teardown(app)


def test_checkin_after_10s():
    app, fake_user, mock_db = _make_app()
    old = datetime.now(timezone.utc) - timedelta(seconds=15)
    mock_db.execute.return_value.fetchone.return_value = (old,)
    with patch("routes.checkin.has_checked_in_today", return_value=False), \
         patch("routes.checkin.log_checkin"), \
         patch("db.resolve_escalations"):
        client = TestClient(app)
        resp = client.post("/checkin", json={})
        assert resp.status_code == 200
        assert resp.json()["status"] == "checked_in"
    _teardown(app)
