from unittest.mock import MagicMock, patch

import pytest

from email_templates import contact_all_clear


def test_contact_all_clear_template_contains_header_and_name():
    html = contact_all_clear("Alice")
    assert "All Clear" in html
    assert "Alice" in html


def test_contact_all_clear_template_mentions_safe():
    html = contact_all_clear("Bob")
    assert "safe" in html.lower()


def _import_task_deps():
    from services import sns_svc
    from services import email_svc
    from db import get_contacts, log_audit_event
    from tasks.escalation import notify_contacts_all_clear
    return sns_svc, email_svc, get_contacts, log_audit_event, notify_contacts_all_clear


def test_notify_contacts_all_clear_sends_sms_and_email():
    # Import modules first, then patch, then call — avoids import caching issues
    import services.sns_svc
    import services.email_svc
    from tasks.escalation import notify_contacts_all_clear
    from db import get_contacts, log_audit_event

    mock_db = MagicMock()
    esc_row = MagicMock()
    esc_row.mappings.return_value.first.return_value = {"stage": "contacts_notified"}
    user_row = MagicMock()
    user_row.mappings.return_value.first.return_value = {"name": "Alice"}
    mock_db.execute.side_effect = [esc_row, user_row]

    mock_get_contacts = MagicMock(return_value=[
        {"id": "c1", "name": "Mom", "phone": "+155****4567", "email": "mom@test.com"},
    ])
    mock_log = MagicMock()

    with patch("tasks.escalation._db", return_value=mock_db), \
         patch.object(services.sns_svc, "send_sms") as mock_sms, \
         patch.object(services.email_svc, "_send_email") as mock_email, \
         patch("db.get_contacts", mock_get_contacts), \
         patch("db.log_audit_event", mock_log):
        notify_contacts_all_clear("user-1", "evt-1")

    mock_sms.assert_called_once_with(
        "+155****4567",
        "\u2705 Alice checked in \u2014 no action needed. They are safe.",
    )
    mock_email.assert_called_once()
    args, _ = mock_email.call_args
    assert args[0] == "mom@test.com"
    assert "All Clear" in args[1]
    assert "Alice" in args[2]


def test_notify_contacts_all_clear_skips_when_stage_not_contacts_notified():
    sns_svc, email_svc, get_contacts, _, task_fn = _import_task_deps()
    with patch("tasks.escalation._db") as mock_db_fn, \
         patch.object(sns_svc, "send_sms") as mock_sms, \
         patch.object(email_svc, "_send_email") as mock_email, \
         patch("db.get_contacts") as mock_get_contacts:
        mock_db = MagicMock()
        mock_db_fn.return_value = mock_db
        mock_db.execute.return_value = MagicMock(
            mappings=MagicMock(first=MagicMock(return_value={"stage": "checkin_requested"}))
        )
        task_fn("user-1", "evt-2")
        mock_sms.assert_not_called()
        mock_email.assert_not_called()
        mock_get_contacts.assert_not_called()


def test_notify_contacts_all_clear_skips_when_no_event():
    sns_svc, email_svc, _, _, task_fn = _import_task_deps()
    with patch("tasks.escalation._db") as mock_db_fn, \
         patch.object(sns_svc, "send_sms") as mock_sms, \
         patch.object(email_svc, "_send_email") as mock_email:
        mock_db = MagicMock()
        mock_db_fn.return_value = mock_db
        mock_db.execute.return_value = MagicMock(
            mappings=MagicMock(first=MagicMock(return_value=None))
        )
        task_fn("user-1", "evt-missing")
        mock_sms.assert_not_called()
        mock_email.assert_not_called()


def test_resolve_escalations_calls_notify_for_contacts_notified_events():
    from db import resolve_escalations
    from tasks.escalation import notify_contacts_all_clear
    mock_db = MagicMock()
    rows_result = MagicMock()
    rows_result.mappings.return_value.all.return_value = [
        {"id": "evt-1"},
        {"id": "evt-2"},
    ]
    mock_db.execute.side_effect = [rows_result, MagicMock(), MagicMock()]
    with patch.object(notify_contacts_all_clear, "delay") as mock_delay:
        resolve_escalations(mock_db, "user-1")
        assert mock_delay.call_count == 2
        mock_delay.assert_any_call("user-1", "evt-1")
        mock_delay.assert_any_call("user-1", "evt-2")


def test_resolve_escalations_does_not_call_notify_when_no_contacts_notified():
    from db import resolve_escalations
    from tasks.escalation import notify_contacts_all_clear
    mock_db = MagicMock()
    rows_result = MagicMock()
    rows_result.mappings.return_value.all.return_value = []
    mock_db.execute.side_effect = [rows_result, MagicMock()]
    with patch.object(notify_contacts_all_clear, "delay") as mock_delay:
        resolve_escalations(mock_db, "user-1")
        mock_delay.assert_not_called()
