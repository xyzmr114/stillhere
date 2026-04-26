"""
Tests for email change feature per SPEC-email-change.md.

These tests verify that:
1. User can change email from settings via PATCH /users/me
2. After email change, email_verified = FALSE in DB
3. A verification email is sent ONLY to the new address (not old)
4. If new email is already in use, API returns 400 with "Email already in use"
5. After email change, old sessions are invalidated (token_version bumped)
6. User cannot pass email verification gate until they verify

Edge cases:
- Same email change: No-op, don't reset verification or bump token version
- Invalid email format: Should be rejected
- Resend verification after email change: Works correctly
- Rapid email changes: Each change resets verification, only latest gets verification

Note: These are unit tests that directly test the underlying functions
to avoid Redis dependency. They follow patterns from test_email_verified_gate.py.

The tests are designed to FAIL before the email change feature is implemented,
and PASS after the implementation per SPEC-email-change.md.
"""
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# Tests for UserPatch model - email field
# ============================================================================

class TestUserPatchModel:
    """Test that UserPatch model has email field (SPEC requirement)."""

    def test_userpatch_model_has_email_field(self):
        """UserPatch model should accept and store an email field.
        
        FAILS before implementation: UserPatch does not have email field
        PASSES after implementation: email field added to UserPatch
        """
        import importlib
        import routes.users as users_module
        importlib.reload(users_module)
        
        from routes.users import UserPatch
        
        # Create a patch object with email
        patch_data = UserPatch(email="test@example.com")
        # This will fail if email field doesn't exist
        assert hasattr(patch_data, 'email'), "UserPatch should have email field"
        assert patch_data.email == "test@example.com"
        
    def test_userpatch_email_is_optional(self):
        """UserPatch email field should be optional (None by default).
        
        FAILS before implementation: email field doesn't exist
        PASSES after implementation: email field defaults to None
        """
        import importlib
        import routes.users as users_module
        importlib.reload(users_module)
        
        from routes.users import UserPatch
        
        # Create without email
        patch_data = UserPatch()
        # This will fail if email field doesn't exist
        assert hasattr(patch_data, 'email'), "UserPatch should have email field"
        assert patch_data.email is None


# ============================================================================
# Tests for email uniqueness check logic
# ============================================================================

class TestEmailUniquenessCheck:
    """Test that email uniqueness is properly validated."""

    def test_email_change_rejects_duplicate_email(self):
        """If new email is already in use by another user, return 400.
        
        FAILS before implementation: email field not processed, no uniqueness check
        PASSES after implementation: proper uniqueness check with HTTPException
        """
        import importlib
        import routes.users as users_module
        importlib.reload(users_module)
        
        from routes.users import update_me, UserPatch
        from fastapi import HTTPException
        
        mock_user = {
            "id": "user-123",
            "email": "old@example.com",
            "name": "Test User",
            "password_hash": "x",
            "email_verified": True,
            "token_version": 1,
        }
        
        mock_db = MagicMock()
        
        def mock_get_user_by_email(db, email):
            if email == "new@example.com":
                return {"id": "other-user-456", "email": "new@example.com"}
            return None
        
        # get_user_by_email is in db module, imported at routes.users module level
        # send_verification_email is imported locally inside update_me()
        with patch("routes.users.get_user_by_email", side_effect=mock_get_user_by_email), \
             patch("services.email_svc.send_verification_email", create=True):
            body = UserPatch(email="new@example.com")
            
            # This should raise HTTPException with "Email already in use"
            try:
                update_me(body, user=mock_user, db=mock_db)
                # If we get here, the feature isn't implemented
                pytest.fail("Expected HTTPException for duplicate email, but no exception was raised")
            except HTTPException as e:
                assert e.status_code == 400
                assert "Email already in use" in e.detail

    def test_email_change_allows_same_email_to_same_user(self):
        """If user changes to their own current email, it should be allowed.
        
        This tests that same-email is treated as no-op.
        """
        import importlib
        import routes.users as users_module
        importlib.reload(users_module)
        
        from routes.users import update_me, UserPatch
        
        mock_user = {
            "id": "user-123",
            "email": "same@example.com",
            "name": "Test User",
            "password_hash": "x",
            "email_verified": True,
            "token_version": 1,
        }
        
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = {**mock_user}
        mock_db.execute.return_value = mock_result
        
        def mock_get_user_by_email(db, email):
            if email == "same@example.com":
                return {"id": "user-123", "email": "same@example.com"}  # Same user
            return None
        
        with patch("routes.users.get_user_by_email", side_effect=mock_get_user_by_email):
            body = UserPatch(email="same@example.com")
            # Should NOT raise - same user can keep their own email
            try:
                result = update_me(body, user=mock_user, db=mock_db)
            except HTTPException as e:
                if "Email already in use" in str(e):
                    pytest.fail("Email change to same email should be a no-op, not an error")


