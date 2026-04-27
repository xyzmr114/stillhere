"""Tests for Contact SMS -> Call Sequential Timing (CONTACT_CALL_DELAY_SECONDS)."""
from unittest.mock import MagicMock, patch

import pytest

from constants import CONTACT_CALL_DELAY_SECONDS


class MockRow:
    """Simulates a SQLAlchemy Row that supports both .first() and .mappings().first()."""

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


def test_notify_contacts_call_exits_early_when_resolved():
    from tasks.escalation import notify_contacts_call
    event_row = MockRow({"resolved": True, "stage": "contacts_notified"})
    with patch("tasks.escalation._db") as mock_db_fn, \
         patch("tasks.escalation.call_contact") as mock_call:
        mock_db = MagicMock()
        mock_db_fn.return_value = mock_db
        mock_db.execute.return_value = event_row
        notify_contacts_call("user-1", "evt-1")
        mock_call.assert_not_called()


def test_notify_contacts_call_exits_early_when_no_event():
    from tasks.escalation import notify_contacts_call
    with patch("tasks.escalation._db") as mock_db_fn, \
         patch("tasks.escalation.call_contact") as mock_call:
        mock_db = MagicMock()
        mock_db_fn.return_value = mock_db
        mock_db.execute.return_value.mappings.return_value.first.return_value = None
        notify_contacts_call("user-1", "evt-missing")
        mock_call.assert_not_called()


def test_notify_contacts_call_exits_early_when_majority_confirmed():
    from tasks.escalation import notify_contacts_call
    with patch("tasks.escalation._db") as mock_db_fn, \
         patch("tasks.escalation.call_contact") as mock_call:
        mock_db = MagicMock()
        mock_db_fn.return_value = mock_db
        user_row = MockRow({"name": "Alice"})
        # event: not resolved, confirmed=2, total=3, majority=2
        mock_db.execute.side_effect = [
            MockRow({"resolved": False, "stage": "contacts_notified"}),  # event
            MockRow({0: 2}),  # confirmed
            MockRow({0: 3}),  # total
            user_row,
        ]
        notify_contacts_call("user-1", "evt-1")
        mock_call.assert_not_called()


def test_notify_contacts_call_calls_call_contact_for_each_phone():
    from tasks.escalation import notify_contacts_call
    with patch("tasks.escalation._db") as mock_db_fn, \
         patch("tasks.escalation.call_contact") as mock_call, \
         patch("db.get_contacts") as mock_get_contacts:
        mock_db = MagicMock()
        mock_db_fn.return_value = mock_db
        user_row = MockRow({"name": "Bob"})
        mock_get_contacts.return_value = [
            {"id": "c1", "name": "Mom", "phone": "+15551111111", "email": "mom@test.com"},
            {"id": "c2", "name": "Dad", "phone": "+15552222222", "email": "dad@test.com"},
        ]
        # event: not resolved, confirmed=0, total=1, majority=1
        mock_db.execute.side_effect = [
            MockRow({"resolved": False, "stage": "contacts_notified"}),  # event
            MockRow({0: 0}),  # confirmed
            MockRow({0: 1}),  # total
            user_row,
        ]
        notify_contacts_call("user-1", "evt-1")
        assert mock_call.call_count == 2
        mock_call.assert_any_call("+15551111111", "Bob")
        mock_call.assert_any_call("+15552222222", "Bob")


def test_notify_contacts_call_skips_contacts_without_phone():
    from tasks.escalation import notify_contacts_call
    with patch("tasks.escalation._db") as mock_db_fn, \
         patch("tasks.escalation.call_contact") as mock_call, \
         patch("db.get_contacts") as mock_get_contacts:
        mock_db = MagicMock()
        mock_db_fn.return_value = mock_db
        user_row = MockRow({"name": "Alice"})
        mock_get_contacts.return_value = [
            {"id": "c1", "name": "Email only", "phone": None, "email": "email@test.com"},
            {"id": "c2", "name": "Phone", "phone": "+15553333333", "email": None},
        ]
        # event: not resolved, confirmed=0, total=2, majority=1
        mock_db.execute.side_effect = [
            MockRow({"resolved": False, "stage": "contacts_notified"}),  # event
            MockRow({0: 0}),  # confirmed
            MockRow({0: 2}),  # total
            user_row,
        ]
        notify_contacts_call("user-1", "evt-1")
        mock_call.assert_called_once_with("+15553333333", "Alice")


def test_escalate_to_contacts_schedules_notify_contacts_call_with_delay():
    from tasks.escalation import escalate_to_contacts, notify_contacts_call
    with patch("tasks.escalation._db") as mock_db_fn, \
         patch("db.get_contacts") as mock_get_contacts:
        mock_db = MagicMock()
        mock_db_fn.return_value = mock_db
        user_row = MockRow({
            "name": "Alice", "device_token": None, "contact_grace_hours": 48
        })
        mock_db.execute.return_value = user_row
        mock_get_contacts.return_value = []
        with patch.object(notify_contacts_call, "apply_async") as mock_apply, \
             patch("tasks.escalation.check_contact_majority") as mock_check, \
             patch("tasks.escalation.contact_grace_timeout") as mock_grace:
            mock_check.apply_async = MagicMock()
            mock_grace.apply_async = MagicMock()
            escalate_to_contacts("user-1", "evt-1")
        mock_apply.assert_called_once_with(
            args=["user-1", "evt-1"],
            countdown=CONTACT_CALL_DELAY_SECONDS,
        )


def test_escalate_to_contacts_does_not_call_call_contact_directly():
    from tasks.escalation import escalate_to_contacts, notify_contacts_call
    with patch("tasks.escalation._db") as mock_db_fn, \
         patch("db.get_contacts") as mock_get_contacts, \
         patch("tasks.escalation.call_contact") as mock_call, \
         patch("services.sns_svc.send_sms") as mock_sms, \
         patch("services.push_svc.send_push") as mock_push, \
         patch.object(notify_contacts_call, "apply_async") as mock_apply, \
         patch("tasks.escalation.check_contact_majority") as mock_check, \
         patch("tasks.escalation.contact_grace_timeout") as mock_grace, \
         patch("services.email_svc._send_email") as mock_email:
        mock_db = MagicMock()
        mock_db_fn.return_value = mock_db
        user_row = MockRow({
            "name": "Alice", "device_token": None, "contact_grace_hours": 48
        })
        mock_db.execute.return_value = user_row
        mock_get_contacts.return_value = [
            {"id": "c1", "name": "Mom", "phone": "+15551111111", "email": None},
        ]
        mock_check.apply_async = MagicMock()
        mock_grace.apply_async = MagicMock()
        escalate_to_contacts("user-1", "evt-1")
        # call_contact should NOT be called directly from escalate_to_contacts
        mock_call.assert_not_called()
