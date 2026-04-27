"""
Tests for contact removal notification feature (TDD approach).

These tests define the expected behavior per SPEC-remove-contact-notification.md:
- When DELETE /contacts/{contact_id} is called, contact receives email and SMS notification
- Notification is sent asynchronously via Celery task
- Failures in notification delivery are logged but do not fail the deletion itself
- Contact with no email/phone: skip both, still delete

Current state:
- send_contact_removed_email exists in email_svc.py ✓
- contact_removed_notification template exists in email_templates.py ✓
- contact_removed task exists in tasks.escalation ✓
- DELETE endpoint integration ALREADY IMPLEMENTED in routes/contacts.py ✓

The endpoint already calls contact_removed.delay() before deleting.
These tests verify the behavior is correct.
"""

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


class MockRow:
    """Simulates a SQLAlchemy Row that supports .mappings().first() and .first()."""

    def __init__(self, data):
        self._data = data

    def mappings(self):
        m = MagicMock()
        m.first.return_value = self._data
        return m

    def first(self):
        return self._data

    def get(self, key, default=None):
        if isinstance(self._data, dict):
            return self._data.get(key, default)
        return default

    def __getitem__(self, key):
        if isinstance(key, int):
            vals = list(self._data.values()) if isinstance(self._data, dict) else [self._data]
            return vals[key]
        return self._data[key]

    def __bool__(self):
        return True


# =============================================================================
# UNIT TESTS
# =============================================================================

class TestContactRemovedTask:
    """Unit tests for the contact_removed Celery task (already exists in tasks.escalation)."""

    def test_contact_removed_task_sends_email_when_email_provided(self):
        """Task should send email notification when contact has email."""
        from tasks.escalation import contact_removed

        with patch("services.email_svc.send_contact_removed_email") as mock_email, \
             patch("services.sns_svc.send_sms") as mock_sms:
            mock_email.return_value = True
            mock_sms.return_value = True

            contact_removed(
                user_id="user-123",
                contact_name="Alice",
                contact_email="alice@example.com",
                contact_phone="+15551234567"
            )

            mock_email.assert_called_once()
            mock_sms.assert_called_once()  # Both should be called when both are provided

    def test_contact_removed_task_sends_sms_when_phone_provided(self):
        """Task should send SMS notification when contact has phone."""
        from tasks.escalation import contact_removed

        with patch("services.email_svc.send_contact_removed_email") as mock_email, \
             patch("services.sns_svc.send_sms") as mock_sms:
            mock_email.return_value = True
            mock_sms.return_value = True

            contact_removed(
                user_id="user-123",
                contact_name="Alice",
                contact_email=None,
                contact_phone="+15551234567"
            )

            mock_email.assert_not_called()
            mock_sms.assert_called_once()

    def test_contact_removed_task_sends_both_email_and_sms(self):
        """Task should send both email and SMS when contact has both."""
        from tasks.escalation import contact_removed

        with patch("services.email_svc.send_contact_removed_email") as mock_email, \
             patch("services.sns_svc.send_sms") as mock_sms:
            mock_email.return_value = True
            mock_sms.return_value = True

            contact_removed(
                user_id="user-123",
                contact_name="Bob",
                contact_email="bob@example.com",
                contact_phone="+15551234567"
            )

            mock_email.assert_called_once()
            mock_sms.assert_called_once()

    def test_contact_removed_task_skips_email_when_no_email(self):
        """Task should skip email when contact has no email."""
        from tasks.escalation import contact_removed

        with patch("services.email_svc.send_contact_removed_email") as mock_email, \
             patch("services.sns_svc.send_sms") as mock_sms:
            mock_email.return_value = True
            mock_sms.return_value = True

            contact_removed(
                user_id="user-123",
                contact_name="Alice",
                contact_email=None,
                contact_phone="+15551234567"
            )

            mock_email.assert_not_called()
            mock_sms.assert_called_once()

    def test_contact_removed_task_skips_sms_when_no_phone(self):
        """Task should skip SMS when contact has no phone."""
        from tasks.escalation import contact_removed

        with patch("services.email_svc.send_contact_removed_email") as mock_email, \
             patch("services.sns_svc.send_sms") as mock_sms:
            mock_email.return_value = True
            mock_sms.return_value = True

            contact_removed(
                user_id="user-123",
                contact_name="Alice",
                contact_email="alice@example.com",
                contact_phone=None
            )

            mock_email.assert_called_once()
            mock_sms.assert_not_called()

    def test_contact_removed_task_skips_both_when_no_email_no_phone(self):
        """Task should skip both when contact has neither email nor phone."""
        from tasks.escalation import contact_removed

        with patch("services.email_svc.send_contact_removed_email") as mock_email, \
             patch("services.sns_svc.send_sms") as mock_sms:
            mock_email.return_value = True
            mock_sms.return_value = True

            contact_removed(
                user_id="user-123",
                contact_name="Alice",
                contact_email=None,
                contact_phone=None
            )

            mock_email.assert_not_called()
            mock_sms.assert_not_called()

    def test_contact_removed_task_logs_email_failure_but_does_not_raise(self):
        """Task should log email failure but continue without raising."""
        from tasks.escalation import contact_removed

        mock_logger = MagicMock()
        with patch("services.email_svc.send_contact_removed_email") as mock_email, \
             patch("services.sns_svc.send_sms") as mock_sms, \
             patch("logging.getLogger", return_value=mock_logger):
            mock_email.side_effect = Exception("SMTP failed")
            mock_sms.return_value = True

            # Should NOT raise
            contact_removed(
                user_id="user-123",
                contact_name="Alice",
                contact_email="alice@example.com",
                contact_phone="+15551234567"
            )

            # Exception should be logged
            assert mock_logger.exception.called
            mock_sms.assert_called_once()  # SMS should still be attempted

    def test_contact_removed_task_logs_sms_failure_but_does_not_raise(self):
        """Task should log SMS failure but continue without raising."""
        from tasks.escalation import contact_removed

        mock_logger = MagicMock()
        with patch("services.email_svc.send_contact_removed_email") as mock_email, \
             patch("services.sns_svc.send_sms") as mock_sms, \
             patch("logging.getLogger", return_value=mock_logger):
            mock_email.return_value = True
            mock_sms.side_effect = Exception("SMS failed")

            # Should NOT raise
            contact_removed(
                user_id="user-123",
                contact_name="Alice",
                contact_email="alice@example.com",
                contact_phone="+15551234567"
            )

            # Exception should be logged
            assert mock_logger.exception.called
            mock_email.assert_called_once()  # Email should still be sent


