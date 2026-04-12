from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from dependencies import get_current_user
from db import get_session


def _make_app():
    fake_user = {"id": "user-123", "email": "a@b.com", "password_hash": "x"}
    mock_db = MagicMock()
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: mock_db
    return app, fake_user, mock_db


def test_cancel_active_escalation():
    app, fake_user, mock_db = _make_app()
    select_result = MagicMock()
    select_result.mappings.return_value.first.return_value = {
        "id": "esc-1", "resolved": False, "user_id": "user-123"
    }
    user_result = MagicMock()
    user_result.mappings.return_value.first.return_value = {
        "name": "Test", "device_token": None
    }
    mock_db.execute.side_effect = [select_result, MagicMock(), user_result]
    mock_db.commit.return_value = None
    try:
        with patch("services.push_svc.settings") as mock_settings:
            mock_settings.firebase_cred_path = ""
            client = TestClient(app)
            resp = client.post("/escalation/esc-1/cancel")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "cancelled"
    finally:
        app.dependency_overrides.clear()


def test_cancel_no_escalation():
    app, fake_user, mock_db = _make_app()
    select_result = MagicMock()
    select_result.mappings.return_value.first.return_value = None
    mock_db.execute.return_value = select_result
    try:
        client = TestClient(app)
        resp = client.post("/escalation/esc-missing/cancel")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_cancel_already_resolved():
    app, fake_user, mock_db = _make_app()
    select_result = MagicMock()
    select_result.mappings.return_value.first.return_value = {
        "id": "esc-2", "resolved": True, "user_id": "user-123"
    }
    mock_db.execute.return_value = select_result
    try:
        client = TestClient(app)
        resp = client.post("/escalation/esc-2/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "already_resolved"
    finally:
        app.dependency_overrides.clear()


def test_cancel_wrong_user():
    app, fake_user, mock_db = _make_app()
    select_result = MagicMock()
    select_result.mappings.return_value.first.return_value = {
        "id": "esc-3", "resolved": False, "user_id": "other-user"
    }
    mock_db.execute.return_value = select_result
    try:
        client = TestClient(app)
        resp = client.post("/escalation/esc-3/cancel")
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()
