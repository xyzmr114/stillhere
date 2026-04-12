from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


def test_contact_form_success():
    from main import app
    try:
        with patch("routes.contact.SessionLocal") as mock_cls:
            mock_db = MagicMock()
            mock_cls.return_value = mock_db
            client = TestClient(app)
            resp = client.post("/api/contact", json={
                "name": "Test User",
                "email": "test@example.com",
                "message": "Hello!",
            })
            assert resp.status_code == 200
            assert resp.json()["ok"] is True
            mock_db.execute.assert_called_once()
            mock_db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_contact_form_missing_name():
    from main import app
    try:
        client = TestClient(app)
        resp = client.post("/api/contact", json={
            "email": "test@example.com",
            "message": "Hello!",
        })
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_contact_form_missing_email():
    from main import app
    try:
        client = TestClient(app)
        resp = client.post("/api/contact", json={
            "name": "Test",
            "message": "Hello!",
        })
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_contact_form_missing_message():
    from main import app
    try:
        client = TestClient(app)
        resp = client.post("/api/contact", json={
            "name": "Test",
            "email": "test@example.com",
        })
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_contact_form_empty_body():
    from main import app
    try:
        client = TestClient(app)
        resp = client.post("/api/contact", json={})
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_consent_page_served():
    from main import app
    client = TestClient(app)
    resp = client.get("/consent")
    assert resp.status_code == 200
    assert "consent" in resp.text.lower()


def test_contact_page_served():
    from main import app
    client = TestClient(app)
    resp = client.get("/contact")
    assert resp.status_code == 200
    assert "contact" in resp.text.lower()


def test_sitemap_page_served():
    from main import app
    client = TestClient(app)
    resp = client.get("/sitemap")
    assert resp.status_code == 200


def test_sitemap_xml_served():
    from main import app
    client = TestClient(app)
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/xml"
    assert "stillherehq.com" in resp.text