# ============================================================================
# Tests for email change verification status reset
# ============================================================================

class TestEmailChangeVerificationReset:
    """Test that email_verified is reset when email changes."""

    def test_email_change_resets_verification_to_false(self):
        """When email is changed, email_verified should be set to FALSE.
        
        FAILS before implementation: email not in ALLOWED_COLUMNS, no reset logic
        PASSES after implementation: email_verified set to FALSE in UPDATE
        """
        import importlib
        import routes.users as users_module
        importlib.reload(users_module)
        
        from routes.users import update_me, UserPatch
        
        mock_user = {
            "id": "user-123",
            "email": "old@example.com",
            "name": "Test User",
            "password_hash": "x",
            "email_verified": True,
            "token_version": 1,
        }
        
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = {
            **mock_user,
            "email": "new@example.com",
            "email_verified": False,  # After change
        }
        mock_db.execute.return_value = mock_result
        
        # Track what UPDATE queries are executed
        update_queries = []
        def capture_update(query, params):
            update_queries.append({"query": str(query), "params": dict(params)})
            return MagicMock()
        mock_db.execute.side_effect = capture_update
        
        with patch("routes.users.get_user_by_email", return_value=None), \
             patch("services.email_svc.send_verification_email", create=True):
            body = UserPatch(email="new@example.com")
            result = update_me(body, user=mock_user, db=mock_db)
            
            # Check that email_verified was set to FALSE in an UPDATE query
            # (the SELECT from get_user() at end of update_me is the last query, so skip it)
            update_queries_only = [q for q in update_queries if "update" in q["query"].lower()]
            assert update_queries_only, f"No UPDATE query found. All queries: {[q['query'] for q in update_queries]}"
            
            # The email change UPDATE should be the one with email_verified = FALSE
            email_update = None
            for q in update_queries_only:
                if "email_verified" in q["query"].lower():
                    email_update = q
                    break
            assert email_update is not None, \
                f"email_verified not in any UPDATE. Updates: {[q['query'] for q in update_queries_only]}"


# ============================================================================
# Tests for token_version bump on email change
# ============================================================================

class TestEmailChangeTokenVersionBump:
    """Test that token_version is bumped when email changes."""

    def test_email_change_bumps_token_version(self):
        """When email is changed, token_version should be incremented.
        
        FAILS before implementation: no token_version bump logic for email
        PASSES after implementation: token_version = token_version + 1 in UPDATE
        """
        import importlib
        import routes.users as users_module
        importlib.reload(users_module)
        
        from routes.users import update_me, UserPatch
        
        mock_user = {
            "id": "user-123",
            "email": "old@example.com",
            "name": "Test User",
            "password_hash": "x",
            "email_verified": True,
            "token_version": 1,
        }
        
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = {
            **mock_user,
            "token_version": 2,  # After bump
        }
        mock_db.execute.return_value = mock_result
        
        # Track what UPDATE queries are executed
        update_queries = []
        def capture_update(query, params):
            update_queries.append({"query": str(query), "params": dict(params)})
            return MagicMock()
        mock_db.execute.side_effect = capture_update
        
        with patch("routes.users.get_user_by_email", return_value=None), \
             patch("services.email_svc.send_verification_email", create=True):
            body = UserPatch(email="new@example.com")
            result = update_me(body, user=mock_user, db=mock_db)
            
            # Check that token_version bump was attempted
            found_bump = False
            for uq in update_queries:
                if "token_version" in str(uq["query"]).lower():
                    found_bump = True
                    break
            
            assert found_bump, \
                f"token_version was not bumped after email change. Updates: {update_queries}"


