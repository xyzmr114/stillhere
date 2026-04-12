from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


def _make_app():
    from main import app
    from dependencies import get_current_user
    from db import get_session

    fake_user = {"id": "user-123", "email": "a@b.com", "password_hash": "x"}

    mock_db = MagicMock()
    mock_db.execute.return_value = MagicMock()
    mock_db.commit.return_value = None

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: mock_db

    return app, fake_user, mock_db


def test_set_vacation_mode():
    app, fake_user, mock_db = _make_app()
    try:
        client = TestClient(app)
        resp = client.patch(
            "/users/me",
            json={
                "vacation_start": "2026-05-01T00:00:00Z",
                "vacation_end": "2026-05-15T00:00:00Z",
            },
        )
        assert resp.status_code == 200
        mock_db.execute.assert_called()
        mock_db.commit.assert_called()
    finally:
        app.dependency_overrides.clear()


def test_vacation_invalid_range():
    app, fake_user, mock_db = _make_app()
    try:
        client = TestClient(app)
        resp = client.patch(
            "/users/me",
            json={
                "vacation_start": "2026-05-15T00:00:00Z",
                "vacation_end": "2026-05-01T00:00:00Z",
            },
        )
        assert resp.status_code == 400
        assert "after" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_vacation_partial():
    app, fake_user, mock_db = _make_app()
    try:
        client = TestClient(app)
        resp = client.patch(
            "/users/me",
            json={"vacation_start": "2026-05-01T00:00:00Z"},
        )
        assert resp.status_code == 400
        assert "both" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_vacation_clear():
    app, fake_user, mock_db = _make_app()
    try:
        client = TestClient(app)
        resp = client.patch(
            "/users/me",
            json={"vacation_start": None, "vacation_end": None},
        )
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()
