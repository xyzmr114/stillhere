from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


def _make_app(has_paid=False):
    from main import app
    from dependencies import get_current_user
    from db import get_session
    fake_user = {"id": "user-123", "email": "a@b.com", "password_hash": "x", "has_paid": has_paid}
    mock_db = MagicMock()
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: mock_db
    return app, fake_user, mock_db


def test_checkout_returns_url():
    app, fake_user, mock_db = _make_app(has_paid=False)
    try:
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/test"
        with patch("routes.stripe_payments.stripe.checkout.Session.create", return_value=mock_session):
            client = TestClient(app)
            resp = client.post("/stripe/checkout")
            assert resp.status_code == 200
            data = resp.json()
            assert "url" in data
            assert data["url"].startswith("https://checkout.stripe.com")
    finally:
        app.dependency_overrides.clear()


def test_checkout_already_paid():
    app, fake_user, mock_db = _make_app(has_paid=True)
    try:
        client = TestClient(app)
        resp = client.post("/stripe/checkout")
        assert resp.status_code == 400
        assert "already paid" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_webhook_flips_has_paid():
    from main import app
    try:
        with patch("routes.stripe_payments.stripe.Webhook.construct_event") as mock_construct, \
             patch("routes.stripe_payments.SessionLocal") as mock_session_cls:
            mock_construct.return_value = {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "client_reference_id": "user-123",
                    }
                },
            }
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            client = TestClient(app)
            resp = client.post(
                "/stripe/webhook",
                content=b'{}',
                headers={"stripe-signature": "test_sig"},
            )
            assert resp.status_code == 200
            mock_db.execute.assert_called_once()
            mock_db.commit.assert_called_once()
            call_args = mock_db.execute.call_args
            assert "user-123" in str(call_args)
    finally:
        app.dependency_overrides.clear()


def test_webhook_rejects_bad_signature():
    from main import app
    try:
        with patch("routes.stripe_payments.stripe.Webhook.construct_event") as mock_construct:
            import stripe as stripe_lib
            mock_construct.side_effect = stripe_lib.error.SignatureVerificationError("bad", "sig")
            client = TestClient(app)
            resp = client.post(
                "/stripe/webhook",
                content=b'{}',
                headers={"stripe-signature": "bad_sig"},
            )
            assert resp.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_webhook_missing_client_ref():
    from main import app
    try:
        with patch("routes.stripe_payments.stripe.Webhook.construct_event") as mock_construct, \
             patch("routes.stripe_payments.SessionLocal") as mock_session_cls:
            mock_construct.return_value = {
                "type": "checkout.session.completed",
                "data": {
                    "object": {}
                },
            }
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            client = TestClient(app)
            resp = client.post(
                "/stripe/webhook",
                content=b'{}',
                headers={"stripe-signature": "test_sig"},
            )
            assert resp.status_code == 200
            mock_db.execute.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_webhook_email_fallback():
    from main import app
    try:
        with patch("routes.stripe_payments.stripe.Webhook.construct_event") as mock_construct, \
             patch("routes.stripe_payments.SessionLocal") as mock_session_cls:
            mock_construct.return_value = {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "customer_email": "a@b.com",
                    }
                },
            }
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            client = TestClient(app)
            resp = client.post(
                "/stripe/webhook",
                content=b'{}',
                headers={"stripe-signature": "test_sig"},
            )
            assert resp.status_code == 200
            mock_db.execute.assert_called_once()
            mock_db.commit.assert_called_once()
            call_args = mock_db.execute.call_args
            assert "a@b.com" in str(call_args)
    finally:
        app.dependency_overrides.clear()