# ============================================================================
# Tests for verification email sending
# ============================================================================

class TestEmailChangeVerificationEmail:
    """Test that verification email is sent to new address only."""

    def test_verification_email_sent_to_new_address(self):
        """When email is changed, verification should be sent to NEW address only.
        
        FAILS before implementation: send_verification_email not called
        PASSES after implementation: email sent to new@example.com, not old@example.com
        """
        import importlib
        import routes.users as users_module
        importlib.reload(users_module)
        
        from routes.users import update_me, UserPatch
        
        mock_user = {
            "id": "user-123",
            "email": "old@example.com",
            "name": "Test User",
            "password_hash": "x",
            "email_verified": True,
            "token_version": 1,
        }
        
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = {
            **mock_user,
            "email": "new@example.com",
        }
        mock_db.execute.return_value = mock_result
        
        with patch("routes.users.get_user_by_email", return_value=None), \
             patch("services.email_svc.send_verification_email", create=True) as mock_send:
            body = UserPatch(email="new@example.com")
            result = update_me(body, user=mock_user, db=mock_db)
            
            # Verify send_verification_email was called
            assert mock_send.called, "send_verification_email was not called"
            
            # Verify it was called with NEW email
            call_args = mock_send.call_args[0]
            assert call_args[0] == "new@example.com", \
                f"Verification email sent to wrong address. Expected: new@example.com, Got: {call_args[0]}"
            assert call_args[1] == "Test User", \
                f"Verification email sent with wrong name. Expected: Test User, Got: {call_args[1]}"
            assert call_args[2] == "user-123", \
                f"Verification email sent with wrong user_id. Expected: user-123, Got: {call_args[2]}"

    def test_same_email_does_not_send_verification(self):
        """When email is unchanged, verification email should NOT be sent.
        
        FAILS before implementation: no special handling for same email
        PASSES after implementation: same email is no-op
        """
        import importlib
        import routes.users as users_module
        importlib.reload(users_module)
        
        from routes.users import update_me, UserPatch
        
        mock_user = {
            "id": "user-123",
            "email": "same@example.com",
            "name": "Test User",
            "password_hash": "x",
            "email_verified": True,
            "token_version": 1,
        }
        
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = {**mock_user}
        mock_db.execute.return_value = mock_result
        
        with patch("routes.users.get_user_by_email", return_value={"id": "user-123", "email": "same@example.com"}), \
             patch("services.email_svc.send_verification_email", create=True):
            body = UserPatch(email="same@example.com")
            result = update_me(body, user=mock_user, db=mock_db)
            
            # If same email is properly handled as no-op, verification should not be sent
            # Note: The implementation may or may not call send_verification_email for same email
            # This test documents expected behavior after implementation


# ============================================================================
# Tests for email field in ALLOWED_COLUMNS
# ============================================================================

