"""
Tests for email_verified gate on escalation pipeline.

These tests verify that:
1. poll_and_fire skips users with email_verified=FALSE
2. schedule_daily_checkin exits early for email_verified=FALSE users

Per SPEC.md, the fix requires:
- poll_and_fire SQL query: add `AND email_verified = TRUE`
- schedule_daily_checkin: add early return if email_verified=FALSE

These tests are designed to FAIL before the fix is applied.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


# We need to mock the config module BEFORE importing tasks.escalation
# since it creates engine at module import time
@pytest.fixture(autouse=True)
def mock_config_and_deps():
    """Mock config.settings and database dependencies before escalation module loads."""
    mock_settings = MagicMock()
    mock_settings.database_url = "postgresql://localhost/test"
    mock_settings.redis_url = "redis://localhost"
    mock_settings.jwt_secret = "test-secret"
    mock_settings.base_url = "http://localhost"
    mock_settings.celery_broker = "redis://localhost"
    
    # Mock config module
    with patch.dict('sys.modules', {'config': MagicMock(settings=mock_settings)}):
        yield


class TestPollAndFireEmailVerified:
    """Test that poll_and_fire excludes unverified users from scheduling."""

    def test_poll_and_fire_skips_unverified_user(self):
        """poll_and_fire should not schedule check-in for users with email_verified=FALSE.
        
        This test FAILS before the fix because the SQL query does not filter on email_verified.
        """
        import tasks.escalation as escalation
        
        # User with email_verified=FALSE - should NOT be scheduled
        unverified_user = {
            "id": "user-unverified-123",
            "email": "typo@example.com",
            "checkin_time": "09:00:00",
            "is_dormant": False,
            "has_paid": True,
            "trial_ends_at": None,
            "email_verified": False,
            "timezone": "UTC",
        }

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [unverified_user]
        
        # Mock the "already checked in" query to return None (not checked in)
        mock_checkin_result = MagicMock()
        mock_checkin_result.first.return_value = None
        
        mock_db.execute.side_effect = [mock_result, mock_checkin_result]

        with patch.object(escalation, "_db", return_value=mock_db), \
             patch.object(escalation, "schedule_daily_checkin") as mock_task:
            escalation.poll_and_fire()

            # The fix should ensure schedule_daily_checkin.delay is NOT called
            # Before fix: user gets scheduled (test FAILS)
            # After fix: user is skipped (test PASSES)
            mock_task.delay.assert_not_called()

    def test_poll_and_fire_includes_verified_user(self):
        """poll_and_fire should schedule check-in for users with email_verified=TRUE.
        
        This test verifies the fix doesn't break verified users.
        """
        import tasks.escalation as escalation
        
        verified_user = {
            "id": "user-verified-456",
            "email": "real@example.com",
            "checkin_time": "09:00:00",
            "is_dormant": False,
            "has_paid": True,
            "trial_ends_at": None,
            "email_verified": True,
            "timezone": "UTC",
            "snooze_until": None,
            "vacation_start": None,
            "vacation_end": None,
        }

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [verified_user]
        
        # Mock the "already checked in" query
        mock_checkin_result = MagicMock()
        mock_checkin_result.first.return_value = None
        
        mock_db.execute.side_effect = [mock_result, mock_checkin_result]

        with patch.object(escalation, "_db", return_value=mock_db), \
             patch.object(escalation, "schedule_daily_checkin") as mock_task:
            escalation.poll_and_fire()

            # Verified user should be scheduled
            mock_task.delay.assert_called_once_with("user-verified-456")

    def test_poll_and_fire_sql_includes_email_verified_filter(self):
        """poll_and_fire SQL query should include email_verified = TRUE filter.
        
        This test directly inspects the SQL query to verify the fix.
        FAILS before fix (no email_verified filter), PASSES after fix.
        """
        import tasks.escalation as escalation
        
        verified_user = {
            "id": "user-verified-789",
            "email": "test@example.com",
            "checkin_time": "09:00:00",
            "is_dormant": False,
            "has_paid": True,
            "trial_ends_at": None,
            "email_verified": True,
            "timezone": "UTC",
        }
        
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [verified_user]
        
        mock_checkin_result = MagicMock()
        mock_checkin_result.first.return_value = None
        
        mock_db.execute.side_effect = [mock_result, mock_checkin_result]

        with patch.object(escalation, "_db", return_value=mock_db), \
             patch.object(escalation, "schedule_daily_checkin"):
            escalation.poll_and_fire()
            
            # Verify the SQL query includes email_verified filter
            call_args = mock_db.execute.call_args
            sql_query = call_args[0][0].text if call_args else ""
            
            # Before fix: query does NOT contain "email_verified"
            # After fix: query contains "AND email_verified = TRUE" or similar
            assert "email_verified" in sql_query, \
                f"SQL query missing email_verified filter. Got: {sql_query}"


class TestScheduleDailyCheckinEmailVerified:
    """Test that schedule_daily_checkin exits early for unverified users."""

    def test_schedule_daily_checkin_exits_early_for_unverified(self):
        """schedule_daily_checkin should return immediately when email_verified=FALSE.
        
        This test FAILS before the fix because schedule_daily_checkin does not
        check email_verified and returns early.
        """
        import tasks.escalation as escalation
        
        unverified_user = {
            "grace_minutes": 30,
            "confirm_by_minutes": 10,
            "device_token": "token-abc",
            "notify_push": True,
            "notify_email": True,
            "notify_sms": True,
            "quiet_hours_start": None,
            "quiet_hours_end": None,
            "timezone": "UTC",
            "token_version": 1,
            "email_verified": False,
        }

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = unverified_user
        mock_db.execute.return_value = mock_result

        with patch.object(escalation, "_db", return_value=mock_db), \
             patch("services.push_svc.send_push") as mock_push, \
             patch("db.log_escalation_event") as mock_log, \
             patch("auth.create_jwt", return_value="fake-token"), \
             patch("db.get_random_checkin_message", return_value="Hello"):
            escalation.schedule_daily_checkin("user-unverified-123")

            # Before fix: push notification IS sent (test FAILS)
            # After fix: push notification is NOT sent, function returns early
            mock_push.assert_not_called()
            mock_log.assert_not_called()

    def test_schedule_daily_checkin_proceeds_for_verified(self):
        """schedule_daily_checkin should proceed normally when email_verified=TRUE.
        
        This test verifies the fix doesn't break verified users.
        """
        import tasks.escalation as escalation
        
        verified_user = {
            "grace_minutes": 30,
            "confirm_by_minutes": 10,
            "device_token": "token-xyz",
            "notify_push": True,
            "notify_email": True,
            "notify_sms": True,
            "quiet_hours_start": None,
            "quiet_hours_end": None,
            "timezone": "UTC",
            "token_version": 1,
            "email_verified": True,
        }

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = verified_user
        
        email_result = MagicMock()
        email_result.mappings.return_value.first.return_value = {"email": "real@example.com", "name": "Test User"}
        mock_db.execute.side_effect = [mock_result, email_result]

        with patch.object(escalation, "_db", return_value=mock_db), \
             patch("services.push_svc.send_push") as mock_push, \
             patch("db.log_escalation_event") as mock_log, \
             patch("auth.create_jwt", return_value="fake-token"), \
             patch("db.get_random_checkin_message", return_value="Hello"):
            escalation.schedule_daily_checkin("user-verified-456")

            # Verified user should proceed (log_escalation_event called)
            mock_log.assert_called()

    def test_schedule_daily_checkin_sql_includes_email_verified(self):
        """schedule_daily_checkin SQL query should include email_verified in SELECT list.
        
        This test directly inspects the SQL query to verify the fix.
        FAILS before fix (email_verified not selected), PASSES after fix.
        """
        import tasks.escalation as escalation
        
        verified_user = {
            "id": "user-verified-789",
            "email": "test@example.com",
            "grace_minutes": 30,
            "confirm_by_minutes": 10,
            "device_token": "token-xyz",
            "notify_push": True,
            "notify_email": True,
            "notify_sms": True,
            "quiet_hours_start": None,
            "quiet_hours_end": None,
            "timezone": "UTC",
            "token_version": 1,
            "email_verified": True,
        }

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = verified_user
        mock_db.execute.return_value = mock_result

        with patch.object(escalation, "_db", return_value=mock_db):
            escalation.schedule_daily_checkin("user-verified-789")
            
            # Verify the SQL query includes email_verified in SELECT
            call_args = mock_db.execute.call_args
            sql_query = call_args[0][0].text if call_args else ""
            
            # Before fix: query does NOT select email_verified
            # After fix: query includes "email_verified" in SELECT list
            assert "email_verified" in sql_query.lower(), \
                f"SQL query missing email_verified in SELECT. Got: {sql_query}"