class TestDeleteContactEndpoint:
    """Unit tests for DELETE /contacts/{contact_id} endpoint calling the notification task."""

    def _make_mock_db(self, contact_data):
        """Create a mock database session that returns contact_data for get_contact query."""
        mock_db = MagicMock()
        # Simulate get_contact returning the contact
        mock_db.execute.return_value = MockRow(contact_data)
        return mock_db

    def test_delete_contact_calls_notification_task(self):
        """DELETE should call contact_removed task before/at deletion time."""
        from main import app
        from dependencies import get_current_user
        from db import get_session

        mock_user = {"id": "user-123", "name": "Test User"}
        contact_data = {"id": "contact-1", "name": "Alice", "email": "alice@example.com", "phone": "+15551234567"}
        mock_db = self._make_mock_db(contact_data)

        try:
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: mock_db

            with patch("routes.contacts.delete_contact") as mock_delete, \
                 patch("tasks.escalation.contact_removed") as mock_task:
                mock_delete.return_value = None

                client = TestClient(app)
                response = client.delete("/contacts/contact-1")

                # Task should be called with contact details
                mock_task.delay.assert_called_once()
                call_args = mock_task.delay.call_args[1]
                assert call_args["contact_name"] == "Alice"
                assert call_args["contact_email"] == "alice@example.com"
                assert call_args["contact_phone"] == "+15551234567"
        finally:
            app.dependency_overrides.clear()

    def test_delete_contact_returns_200_even_if_notification_fails(self):
        """DELETE should return 200 even if notification task raises."""
        from main import app
        from dependencies import get_current_user
        from db import get_session

        mock_user = {"id": "user-123", "name": "Test User"}
        contact_data = {"id": "contact-1", "name": "Alice", "email": "alice@example.com", "phone": "+15551234567"}
        mock_db = self._make_mock_db(contact_data)

        try:
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: mock_db

            with patch("routes.contacts.delete_contact") as mock_delete, \
                 patch("tasks.escalation.contact_removed") as mock_task:
                mock_delete.return_value = None
                mock_task.delay.side_effect = Exception("Celery unavailable")

                client = TestClient(app)
                response = client.delete("/contacts/contact-1")

                # Should still return 200 - deletion always succeeds
                assert response.status_code == 200
                assert response.json()["message"] == "Contact deleted"
        finally:
            app.dependency_overrides.clear()

    def test_delete_contact_still_succeeds_if_task_raises(self):
        """Deletion should succeed even if notification task raises."""
        from main import app
        from dependencies import get_current_user
        from db import get_session

        mock_user = {"id": "user-123", "name": "Test User"}
        contact_data = {"id": "contact-1", "name": "Alice", "email": "alice@example.com", "phone": "+15551234567"}
        mock_db = self._make_mock_db(contact_data)

        try:
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: mock_db

            with patch("routes.contacts.delete_contact") as mock_delete, \
                 patch("tasks.escalation.contact_removed") as mock_task:
                mock_delete.return_value = None
                mock_task.delay.side_effect = Exception("Task queue down")

                client = TestClient(app)
                response = client.delete("/contacts/contact-1")

                assert response.status_code == 200
                mock_delete.assert_called_once()  # Deletion still happened
        finally:
            app.dependency_overrides.clear()