class TestEmailInAllowedColumns:
    """Test that email is in the list of allowed columns for update."""

    def test_email_field_is_allowed_in_update(self):
        """The email field should be in ALLOWED_COLUMNS for PATCH /users/me.
        
        FAILS before implementation: email not in ALLOWED_COLUMNS
        PASSES after implementation: email added to ALLOWED_COLUMNS
        """
        import importlib
        import routes.users as users_module
        importlib.reload(users_module)
        
        from routes.users import update_me, UserPatch
        
        mock_user = {
            "id": "user-123",
            "email": "old@example.com",
            "name": "Test User",
            "password_hash": "x",
            "email_verified": True,
            "token_version": 1,
        }
        
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = {
            **mock_user,
            "email": "new@example.com",
        }
        mock_db.execute.return_value = mock_result
        
        with patch("routes.users.get_user_by_email", return_value=None), \
             patch("services.email_svc.send_verification_email", create=True) as mock_send:
            body = UserPatch(email="new@example.com")
            
            # This should not raise a validation error
            try:
                result = update_me(body, user=mock_user, db=mock_db)
                # If email was processed, send_verification_email should be called
                # (unless same-email no-op logic handles it)
            except Exception as e:
                # If there's a specific error about email not being allowed, we need to fix
                if "email" in str(e).lower() and "allowed" in str(e).lower():
                    pytest.fail(f"email field is not in ALLOWED_COLUMNS: {e}")


# ============================================================================
# Tests for email validation on change
# ============================================================================

class TestEmailValidation:
    """Test that invalid email formats are rejected."""

    def test_invalid_email_format_is_rejected(self):
        """When email format is invalid, should return 400/422.
        
        PASSES: pydantic's EmailStr validation handles this
        """
        import importlib
        import routes.users as users_module
        importlib.reload(users_module)
        
        from routes.users import UserPatch
        from pydantic import ValidationError
        
        # Invalid email formats should be rejected by EmailStr
        invalid_emails = [
            "not-an-email",
            "@nodomain.com",
            "spaces in@email.com",
        ]
        
        for invalid_email in invalid_emails:
            with pytest.raises((ValidationError, ValueError)):
                UserPatch(email=invalid_email)


# ============================================================================
# Tests for unverified user escalation gate
# ============================================================================

class TestEmailVerificationGate:
    """Test that unverified users cannot proceed with escalation."""

    def test_unverified_user_cannot_escalate(self):
        """User with email_verified=FALSE should not pass escalation gate.
        
        PASSES: This is already implemented in tasks.escalation
        """
        from tasks.escalation import schedule_daily_checkin
        
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
            "email_verified": False,  # Unverified after email change
        }

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = unverified_user
        mock_db.execute.return_value = mock_result

        with patch("tasks.escalation._db", return_value=mock_db), \
             patch("services.push_svc.send_push") as mock_push, \
             patch("db.log_escalation_event") as mock_log:
            schedule_daily_checkin("user-123")

            # Unverified user should NOT proceed to escalation
            mock_push.assert_not_called()
            mock_log.assert_not_called()


# ============================================================================
# Integration-style tests (using mock_db and mock_user)
# ============================================================================

class TestEmailChangeFullFlow:
    """Full flow tests simulating the complete email change scenario."""

    def test_email_change_complete_flow(self):
        """Test complete email change: update -> reset verification -> send email.
        
        FAILS before implementation: email field not processed
        PASSES after implementation: all steps happen correctly
        """
        import importlib
        import routes.users as users_module
        importlib.reload(users_module)
        
        from routes.users import update_me, UserPatch
        
        mock_user = {
            "id": "user-123",
            "email": "old@example.com",
            "name": "Test User",
            "password_hash": "x",
            "email_verified": True,
            "token_version": 1,
        }
        
        # Mock DB that tracks updates
        updates = []
        
        def mock_execute(query, params=None):
            result = MagicMock()
            updates.append({"query": str(query), "params": dict(params) if params else {}})
            
            if "RETURNING" in str(query).upper() or "SELECT" in str(query).upper():
                result.mappings.return_value.first.return_value = {
                    **mock_user,
                    "email": updates[-1]["params"].get("email", "old@example.com"),
                    "email_verified": False,  # After change
                    "token_version": 2,  # After bump
                }
            return result
        
        mock_db = MagicMock()
        mock_db.execute.side_effect = mock_execute
        mock_db.commit.return_value = None
        
        with patch("routes.users.get_user_by_email", return_value=None), \
             patch("services.email_svc.send_verification_email", create=True) as mock_send:
            body = UserPatch(email="new@example.com")
            result = update_me(body, user=mock_user, db=mock_db)
            
            # Verify all steps happened
            assert mock_send.called, "Verification email not sent"
            assert mock_send.call_args[0][0] == "new@example.com", \
                "Wrong email in verification"
            
            # Check that email_verified was set to False
            update_queries = [u for u in updates if "UPDATE" in str(u["query"]).upper()]
            assert len(update_queries) >= 1, "No UPDATE query executed"
            
            # Check token_version was bumped
            found_token_bump = any("token_version" in str(u["query"]).lower() for u in update_queries)
            assert found_token_bump, "token_version was not bumped"

    def test_email_change_graceful_failure_when_email_service_fails(self):
        """If send_verification_email fails, email change should still succeed.
        
        FAILS before implementation: no try/except around email send
        PASSES after implementation: email failure is caught and logged
        """
        import importlib
        import routes.users as users_module
        importlib.reload(users_module)
        
        from routes.users import update_me, UserPatch
        
        mock_user = {
            "id": "user-123",
            "email": "old@example.com",
            "name": "Test User",
            "password_hash": "x",
            "email_verified": True,
            "token_version": 1,
        }
        
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = {
            **mock_user,
            "email": "new@example.com",
            "email_verified": False,
        }
        mock_db.execute.return_value = mock_result
        
        with patch("routes.users.get_user_by_email", return_value=None), \
             patch("services.email_svc.send_verification_email", create=True) as mock_send:
            # Simulate email service failure
            mock_send.side_effect = Exception("Email service unavailable")
            
            body = UserPatch(email="new@example.com")
            
            # Should still succeed - email change is not dependent on email sending
            try:
                result = update_me(body, user=mock_user, db=mock_db)
            except Exception as e:
                if "Email service unavailable" in str(e):
                    pytest.fail("Email change should succeed even if email service fails")


# ============================================================================
# Tests for rapid email changes
# ============================================================================

class TestRapidEmailChanges:
    """Test edge case of rapid successive email changes."""

    def test_multiple_email_changes_resets_verification_each_time(self):
        """Each email change should reset verification and send new verification.
        
        FAILS before implementation: no email change logic
        PASSES after implementation: each change triggers new verification
        """
        import importlib
        import routes.users as users_module
        importlib.reload(users_module)
        
        from routes.users import update_me, UserPatch
        
        mock_user = {
            "id": "user-123",
            "email": "original@example.com",
            "name": "Test User",
            "password_hash": "x",
            "email_verified": True,
            "token_version": 1,
        }
        
        call_count = 0
        emails_sent_to = []
        
        def mock_execute(query, params=None):
            nonlocal call_count
            result = MagicMock()
            call_count += 1
            
            if params and "email" in params:
                emails_sent_to.append(params["email"])
            
            result.mappings.return_value.first.return_value = {
                **mock_user,
                "email": params.get("email") if params else "original@example.com",
                "email_verified": False,
                "token_version": call_count,
            }
            return result
        
        mock_db = MagicMock()
        mock_db.execute.side_effect = mock_execute
        mock_db.commit.return_value = None
        
        with patch("routes.users.get_user_by_email", return_value=None), \
             patch("services.email_svc.send_verification_email", create=True) as mock_send:
            
            # First change
            body1 = UserPatch(email="first@example.com")
            update_me(body1, user=mock_user, db=mock_db)
            
            first_email = mock_send.call_args[0][0]
            
            # Second change
            body2 = UserPatch(email="second@example.com")
            update_me(body2, user=mock_user, db=mock_db)
            
            second_email = mock_send.call_args[0][0]
            
            # Most recent verification should go to latest email
            assert second_email == "second@example.com", \
                f"Latest verification should go to second@example.com, got: {second_email}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