class TestSendContactRemovedEmail:
    """Unit tests for send_contact_removed_email function (already exists)."""

    def test_send_contact_removed_email_exists(self):
        """send_contact_removed_email function should exist in email_svc."""
        from services import email_svc
        assert hasattr(email_svc, "send_contact_removed_email")

    def test_send_contact_removed_email_calls__send_email(self):
        """send_contact_removed_email should call _send_email with correct subject."""
        from services.email_svc import send_contact_removed_email

        with patch("services.email_svc._send_email") as mock_send:
            mock_send.return_value = True

            send_contact_removed_email(
                to_email="alice@example.com",
                contact_name="Alice",
                user_name="Bob"
            )

            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            assert call_args[0] == "alice@example.com"
            assert "removed" in call_args[1].lower()  # Subject should mention removal


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestContactRemovalIntegration:
    """Integration tests for full contact removal notification flow."""

    def _make_mock_db(self, contact_data):
        """Create a mock database session."""
        mock_db = MagicMock()
        mock_db.execute.return_value = MockRow(contact_data)
        return mock_db

    def test_full_delete_flow_calls_task_with_contact_details(self):
        """Full delete flow: API call -> task called with contact details."""
        from main import app
        from dependencies import get_current_user
        from db import get_session

        mock_user = {"id": "user-123", "name": "Bob"}
        contact_data = {"id": "c1", "name": "Alice", "email": "alice@example.com", "phone": "+15551234567"}
        mock_db = self._make_mock_db(contact_data)

        try:
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: mock_db

            with patch("routes.contacts.delete_contact") as mock_delete, \
                 patch("tasks.escalation.contact_removed") as mock_task:
                mock_delete.return_value = None

                client = TestClient(app)
                response = client.delete("/contacts/c1")

                assert response.status_code == 200
                mock_task.delay.assert_called_once()
                call_kwargs = mock_task.delay.call_args[1]
                assert call_kwargs["contact_name"] == "Alice"
                assert call_kwargs["contact_email"] == "alice@example.com"
                assert call_kwargs["contact_phone"] == "+15551234567"
        finally:
            app.dependency_overrides.clear()

    def test_delete_without_email_or_phone_still_deletes_and_calls_task(self):
        """Contact with no email/phone should still be deleted and task called."""
        from main import app
        from dependencies import get_current_user
        from db import get_session

        mock_user = {"id": "user-123", "name": "Bob"}
        contact_data = {"id": "c1", "name": "Ghost", "email": None, "phone": None}
        mock_db = self._make_mock_db(contact_data)

        try:
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: mock_db

            with patch("routes.contacts.delete_contact") as mock_delete, \
                 patch("tasks.escalation.contact_removed") as mock_task:
                mock_delete.return_value = None

                client = TestClient(app)
                response = client.delete("/contacts/c1")

                assert response.status_code == 200
                mock_delete.assert_called_once()
                # Task is still called but should handle None email/phone gracefully
                mock_task.delay.assert_called_once()
                call_kwargs = mock_task.delay.call_args[1]
                assert call_kwargs["contact_email"] is None
                assert call_kwargs["contact_phone"] is None
        finally:
            app.dependency_overrides.clear()

    def test_delete_returns_200_when_notification_completely_fails(self):
        """DELETE returns 200 even when notification task fails completely."""
        from main import app
        from dependencies import get_current_user
        from db import get_session

        mock_user = {"id": "user-123", "name": "Bob"}
        contact_data = {"id": "c1", "name": "Alice", "email": "alice@example.com", "phone": "+15551234567"}
        mock_db = self._make_mock_db(contact_data)

        try:
            app.dependency_overrides[get_current_user] = lambda: mock_user
            app.dependency_overrides[get_session] = lambda: mock_db

            with patch("routes.contacts.delete_contact") as mock_delete, \
                 patch("tasks.escalation.contact_removed") as mock_task:
                mock_delete.return_value = None
                # Task raises exception but deletion still happens
                mock_task.delay.side_effect = Exception("Total failure")

                client = TestClient(app)
                response = client.delete("/contacts/c1")

                # Deletion always succeeds - 200 returned
                assert response.status_code == 200
                assert response.json()["message"] == "Contact deleted"
        finally:
            app.dependency_overrides.clear()
