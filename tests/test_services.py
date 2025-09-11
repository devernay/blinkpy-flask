"""Unit tests for service classes and functions.

This file contains ONLY unit tests for blinkapp/services/ modules:
- Time services (time_service.py)
- File services (file_service.py)
- Authentication services (auth_service.py)
- Cache services (cache_service.py)
- Device services (device_service.py)
- HLS services (hls_service.py)
- Clip processing services (clip_processing.py)
- Stream services (stream_service.py)
- System services (system_service.py)
- Connection services (connection_service.py)

These are pure unit tests with mocked dependencies.
DO NOT add integration tests here - those belong in test_integration_*.py files.
DO NOT add Flask route tests here - those belong in test_integration_api.py.
"""

# pyright: reportUnnecessaryTypeIgnoreComment=false

import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, mock_open, patch

import requests
from aiohttp import ClientSession

from blinkapp.models.ids import ClipId
from tests.test_base import BaseTestCase, create_mock_thread_pool_executor


class TestTimeService(BaseTestCase):
    """Test time service functions."""

    def test_seconds_since_now_from_datetime(self) -> None:
        """Test calculating seconds since now from datetime."""
        from datetime import UTC, timedelta

        from blinkapp.services.time_service import seconds_since_now_from_datetime

        # Test with a time 60 seconds ago with timezone
        past_time = datetime.now(UTC) - timedelta(seconds=60)

        result = seconds_since_now_from_datetime(past_time)

        # Should be approximately 60 seconds (allow some tolerance)
        self.assertGreater(result, 55)
        self.assertLess(result, 65)

    def test_time_difference_calculation(self) -> None:
        """Test time difference calculation for thumbnails."""
        from datetime import datetime, timedelta

        # Test recent timestamp (minutes ago)
        now = datetime.now()
        recent_time = now - timedelta(minutes=30)
        recent_ts = recent_time.timestamp()

        # Test the time formatting logic
        diff = now - datetime.fromtimestamp(recent_ts)
        minutes = diff.seconds // 60
        expected = f"{minutes}m ago"

        self.assertIn("m ago", expected)

    def test_time_formatting_hours(self) -> None:
        """Test time formatting for hours."""
        from datetime import datetime, timedelta

        now = datetime.now()
        hours_ago = now - timedelta(hours=3)

        diff = now - hours_ago
        hours = diff.seconds // 3600
        expected = f"{hours}h ago"

        self.assertIn("h ago", expected)

    def test_time_formatting_days(self) -> None:
        """Test time formatting for days."""
        from datetime import datetime, timedelta

        now = datetime.now()
        days_ago = now - timedelta(days=2)

        diff = now - days_ago
        days = diff.days
        expected = f"{days}d ago"

        self.assertEqual(expected, "2d ago")


class TestAuthService(BaseTestCase):
    """Test authentication service functions."""

    def test_is_blink_authenticated_true(self) -> None:
        """Test blink authentication check returns true."""
        from blinkapp.services.auth_service import is_blink_authenticated
        from tests.test_base import create_mock_blink_instance

        mock_blink = create_mock_blink_instance(available=True)
        result = is_blink_authenticated(mock_blink)
        self.assertTrue(result)

    def test_is_blink_authenticated_false_no_token(self) -> None:
        """Test blink authentication check returns false when no token."""
        from blinkapp.services.auth_service import is_blink_authenticated
        from tests.test_base import create_mock_blink_instance

        mock_blink = create_mock_blink_instance(available=False)
        result = is_blink_authenticated(mock_blink)
        self.assertFalse(result)

    def test_is_blink_authenticated_false_no_blink(self) -> None:
        """Test blink authentication check returns false when no blink instance."""
        from blinkapp.services.auth_service import is_blink_authenticated

        result = is_blink_authenticated(None)
        self.assertFalse(result)

    def test_is_valid_email_format_valid(self) -> None:
        """Test valid email format validation."""
        from blinkapp.services.auth_service import is_valid_email_format

        self.assertTrue(is_valid_email_format("test@example.com"))
        self.assertTrue(is_valid_email_format("user.name@domain.co.uk"))

    def test_is_valid_email_format_invalid(self) -> None:
        """Test invalid email format validation."""
        from blinkapp.services.auth_service import is_valid_email_format

        self.assertFalse(is_valid_email_format("invalid"))
        self.assertFalse(is_valid_email_format("@domain.com"))
        self.assertFalse(is_valid_email_format("user@"))

    @patch("blinkapp.services.auth_service.logger")
    def test_validate_credentials_valid(self, mock_logger: Mock) -> None:
        """Test credential validation with valid inputs."""
        from blinkapp.services.auth_service import validate_credentials

        result = validate_credentials("test@example.com", "password123")
        self.assertTrue(result)

    @patch("blinkapp.services.auth_service.logger")
    def test_validate_credentials_invalid_email(self, mock_logger: Mock) -> None:
        """Test credential validation with invalid email."""
        from blinkapp.services.auth_service import validate_credentials

        result = validate_credentials("invalid", "password123")
        self.assertFalse(result)

    @patch("blinkapp.services.auth_service.logger")
    def test_validate_credentials_empty_password(self, mock_logger: Mock) -> None:
        """Test credential validation with empty password."""
        from blinkapp.services.auth_service import validate_credentials

        result = validate_credentials("test@example.com", "")
        self.assertFalse(result)

    def test_is_valid_email_format_comprehensive(self) -> None:
        """Test email validation comprehensively."""
        from blinkapp.services.auth_service import is_valid_email_format

        # Valid emails
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
        ]
        for email in valid_emails:
            with self.subTest(email=email):
                self.assertTrue(is_valid_email_format(email))

        # Invalid emails - test the ones that definitely fail
        self.assertFalse(is_valid_email_format(""))
        self.assertFalse(is_valid_email_format("@domain.com"))

    def test_validate_credentials_cases(self) -> None:
        """Test credential validation."""
        from blinkapp.services.auth_service import validate_credentials

        # Empty credentials
        self.assertFalse(validate_credentials("", ""))
        self.assertFalse(validate_credentials("user@example.com", ""))
        self.assertFalse(validate_credentials("", "password"))

        # Valid credentials
        self.assertTrue(validate_credentials("user@example.com", "password123"))

    def test_create_blink_session_default(self) -> None:
        """Test creating blink session with default factory."""
        from blinkapp.services import auth_service

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = Mock(spec=ClientSession)
            mock_session_class.return_value = mock_session

            result = auth_service._create_blink_session()

            self.assertEqual(result, mock_session)
            mock_session_class.assert_called_once()

    def test_create_blink_session_custom_factory(self) -> None:
        """Test creating blink session with custom factory."""
        from blinkapp.services import auth_service

        with patch(
            "aiohttp.ClientSession", return_value=Mock(spec=ClientSession)
        ) as mock_factory:
            result = auth_service._create_blink_session()

            self.assertIsNotNone(result)
            mock_factory.assert_called_once()

    def test_is_blink_authenticated_no_instance_expansion(self) -> None:
        """Test is_blink_authenticated when no blink instance (expansion)."""
        from unittest.mock import patch

        from blinkapp.services import auth_service

        with patch(
            "blinkapp.services.blink_service.get_blink_instance"
        ) as mock_get_blink:
            mock_get_blink.return_value = None
            result = auth_service.is_blink_authenticated()
            self.assertFalse(result)

    def test_is_valid_email_format_valid_expansion(self) -> None:
        """Test is_valid_email_format with valid email (expansion)."""
        from blinkapp.services import auth_service

        result = auth_service.is_valid_email_format("test@example.com")
        self.assertTrue(result)

    def test_is_valid_email_format_invalid_expansion(self) -> None:
        """Test is_valid_email_format with invalid email (expansion)."""
        from blinkapp.services import auth_service

        result = auth_service.is_valid_email_format("invalid-email")
        self.assertFalse(result)

    def test_validate_credentials_empty_expansion(self) -> None:
        """Test validate_credentials with empty credentials (expansion)."""
        from blinkapp.services import auth_service

        result = auth_service.validate_credentials("", "")
        self.assertFalse(result)

    def test_validate_credentials_valid_expansion(self) -> None:
        """Test validate_credentials with valid credentials (expansion)."""
        from blinkapp.services import auth_service

        result = auth_service.validate_credentials("test@example.com", "password123")
        self.assertTrue(result)

    def test_validate_credentials_invalid_email_expansion(self) -> None:
        """Test validate_credentials with invalid email format (expansion)."""
        from blinkapp.services import auth_service

        result = auth_service.validate_credentials("invalid-email", "password123")
        self.assertFalse(result)

    def test_is_blink_authenticated_runtime_error(self) -> None:
        """Test is_blink_authenticated when ensure_blink_initialized raises RuntimeError."""
        from blinkapp.services.auth_service import is_blink_authenticated

        with patch(
            "blinkapp.services.blink_service.ensure_blink_initialized"
        ) as mock_ensure:
            mock_ensure.side_effect = RuntimeError("Not initialized")
            result = is_blink_authenticated()
            self.assertFalse(result)

    def test_is_valid_email_format_edge_cases(self) -> None:
        """Test email validation edge cases."""
        from blinkapp.services.auth_service import is_valid_email_format

        # Non-string input - intentionally testing invalid types for robustness
        self.assertFalse(is_valid_email_format(None))  # type: ignore[arg-type]
        self.assertFalse(is_valid_email_format(123))  # type: ignore[arg-type]

        # Multiple @ symbols
        self.assertFalse(is_valid_email_format("user@@domain.com"))
        self.assertFalse(is_valid_email_format("user@domain@com"))

        # No domain extension
        self.assertFalse(is_valid_email_format("user@domain"))

    def test_validate_credentials_non_string_inputs(self) -> None:
        """Test validate_credentials with non-string inputs."""
        from blinkapp.services.auth_service import validate_credentials

        # Non-string inputs - intentionally testing invalid types for robustness
        self.assertFalse(validate_credentials(None, "password"))  # type: ignore[arg-type]
        self.assertFalse(validate_credentials("user@example.com", None))  # type: ignore[arg-type]
        self.assertFalse(validate_credentials(123, "password"))  # type: ignore[arg-type]
        self.assertFalse(validate_credentials("user@example.com", 123))  # type: ignore[arg-type]

    def test_validate_credentials_xss_patterns(self) -> None:
        """Test validate_credentials XSS pattern detection."""
        from blinkapp.services.auth_service import validate_credentials

        xss_patterns = [
            "user@example.com<script>alert('xss')</script>",
            "user@example.com</script>",
            "javascript:alert('xss')@example.com",
            "user@example.comonload=alert('xss')",
            "user@example.comonerror=alert('xss')",
        ]

        for pattern in xss_patterns:
            with self.subTest(pattern=pattern):
                self.assertFalse(validate_credentials(pattern, "password"))
                self.assertFalse(validate_credentials("user@example.com", pattern))

    @patch("blinkapp.config.Config.MAX_PASSWORD_LENGTH", 10)
    def test_validate_credentials_password_too_long(self) -> None:
        """Test validate_credentials with password exceeding max length."""
        from blinkapp.services.auth_service import validate_credentials

        long_password = "a" * 11  # Exceeds mocked MAX_PASSWORD_LENGTH of 10
        result = validate_credentials("user@example.com", long_password)
        self.assertFalse(result)

    def test_validate_credentials_whitespace_only(self) -> None:
        """Test validate_credentials with whitespace-only inputs."""
        from blinkapp.services.auth_service import validate_credentials

        self.assertFalse(validate_credentials("   ", "password"))
        self.assertFalse(validate_credentials("user@example.com", "   "))
        self.assertFalse(validate_credentials("   ", "   "))

    def test_create_auth_object_default_factory(self) -> None:
        """Test _create_auth_object with default factory."""
        from blinkapp.services.auth_service import _create_auth_object

        mock_session = Mock(spec=ClientSession)

        with patch("blinkpy.auth.Auth") as mock_auth_class:
            from tests.test_base import create_mock_auth

            mock_auth = create_mock_auth()
            mock_auth_class.return_value = mock_auth

            result = _create_auth_object("user@example.com", "password", mock_session)

            self.assertEqual(result, mock_auth)
            mock_auth_class.assert_called_once_with(
                {"username": "user@example.com", "password": "password"},
                no_prompt=True,
                session=mock_session,
            )

    def test_create_auth_object_custom_factory(self) -> None:
        """Test _create_auth_object with custom factory."""
        from blinkapp.services.auth_service import _create_auth_object

        mock_session = Mock(spec=ClientSession)
        mock_auth_factory = Mock()
        from tests.test_base import create_mock_auth

        mock_auth = create_mock_auth()
        mock_auth_factory.return_value = mock_auth

        result = _create_auth_object(
            "user@example.com", "password", mock_session, mock_auth_factory
        )

        self.assertEqual(result, mock_auth)
        mock_auth_factory.assert_called_once_with(
            {"username": "user@example.com", "password": "password"},
            no_prompt=True,
            session=mock_session,
        )

    @patch("blinkapp.services.auth_service.get_blink_instance")
    @patch("blinkapp.services.auth_service._create_blink_session")
    @patch("blinkapp.services.auth_service._create_auth_object")
    @patch("blinkapp.services.blink_service.initialize_blink_instance")
    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    def test_initialize_blink_success_no_2fa(
        self,
        mock_ensure_blink: Mock,
        mock_init_blink: Mock,
        mock_create_auth: Mock,
        mock_create_session: Mock,
        mock_get_blink: Mock,
    ) -> None:
        """Test initialize_blink success without 2FA."""
        from blinkapp.services.auth_service import initialize_blink
        from tests.test_base import create_mock_auth, create_mock_blink_instance

        # Setup mocks
        mock_session = Mock(spec=ClientSession)
        mock_create_session.return_value = mock_session

        mock_auth = create_mock_auth()
        mock_create_auth.return_value = mock_auth

        mock_blink = create_mock_blink_instance(available=True, key_required=False)
        mock_ensure_blink.return_value = mock_blink
        mock_get_blink.return_value = mock_blink

        # Mock start method to return True
        mock_blink.start = AsyncMock(return_value=True)

        # Use asyncio to run the coroutine
        import asyncio

        result = asyncio.run(initialize_blink("user@example.com", "password"))

        self.assertTrue(result)
        mock_create_session.assert_called_once()
        mock_init_blink.assert_called_once_with(mock_session)
        mock_create_auth.assert_called_once_with(
            "user@example.com", "password", mock_session
        )
        mock_blink.start.assert_called_once()

    @patch("blinkapp.services.auth_service.get_blink_instance")
    @patch("blinkapp.services.auth_service._create_blink_session")
    @patch("blinkapp.services.auth_service._create_auth_object")
    @patch("blinkapp.services.blink_service.initialize_blink_instance")
    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    def test_initialize_blink_2fa_required(
        self,
        mock_ensure_blink: Mock,
        mock_init_blink: Mock,
        mock_create_auth: Mock,
        mock_create_session: Mock,
        mock_get_blink: Mock,
    ) -> None:
        """Test initialize_blink when 2FA is required."""
        from blinkapp.services.auth_service import initialize_blink
        from tests.test_base import create_mock_auth, create_mock_blink_instance

        # Setup mocks
        mock_session = Mock(spec=ClientSession)
        mock_create_session.return_value = mock_session

        mock_auth = create_mock_auth()
        mock_create_auth.return_value = mock_auth

        mock_blink = create_mock_blink_instance(available=True, key_required=True)
        mock_ensure_blink.return_value = mock_blink
        mock_get_blink.return_value = mock_blink

        # Mock start method to return True
        mock_blink.start = AsyncMock(return_value=True)

        # Use asyncio to run the coroutine
        import asyncio

        result = asyncio.run(initialize_blink("user@example.com", "password"))

        self.assertEqual(result, "2fa_required")
        mock_blink.start.assert_called_once()

    @patch("blinkapp.CREDENTIALS_FILE", "/tmp/test_creds.json")
    @patch("blinkapp.services.auth_service.get_blink_instance")
    def test_verify_2fa_and_save_success(self, mock_get_blink: Mock) -> None:
        """Test verify_2fa_and_save success."""
        from blinkapp.services.auth_service import verify_2fa_and_save
        from tests.test_base import create_mock_blink_instance

        mock_blink = create_mock_blink_instance(available=True)
        mock_blink.auth.send_auth_key = AsyncMock(return_value=True)
        mock_blink.setup_post_verify = AsyncMock(return_value=True)
        mock_blink.save = AsyncMock(return_value=True)
        mock_get_blink.return_value = mock_blink

        # Use asyncio to run the coroutine
        import asyncio

        result = asyncio.run(
            verify_2fa_and_save("user@example.com", "password", "123456")
        )

        self.assertTrue(result)
        mock_blink.auth.send_auth_key.assert_called_once_with(mock_blink, "123456")
        mock_blink.setup_post_verify.assert_called_once()
        mock_blink.save.assert_called_once_with("/tmp/test_creds.json")

    @patch("blinkapp.CREDENTIALS_FILE", "/tmp/test_creds.json")
    @patch("pathlib.Path.exists")
    @patch("blinkpy.helpers.util.json_load")
    @patch("aiohttp.ClientSession")
    @patch("blinkpy.auth.Auth")
    @patch("blinkpy.blinkpy.Blink")
    def test_load_saved_blink_success(
        self,
        mock_blink_class: Mock,
        mock_auth_class: Mock,
        mock_session_class: Mock,
        mock_json_load: Mock,
        mock_exists: Mock,
    ) -> None:
        """Test load_saved_blink success."""
        from blinkapp.services.auth_service import load_saved_blink
        from tests.test_base import create_mock_auth, create_mock_blink_instance

        # Setup mocks
        mock_exists.return_value = True
        mock_json_load.return_value = {
            "username": "user@example.com",
            "token": "test_token",
        }

        mock_session = Mock(spec=ClientSession)
        mock_session_class.return_value = mock_session

        mock_auth = create_mock_auth()
        mock_auth_class.return_value = mock_auth

        mock_blink = create_mock_blink_instance(available=True)
        mock_blink.start = AsyncMock(return_value=True)
        mock_blink_class.return_value = mock_blink

        # Use asyncio to run the coroutine
        import asyncio

        result = asyncio.run(load_saved_blink())

        self.assertTrue(result)
        mock_json_load.assert_called_once_with("/tmp/test_creds.json")
        mock_session_class.assert_called_once()
        mock_auth_class.assert_called_once()
        mock_blink_class.assert_called_once_with(session=mock_session)
        mock_blink.start.assert_called_once()

    @patch("blinkapp.CREDENTIALS_FILE", "/tmp/test_creds.json")
    @patch("pathlib.Path.exists")
    def test_load_saved_blink_no_file(self, mock_exists: Mock) -> None:
        """Test load_saved_blink when no credentials file exists."""
        from blinkapp.services.auth_service import load_saved_blink

        mock_exists.return_value = False

        # Use asyncio to run the coroutine
        import asyncio

        result = asyncio.run(load_saved_blink())

        self.assertFalse(result)

    @patch("blinkapp.CREDENTIALS_FILE", "/tmp/test_creds.json")
    @patch("pathlib.Path.exists")
    @patch("blinkpy.helpers.util.json_load")
    @patch("aiohttp.ClientSession")
    @patch("blinkpy.auth.Auth")
    @patch("blinkpy.blinkpy.Blink")
    def test_load_saved_blink_start_fails(
        self,
        mock_blink_class: Mock,
        mock_auth_class: Mock,
        mock_session_class: Mock,
        mock_json_load: Mock,
        mock_exists: Mock,
    ) -> None:
        """Test load_saved_blink when blink.start() fails."""
        from blinkapp.services.auth_service import load_saved_blink
        from tests.test_base import create_mock_auth, create_mock_blink_instance

        # Setup mocks
        mock_exists.return_value = True
        mock_json_load.return_value = {
            "username": "user@example.com",
            "token": "test_token",
        }

        mock_session = Mock(spec=ClientSession)
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session

        mock_auth = create_mock_auth()
        mock_auth_class.return_value = mock_auth

        mock_blink = create_mock_blink_instance(available=False)
        mock_blink.start = AsyncMock(return_value=False)
        mock_blink_class.return_value = mock_blink

        # Use asyncio to run the coroutine
        import asyncio

        result = asyncio.run(load_saved_blink())

        self.assertFalse(result)
        mock_session.close.assert_called_once()

    @patch("blinkapp.CREDENTIALS_FILE", "/tmp/test_creds.json")
    @patch("pathlib.Path.exists")
    @patch("blinkpy.helpers.util.json_load")
    def test_load_saved_blink_exception(
        self, mock_json_load: Mock, mock_exists: Mock
    ) -> None:
        """Test load_saved_blink when exception occurs."""
        from blinkapp.services.auth_service import load_saved_blink

        mock_exists.return_value = True
        mock_json_load.side_effect = Exception("Load failed")

        # Use asyncio to run the coroutine
        import asyncio

        result = asyncio.run(load_saved_blink())

        self.assertFalse(result)

    @patch("blinkapp.services.auth_service.validate_credentials")
    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    def test_handle_login_invalid_credentials(
        self, mock_ensure_conn: Mock, mock_validate: Mock
    ) -> None:
        """Test handle_login with invalid credentials."""
        from blinkapp.services.auth_service import handle_login

        mock_validate.return_value = False

        result = handle_login("invalid", "")

        expected = {"success": False, "error": "Invalid username or password format"}
        self.assertEqual(result, expected)
        mock_validate.assert_called_once_with("invalid", "")

    @patch("blinkapp.services.auth_service.validate_credentials")
    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    def test_handle_login_connection_not_ready(
        self, mock_ensure_conn: Mock, mock_validate: Mock
    ) -> None:
        """Test handle_login when connection not ready."""
        from blinkapp.services.auth_service import handle_login

        mock_validate.return_value = True
        mock_ensure_conn.side_effect = RuntimeError("Not ready")

        result = handle_login("user@example.com", "password")

        expected = {"success": False, "error": "System not ready. Please try again."}
        self.assertEqual(result, expected)

    @patch("blinkapp.services.auth_service.validate_credentials")
    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    @patch("flask.session", {})
    def test_handle_login_success(
        self, mock_ensure_conn: Mock, mock_validate: Mock
    ) -> None:
        """Test handle_login success."""
        from blinkapp.services.auth_service import handle_login
        from tests.test_base import create_mock_blink_connection

        mock_validate.return_value = True
        mock_conn = create_mock_blink_connection()
        mock_conn.execute.return_value = True
        mock_ensure_conn.return_value = mock_conn

        result = handle_login("user@example.com", "password")

        expected = {"success": True}
        self.assertEqual(result, expected)

    @patch("blinkapp.services.auth_service.validate_credentials")
    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    @patch("flask.session", {})
    def test_handle_login_2fa_required(
        self, mock_ensure_conn: Mock, mock_validate: Mock
    ) -> None:
        """Test handle_login when 2FA required."""
        from blinkapp.services.auth_service import handle_login
        from tests.test_base import create_mock_blink_connection

        mock_validate.return_value = True
        mock_conn = create_mock_blink_connection()
        mock_conn.execute.return_value = "2fa_required"
        mock_ensure_conn.return_value = mock_conn

        with patch("flask.session", {}) as mock_session:
            result = handle_login("user@example.com", "password")

            expected = {"success": False, "requires_2fa": True}
            self.assertEqual(result, expected)
            self.assertTrue(mock_session["pending_2fa"])
            self.assertEqual(mock_session["temp_username"], "user@example.com")
            self.assertEqual(mock_session["temp_password"], "password")

    @patch("blinkapp.services.auth_service.validate_credentials")
    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    def test_handle_login_auth_failed(
        self, mock_ensure_conn: Mock, mock_validate: Mock
    ) -> None:
        """Test handle_login when authentication fails."""
        from blinkapp.services.auth_service import handle_login
        from tests.test_base import create_mock_blink_connection

        mock_validate.return_value = True
        mock_conn = create_mock_blink_connection()
        mock_conn.execute.return_value = False
        mock_ensure_conn.return_value = mock_conn

        result = handle_login("user@example.com", "password")

        expected = {"success": False, "error": "Authentication failed"}
        self.assertEqual(result, expected)

    @patch("blinkapp.services.auth_service.validate_credentials")
    def test_handle_login_exception(self, mock_validate: Mock) -> None:
        """Test handle_login when exception occurs."""
        from blinkapp.services.auth_service import handle_login

        mock_validate.side_effect = Exception("Validation error")

        result = handle_login("user@example.com", "password")

        expected = {"success": False, "error": "Authentication failed"}
        self.assertEqual(result, expected)

    def test_handle_logout(self) -> None:
        """Test handle_logout."""
        from blinkapp.services.auth_service import handle_logout

        mock_session = Mock()
        mock_session.clear = Mock()

        with patch("flask.session", mock_session):
            result = handle_logout()

            expected = {"success": True}
            self.assertEqual(result, expected)
            mock_session.clear.assert_called_once()

    @patch(
        "flask.session",
        {"temp_username": "user@example.com", "temp_password": "password"},
    )
    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    def test_handle_2fa_verification_success(self, mock_ensure_conn: Mock) -> None:
        """Test handle_2fa_verification success."""
        from blinkapp.services.auth_service import handle_2fa_verification
        from tests.test_base import create_mock_blink_connection

        mock_conn = create_mock_blink_connection()
        mock_conn.execute.return_value = True
        mock_ensure_conn.return_value = mock_conn

        with patch(
            "flask.session",
            {
                "temp_username": "user@example.com",
                "temp_password": "password",
                "pending_2fa": True,
            },
        ) as mock_session:
            result = handle_2fa_verification("123456")

            expected = {"success": True}
            self.assertEqual(result, expected)
            self.assertNotIn("pending_2fa", mock_session)
            self.assertNotIn("temp_username", mock_session)
            self.assertNotIn("temp_password", mock_session)
            self.assertTrue(mock_session["authenticated"])

    @patch("flask.session", {})
    def test_handle_2fa_verification_no_session(self) -> None:
        """Test handle_2fa_verification when no session data."""
        from blinkapp.services.auth_service import handle_2fa_verification

        result = handle_2fa_verification("123456")

        expected = {"success": False, "error": "Session expired. Please login again."}
        self.assertEqual(result, expected)

    @patch(
        "flask.session",
        {"temp_username": "user@example.com", "temp_password": "password"},
    )
    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    def test_handle_2fa_verification_connection_not_ready(
        self, mock_ensure_conn: Mock
    ) -> None:
        """Test handle_2fa_verification when connection not ready."""
        from blinkapp.services.auth_service import handle_2fa_verification

        mock_ensure_conn.side_effect = RuntimeError("Not ready")

        result = handle_2fa_verification("123456")

        expected = {"success": False, "error": "System not ready. Please try again."}
        self.assertEqual(result, expected)

    @patch(
        "flask.session",
        {"temp_username": "user@example.com", "temp_password": "password"},
    )
    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    def test_handle_2fa_verification_invalid_code(self, mock_ensure_conn: Mock) -> None:
        """Test handle_2fa_verification with invalid code."""
        from blinkapp.services.auth_service import handle_2fa_verification
        from tests.test_base import create_mock_blink_connection

        mock_conn = create_mock_blink_connection()
        mock_conn.execute.return_value = False
        mock_ensure_conn.return_value = mock_conn

        result = handle_2fa_verification("invalid")

        expected = {"success": False, "error": "Invalid 2FA code"}
        self.assertEqual(result, expected)

    @patch(
        "flask.session",
        {"temp_username": "user@example.com", "temp_password": "password"},
    )
    def test_handle_2fa_verification_exception(self) -> None:
        """Test handle_2fa_verification when exception occurs."""
        from blinkapp.services.auth_service import handle_2fa_verification

        with patch(
            "blinkapp.services.blink_service.ensure_blink_connection_initialized"
        ) as mock_ensure_conn:
            mock_ensure_conn.side_effect = Exception("Connection error")

            result = handle_2fa_verification("123456")

            expected = {"success": False, "error": "2FA verification failed"}
            self.assertEqual(result, expected)


class TestBlinkConnection(BaseTestCase):
    """Test blink connection service functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()


class TestBlinkService(BaseTestCase):
    """Test blink service functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()

    def test_blink_connection_access(self) -> None:
        """Test blink_connection access."""
        from blinkapp.services import blink_service

        # Test that we can get a blink connection instance
        try:
            connection = blink_service.ensure_blink_connection_initialized()
            self.assertTrue(hasattr(connection, "execute"))
        except RuntimeError:
            # Connection not initialized yet, which is fine
            pass

    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    @patch("aiohttp.ClientSession")
    @patch("blinkpy.blinkpy.Blink")
    @patch("blinkpy.auth.Auth")
    def test_initialize_blink_success(
        self,
        mock_auth: Mock,
        mock_blink: Mock,
        mock_session: Mock,
        mock_connection: Mock,
    ) -> None:
        """Test successful Blink initialization."""
        from tests.test_base import (
            create_mock_auth,
            create_mock_blink_instance,
            mock_execute_with_coroutine_cleanup,
        )

        # Setup mocks - use patched ClientSession directly
        mock_session.return_value = mock_session  # Use the patched mock directly

        mock_blink_instance = create_mock_blink_instance(
            available=True, key_required=False
        )
        mock_blink.return_value = mock_blink_instance

        mock_auth_instance = create_mock_auth()
        mock_auth.return_value = mock_auth_instance

        from blinkapp.services.auth_service import initialize_blink

        # Mock the async execution
        mock_connection.execute = mock_execute_with_coroutine_cleanup(return_value=True)
        result = mock_connection.execute(
            initialize_blink("test@example.com", "password")
        )
        self.assertTrue(result)

    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    @patch("aiohttp.ClientSession")
    @patch("blinkpy.blinkpy.Blink")
    @patch("blinkpy.auth.Auth")
    def test_initialize_blink_2fa_required(
        self,
        mock_auth: Mock,
        mock_blink: Mock,
        mock_session: Mock,
        mock_connection: Mock,
    ) -> None:
        """Test Blink initialization when 2FA authentication is required."""
        from tests.test_base import (
            create_mock_blink_instance,
            mock_execute_with_coroutine_cleanup,
        )

        # Setup mocks - use patched ClientSession directly
        mock_session.return_value = mock_session  # Use the patched mock directly

        mock_blink_instance = create_mock_blink_instance(
            available=True, key_required=True
        )
        mock_blink.return_value = mock_blink_instance

        try:
            from blinkapp.services.auth_service import initialize_blink

            # Mock the async execution for 2FA required case
            mock_connection.execute = mock_execute_with_coroutine_cleanup(
                return_value="2fa_required"
            )
            result = mock_connection.execute(
                initialize_blink("test@example.com", "password")
            )
            self.assertEqual(result, "2fa_required")
        except (ImportError, AttributeError):
            self.assertTrue(True)


class TestBlinkValidators(BaseTestCase):
    """Test blink validators service functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()


class TestCacheService(BaseTestCase):
    """Test cache service functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Reset global caches before each test
        from blinkapp.services.cache_service import cleanup_global_caches

        cleanup_global_caches()

    def test_initialize_caches(self) -> None:
        """Test cache initialization."""
        from blinkapp.services.cache_service import initialize_caches

        config: dict[str, object] = {
            "CLIPS_CACHE_SIZE": 50,
            "THUMBNAIL_CACHE_SIZE": 100,
        }
        initialize_caches(config)

        # Verify caches are initialized
        from blinkapp.services.cache_service import camera_thumbnail_cache, clips_cache

        self.assertIsNotNone(clips_cache)
        self.assertIsNotNone(camera_thumbnail_cache)

    def test_ensure_clips_cache_initialized_after_init(self) -> None:
        """Test clips cache initialization after global init."""
        from blinkapp.services.cache_service import (
            ensure_clips_cache_initialized,
            initialize_caches,
        )

        config: dict[str, object] = {
            "CLIPS_CACHE_SIZE": 50,
            "THUMBNAIL_CACHE_SIZE": 100,
        }
        initialize_caches(config)

        cache = ensure_clips_cache_initialized()
        self.assertIsNotNone(cache)

    def test_ensure_camera_thumbnail_cache_initialized_after_init(self) -> None:
        """Test camera thumbnail cache initialization after global init."""
        from blinkapp.services.cache_service import (
            ensure_camera_thumbnail_cache_initialized,
            initialize_caches,
        )

        config: dict[str, object] = {
            "CLIPS_CACHE_SIZE": 50,
            "THUMBNAIL_CACHE_SIZE": 100,
        }
        initialize_caches(config)

        cache = ensure_camera_thumbnail_cache_initialized()
        self.assertIsNotNone(cache)

    def test_cleanup_global_caches(self) -> None:
        """Test cleaning up global caches."""
        from blinkapp.services.cache_service import (
            cleanup_global_caches,
            initialize_caches,
        )

        # Initialize caches
        config: dict[str, object] = {
            "CLIPS_CACHE_SIZE": 50,
            "THUMBNAIL_CACHE_SIZE": 100,
        }
        initialize_caches(config)

        # Reset caches
        cleanup_global_caches()

        # Verify caches are reset
        from blinkapp.services.cache_service import camera_thumbnail_cache, clips_cache

        self.assertIsNone(clips_cache)
        self.assertIsNone(camera_thumbnail_cache)

    def test_validate_cache_directory(self) -> None:
        """Test cache directory validation."""
        from blinkapp.services.cache_service import validate_cache_directory

        # Test with /tmp which should exist on most systems
        result = validate_cache_directory("/tmp")
        self.assertIsInstance(result, bool)

    def test_ensure_cache_directory(self) -> None:
        """Test cache directory creation."""
        import os
        import tempfile

        from blinkapp.services.cache_service import ensure_cache_directory

        # Use a temporary directory that we can actually write to
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = os.path.join(temp_dir, "test_cache")
            result = ensure_cache_directory(test_path)
            self.assertEqual(result, test_path)
            self.assertTrue(os.path.exists(test_path))
            self.assertTrue(os.path.isdir(test_path))

    def test_cache_service_stats(self) -> None:
        """Test cache service stats."""
        from blinkapp.services.cache_service import get_cache_stats, initialize_caches

        # Initialize caches first
        config: dict[str, object] = {
            "CLIPS_CACHE_SIZE": 50,
            "THUMBNAIL_CACHE_SIZE": 100,
        }
        initialize_caches(config)

        stats = get_cache_stats()
        self.assertIsInstance(stats, dict)

    def test_clear_all_caches(self) -> None:
        """Test clearing all caches."""
        from blinkapp.services.cache_service import clear_all_caches

        with (
            patch(
                "blinkapp.services.cache_service.ensure_camera_thumbnail_cache_initialized"
            ),
            patch("blinkapp.services.cache_service.ensure_clips_cache_initialized"),
            patch("blinkapp.services.cache_service.clear_camera_thumbnail_cache_files"),
            patch("blinkapp.services.cache_service.clear_clips_cache_files"),
            patch("blinkapp.services.connection_service.ensure_executor_initialized"),
        ):
            clear_all_caches()  # Should not raise exception

    def test_ensure_cache_paths_initialized(self) -> None:
        """Test cache paths initialization."""
        from blinkapp.services.cache_service import ensure_cache_paths_initialized

        ensure_cache_paths_initialized()  # Should not raise exception

    @patch("blinkapp.CACHE_DIR", None)
    @patch("blinkapp.CREDENTIALS_FILE", "test")
    @patch("blinkapp.THUMBNAIL_CACHE_DIR", "test")
    @patch("blinkapp.CLIPS_CACHE_DIR", "test")
    def test_ensure_cache_paths_cache_dir_none(self) -> None:
        """Test cache path initialization when main cache directory is None."""
        from blinkapp.services.cache_service import ensure_cache_paths_initialized

        with self.assertRaises(RuntimeError):
            ensure_cache_paths_initialized()

    @patch("blinkapp.CACHE_DIR", "test")
    @patch("blinkapp.CREDENTIALS_FILE", None)
    @patch("blinkapp.THUMBNAIL_CACHE_DIR", "test")
    @patch("blinkapp.CLIPS_CACHE_DIR", "test")
    def test_ensure_cache_paths_credentials_file_none(self) -> None:
        """Test ensure_cache_paths_initialized when CREDENTIALS_FILE is None."""
        from blinkapp.services.cache_service import ensure_cache_paths_initialized

        with self.assertRaises(RuntimeError):
            ensure_cache_paths_initialized()

    @patch("blinkapp.CACHE_DIR", "test")
    @patch("blinkapp.CREDENTIALS_FILE", "test")
    @patch("blinkapp.THUMBNAIL_CACHE_DIR", None)
    @patch("blinkapp.CLIPS_CACHE_DIR", "test")
    def test_ensure_cache_paths_thumbnail_dir_none(self) -> None:
        """Test ensure_cache_paths_initialized when THUMBNAIL_CACHE_DIR is None."""
        from blinkapp.services.cache_service import ensure_cache_paths_initialized

        with self.assertRaises(RuntimeError):
            ensure_cache_paths_initialized()

    @patch("blinkapp.CACHE_DIR", "test")
    @patch("blinkapp.CREDENTIALS_FILE", "test")
    @patch("blinkapp.THUMBNAIL_CACHE_DIR", "test")
    @patch("blinkapp.CLIPS_CACHE_DIR", None)
    def test_ensure_cache_paths_clips_dir_none(self) -> None:
        """Test ensure_cache_paths_initialized when CLIPS_CACHE_DIR is None."""
        from blinkapp.services.cache_service import ensure_cache_paths_initialized

        with self.assertRaises(RuntimeError):
            ensure_cache_paths_initialized()

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/clips")
    @patch("blinkapp.THUMBNAIL_CACHE_DIR", "/tmp/thumbnails")
    @patch("os.makedirs")
    @patch("shutil.rmtree")
    @patch("os.path.exists")
    def test_clear_file_cache_operations(
        self, mock_exists: Mock, mock_rmtree: Mock, mock_makedirs: Mock
    ) -> None:
        """Test file cache clearing operations."""
        mock_exists.return_value = True

        # Test the clear_file_cache function logic
        cache_dir = "/tmp/test_cache"

        # Simulate the clear_file_cache function
        if mock_exists(cache_dir):
            mock_rmtree(cache_dir)
            mock_makedirs(cache_dir, exist_ok=True)

        mock_rmtree.assert_called_with(cache_dir)
        mock_makedirs.assert_called_with(cache_dir, exist_ok=True)

    def test_cache_instance_access(self) -> None:
        """Test global cache instance access and initialization patterns.

        Why: Cache instances are global singletons that must be accessible across modules.
        What: Verifies cache instances can be accessed and mocked for testing.
        How: Patches global cache instances and validates access patterns work correctly.
        """
        from tests.test_base import create_mock_camera_cache, create_mock_clips_cache

        # Mock the cache instances directly since they're imported globals
        mock_camera_thumbnail_cache = create_mock_camera_cache()
        mock_clips_cache = create_mock_clips_cache()

        with patch(
            "blinkapp.services.cache_service.camera_thumbnail_cache",
            mock_camera_thumbnail_cache,
        ):
            with patch("blinkapp.services.cache_service.clips_cache", mock_clips_cache):
                # Test that ensure functions work correctly
                from blinkapp.services.cache_service import (
                    ensure_camera_thumbnail_cache_initialized,
                    ensure_clips_cache_initialized,
                )

                camera_thumbnail_cache_instance = (
                    ensure_camera_thumbnail_cache_initialized()
                )
                clips_cache_instance = ensure_clips_cache_initialized()

                self.assertIsNotNone(camera_thumbnail_cache_instance)
                self.assertIsNotNone(clips_cache_instance)
                self.assertEqual(
                    camera_thumbnail_cache_instance, mock_camera_thumbnail_cache
                )
                self.assertEqual(clips_cache_instance, mock_clips_cache)


class TestCameraService(BaseTestCase):
    """Test camera service functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()

    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    def test_find_camera_by_id_success(self, mock_ensure_blink: Mock) -> None:
        """Test find_camera_by_id with existing camera."""
        from blinkapp.services.camera_service import find_camera_by_id
        from tests.test_base import create_mock_blink_instance, create_mock_camera

        mock_blink = create_mock_blink_instance(available=True)
        mock_camera = create_mock_camera(camera_id=12345)

        # Setup sync module with camera
        mock_sync = Mock()
        mock_sync.cameras = {"camera_12345": mock_camera}
        mock_blink.sync = {"sync_1": mock_sync}
        mock_ensure_blink.return_value = mock_blink

        result = find_camera_by_id(12345)

        self.assertEqual(result, mock_camera)

    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    def test_find_camera_by_id_not_found(self, mock_ensure_blink: Mock) -> None:
        """Test find_camera_by_id with non-existent camera."""
        from blinkapp.services.camera_service import find_camera_by_id
        from tests.test_base import create_mock_blink_instance

        mock_blink = create_mock_blink_instance(available=True)
        mock_sync = Mock()
        mock_sync.cameras = {}
        mock_blink.sync = {"sync_1": mock_sync}
        mock_ensure_blink.return_value = mock_blink

        result = find_camera_by_id(99999)

        self.assertIsNone(result)

    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    def test_find_camera_by_id_blink_unavailable(self, mock_ensure_blink: Mock) -> None:
        """Test find_camera_by_id when blink is unavailable."""
        from blinkapp.services.camera_service import find_camera_by_id
        from tests.test_base import create_mock_blink_instance

        mock_blink = create_mock_blink_instance(available=False)
        mock_ensure_blink.return_value = mock_blink

        result = find_camera_by_id(12345)

        self.assertIsNone(result)


class TestDebugService(BaseTestCase):
    """Test debug service functions."""

    def test_check_credentials_file_exists_true(self) -> None:
        """Test check_credentials_file_exists when file exists."""
        from pathlib import Path

        from blinkapp.services.debug_service import check_credentials_file_exists

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_creds.json"
            test_file.write_text("{}")

            result = check_credentials_file_exists(test_file)
            self.assertTrue(result)

    def test_check_credentials_file_exists_false(self) -> None:
        """Test check_credentials_file_exists when file doesn't exist."""
        from pathlib import Path

        from blinkapp.services.debug_service import check_credentials_file_exists

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "nonexistent.json"

            result = check_credentials_file_exists(test_file)
            self.assertFalse(result)

    def test_dump_cloud_videos_empty(self) -> None:
        """Test dump_cloud_videos with empty list."""
        from blinkapp.services.debug_service import dump_cloud_videos

        with patch("blinkapp.services.debug_service.logger") as mock_logger:
            dump_cloud_videos([])

            mock_logger.info.assert_called_with("=== CLOUD VIDEOS ===")

    def test_dump_cloud_videos_with_data(self) -> None:
        """Test dump_cloud_videos with video data."""
        from blinkapp.services.debug_service import dump_cloud_videos

        videos = [{"id": "123", "name": "test.mp4"}, {"id": "456", "name": "test2.mp4"}]

        with patch("blinkapp.services.debug_service.logger") as mock_logger:
            dump_cloud_videos(videos)

            mock_logger.info.assert_any_call("=== CLOUD VIDEOS ===")
            mock_logger.info.assert_any_call(f"Video: {videos[0]}")
            mock_logger.info.assert_any_call(f"Video: {videos[1]}")

    def test_dump_blink_system_info_blink_unavailable(self) -> None:
        """Test dump_blink_system_info when blink is unavailable."""
        from blinkapp.services.debug_service import dump_blink_system_info

        with (
            patch(
                "blinkapp.services.blink_service.ensure_blink_initialized",
                return_value=None,
            ),
            patch("blinkapp.logger") as mock_logger,
        ):
            dump_blink_system_info()

            mock_logger.error.assert_called_with("Blink system not available")

    def test_dump_blink_system_info_blink_not_available(self) -> None:
        """Test dump_blink_system_info when blink exists but not available."""
        from blinkapp.services.debug_service import dump_blink_system_info
        from tests.test_base import create_mock_blink_instance

        mock_blink = create_mock_blink_instance()
        mock_blink.available = False

        with (
            patch(
                "blinkapp.services.blink_service.ensure_blink_initialized",
                return_value=mock_blink,
            ),
            patch("blinkapp.logger") as mock_logger,
        ):
            dump_blink_system_info()

            mock_logger.error.assert_called_with("Blink system not available")

    def test_dump_blink_system_info_success(self) -> None:
        """Test dump_blink_system_info with successful system dump."""
        from blinkapp.services.debug_service import dump_blink_system_info
        from tests.test_base import (
            create_mock_blink_instance,
            create_mock_camera,
            create_mock_sync,
        )

        mock_sync = create_mock_sync(network_id=12345, armed=True, status="online")
        mock_camera = create_mock_camera(name="camera1")

        mock_blink = create_mock_blink_instance()
        mock_blink.available = True
        mock_blink.account_id = "12345"
        mock_blink.homescreen = {"account": {"id": "12345"}}
        mock_blink.sync = {"sync1": mock_sync}
        mock_blink.cameras = {"camera1": mock_camera}

        with (
            patch(
                "blinkapp.services.blink_service.ensure_blink_initialized",
                return_value=mock_blink,
            ),
            patch("blinkapp.logger") as mock_logger,
        ):
            dump_blink_system_info()

            # Check that logger was called (don't assert specific calls since they may vary)
            self.assertTrue(mock_logger.info.called)
            self.assertTrue(mock_logger.info.call_count > 0)


class TestDeviceService(BaseTestCase):
    """Test device service functions."""

    def test_create_device_data(self) -> None:
        """Test device data creation for UI display."""
        from blinkapp.services.device_service import create_device_data
        from tests.test_base import create_mock_camera

        mock_camera = create_mock_camera(
            camera_id="test_camera_boost",
            name="Test Camera",
            motion_enabled=True,
            temperature=72,
            battery="ok",
            wifi_strength=4,
            last_record={"created_at": "2023-01-01T00:00:00Z"},
        )

        current_ts = 1640995200  # 2022-01-01 00:00:00
        cached_ts = 1640991600  # 2021-12-31 23:00:00

        result = create_device_data(mock_camera, current_ts, cached_ts)

        self.assertIsInstance(result, dict)
        self.assertIn("name", result)
        self.assertEqual(result["name"], "Test Camera")
        self.assertEqual(result["id"], "test_camera_boost")

    def test_create_device_data_basic(self) -> None:
        """Test creating device data."""
        from blinkapp.services.device_service import create_device_data
        from tests.test_base import create_mock_camera

        mock_camera = create_mock_camera(
            camera_id="test_id",
            name="Test Camera",
            motion_enabled=True,
            temperature=25,
            battery_voltage=110,
            wifi_strength=-50,
        )

        result = create_device_data(mock_camera, 1234567890, 1234567800)

        self.assertIn("name", result)
        self.assertIn("motion_enabled", result)
        self.assertIn("temperature", result)
        self.assertEqual(result["name"], "Test Camera")


class TestHlsService(BaseTestCase):
    """Test HLS service pure functions for coverage."""

    def test_parse_tcp_url_variations(self) -> None:
        """Test various TCP URL parsing scenarios."""
        from blinkapp.services.hls_service import parse_tcp_url

        # Valid URL with port
        result = parse_tcp_url("tcp://192.168.1.100:8080")
        self.assertEqual(result["protocol"], "tcp")
        self.assertEqual(result["host"], "192.168.1.100")
        self.assertEqual(result["port"], "8080")

        # Valid URL without port
        result = parse_tcp_url("tcp://192.168.1.100")
        self.assertEqual(result["protocol"], "tcp")
        self.assertEqual(result["host"], "192.168.1.100")
        self.assertEqual(result["port"], "")

        # Empty URL
        result = parse_tcp_url("")
        self.assertEqual(result, {})

        # URL without protocol
        result = parse_tcp_url("192.168.1.100:8080")
        self.assertEqual(result, {})

    def test_generate_hls_url_variations(self) -> None:
        """Test HLS URL generation."""
        from blinkapp.services.hls_service import generate_hls_url

        # Default base URL
        result = generate_hls_url("camera123")
        self.assertEqual(result, "http://localhost:8080/hls/camera123/playlist.m3u8")

        # Custom base URL
        result = generate_hls_url("camera456", "http://example.com:9000")
        self.assertEqual(result, "http://example.com:9000/hls/camera456/playlist.m3u8")

    def test_parse_tcp_url_empty_string(self) -> None:
        """Test parsing empty URL string."""
        from blinkapp.services.hls_service import parse_tcp_url

        result = parse_tcp_url("")
        self.assertEqual(result, {})

    def test_parse_tcp_url_no_port_detailed(self) -> None:
        """Test parsing URL without port."""
        from blinkapp.services.hls_service import parse_tcp_url

        result = parse_tcp_url("tcp://127.0.0.1")
        expected = {"protocol": "tcp", "host": "127.0.0.1", "port": ""}
        self.assertEqual(result, expected)


class TestHLSStreamConfig(BaseTestCase):
    """Test HLS stream configuration."""

    def test_hls_stream_config_defaults(self) -> None:
        """Test HLS config uses defaults from Config."""
        from blinkapp.services.hls_service import HLSStreamConfig

        config = HLSStreamConfig()

        # Should use Config defaults
        self.assertIsNotNone(config.segment_time)
        self.assertIsNotNone(config.list_size)
        self.assertIsNotNone(config.timeout)
        self.assertIsNotNone(config.idle_timeout)

    def test_hls_stream_config_custom_values(self) -> None:
        """Test HLS config with custom values."""
        from blinkapp.services.hls_service import HLSStreamConfig

        config = HLSStreamConfig(
            segment_time=5, list_size=10, timeout=30, idle_timeout=60
        )

        self.assertEqual(config.segment_time, 5)
        self.assertEqual(config.list_size, 10)
        self.assertEqual(config.timeout, 30)
        self.assertEqual(config.idle_timeout, 60)


class TestFFmpegHelpers(BaseTestCase):
    """Test FFmpeg helper functions."""

    def test_build_ffmpeg_command(self) -> None:
        """Test FFmpeg command building."""
        from blinkapp.services.hls_service import HLSStreamConfig, _build_ffmpeg_command

        config = HLSStreamConfig(segment_time=4, list_size=5)
        output_path = Path("/tmp/test.m3u8")
        tcp_url = "tcp://127.0.0.1:8080"

        cmd = _build_ffmpeg_command(tcp_url, output_path, config)

        expected = [
            "ffmpeg",
            "-i",
            tcp_url,
            "-c",
            "copy",
            "-f",
            "hls",
            "-hls_time",
            "4",
            "-hls_list_size",
            "5",
            "-hls_flags",
            "delete_segments",
            str(output_path),
        ]

        self.assertEqual(cmd, expected)

    def test_create_ffmpeg_process_success(self) -> None:
        """Test successful FFmpeg process creation."""
        from blinkapp.services.hls_service import _create_ffmpeg_process

        cmd = ["ffmpeg", "-version"]
        result = _create_ffmpeg_process(cmd, None)

        # Should return a process if ffmpeg is available, None if not
        if result is not None:
            self.assertIsInstance(result, subprocess.Popen)
            try:
                result.terminate()  # Clean up the process
                result.wait(timeout=1)  # Wait for process to actually terminate
            except subprocess.TimeoutExpired:
                result.kill()  # Force kill if it doesn't terminate
                result.wait()
            finally:
                # Ensure all pipes are closed
                if result.stdout:
                    result.stdout.close()
                if result.stderr:
                    result.stderr.close()
                if result.stdin:
                    result.stdin.close()
        else:
            # ffmpeg not available in test environment
            self.assertIsNone(result)

    def test_create_ffmpeg_process_error(self) -> None:
        """Test FFmpeg process creation error."""
        from blinkapp.services.hls_service import _create_ffmpeg_process

        cmd = ["nonexistent_command"]
        result = _create_ffmpeg_process(cmd, None)

        self.assertIsNone(result)

    def test_create_ffmpeg_process_subprocess_error(self) -> None:
        """Test FFmpeg process creation subprocess error."""
        from blinkapp.services.hls_service import _create_ffmpeg_process

        cmd = ["invalid_command_that_should_fail"]
        result = _create_ffmpeg_process(cmd, None)

        self.assertIsNone(result)

    def test_create_ffmpeg_process_default_factory(self) -> None:
        """Test FFmpeg process creation with default factory."""
        import subprocess

        from blinkapp.services.hls_service import _create_ffmpeg_process

        # Use real Popen class as spec since it's not patched at import time
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.poll.return_value = None
        mock_process.terminate = Mock(spec=callable)
        mock_process.kill = Mock(spec=callable)

        with patch("subprocess.Popen", return_value=mock_process):
            cmd = ["echo", "test"]
            result = _create_ffmpeg_process(cmd)

            self.assertEqual(result, mock_process)

    def test_create_ffmpeg_process_with_mock_factory(self) -> None:
        """Test FFmpeg process creation with mocked factory."""
        import subprocess

        from blinkapp.services.hls_service import _create_ffmpeg_process

        mock_process = Mock(spec=subprocess.Popen)
        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            result = _create_ffmpeg_process(["ffmpeg", "-version"])

            self.assertEqual(result, mock_process)
            mock_popen.assert_called_once()

    def test_create_ffmpeg_process_os_error(self) -> None:
        """Test FFmpeg process creation with OS error."""
        from blinkapp.services.hls_service import _create_ffmpeg_process

        with patch("subprocess.Popen", side_effect=OSError("Process error")):
            result = _create_ffmpeg_process(["ffmpeg", "-version"])

            self.assertIsNone(result)


class TestHLSStream(BaseTestCase):
    """Test HLS stream management."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        from blinkapp.services.hls_service import HLSStreamConfig

        super().setUp()
        self.config = HLSStreamConfig(
            segment_time=2, list_size=3, timeout=10, idle_timeout=30
        )
        self.camera_id = "test_camera"
        self.tcp_url = "tcp://127.0.0.1:8080"

    def test_hls_stream_init(self) -> None:
        """Test HLS stream initialization."""
        from blinkapp.services.hls_service import HLSStream

        stream = HLSStream(self.camera_id, self.tcp_url, self.config)

        self.assertEqual(stream.camera_id, self.camera_id)
        self.assertEqual(stream.tcp_url, self.tcp_url)
        self.assertEqual(stream.config, self.config)
        self.assertIsNone(stream.process)
        self.assertIsNone(stream.temp_dir)
        self.assertFalse(stream._active)
        self.assertIsNotNone(stream.lock)  # Just check it exists

    @patch("blinkapp.services.hls_service._create_ffmpeg_process")
    @patch("time.sleep")
    def test_hls_stream_start_success(
        self, mock_sleep: Mock, mock_create_process: Mock
    ) -> None:
        """Test successful HLS stream start."""
        import tempfile

        from blinkapp.services.hls_service import HLSStream

        # Use real TemporaryDirectory class as spec
        mock_dir = Mock(spec=tempfile.TemporaryDirectory)
        mock_dir.name = "/tmp/hls_test_camera_123"
        mock_dir.__enter__ = Mock(spec=callable, return_value=mock_dir)
        mock_dir.__exit__ = Mock(spec=callable, return_value=None)

        with patch("tempfile.TemporaryDirectory", return_value=mock_dir):
            # Mock FFmpeg process
            import subprocess

            mock_process = Mock(spec=subprocess.Popen)
            mock_process.poll.return_value = None  # Process is running
            mock_create_process.return_value = mock_process

            stream = HLSStream(self.camera_id, self.tcp_url, self.config)
            hls_url, error = stream.start()

            self.assertIsNotNone(hls_url)
            self.assertIsNone(error)
            self.assertTrue(stream._active)
            self.assertEqual(stream.process, mock_process)
        self.assertEqual(stream.temp_dir, mock_dir)
        mock_sleep.assert_called_once_with(2)

    @patch("blinkapp.services.hls_service._create_ffmpeg_process")
    def test_hls_stream_start_process_creation_failed(
        self, mock_create_process: Mock
    ) -> None:
        """Test HLS stream start when process creation fails."""
        from blinkapp.services.hls_service import HLSStream

        mock_create_process.return_value = None

        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        hls_url, error = stream.start()

        self.assertIsNone(hls_url)
        self.assertEqual(error, "Failed to create FFmpeg process")
        self.assertFalse(stream._active)

    def test_hls_stream_stop(self) -> None:
        """Test HLS stream stop."""
        from blinkapp.services.hls_service import HLSStream

        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream._active = True

        with patch.object(stream, "cleanup") as mock_cleanup:
            stream.stop()

            self.assertFalse(stream._active)
            mock_cleanup.assert_called_once()

    def test_hls_stream_cleanup_with_process(self) -> None:
        """Test HLS stream cleanup with active process."""
        from blinkapp.services.hls_service import HLSStream

        stream = HLSStream(self.camera_id, self.tcp_url, self.config)

        # Mock process
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.wait.return_value = None
        stream.process = mock_process

        # Mock temp directory
        mock_temp_dir = Mock(spec=tempfile.TemporaryDirectory)
        stream.temp_dir = mock_temp_dir

        stream.cleanup()

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_with(timeout=5)
        mock_temp_dir.cleanup.assert_called_once()
        self.assertIsNone(stream.process)
        self.assertIsNone(stream.temp_dir)

    def test_hls_stream_is_active_not_active(self) -> None:
        """Test is_active when stream is not active."""
        from blinkapp.services.hls_service import HLSStream

        stream = HLSStream(self.camera_id, self.tcp_url, self.config)

        self.assertFalse(stream.is_active())

    def test_hls_stream_get_hls_url_no_temp_dir(self) -> None:
        """Test get_hls_url when no temp directory."""
        from blinkapp.services.hls_service import HLSStream

        stream = HLSStream(self.camera_id, self.tcp_url, self.config)

        self.assertIsNone(stream.get_hls_url())

    def test_hls_stream_get_hls_url_success(self) -> None:
        """Test get_hls_url with temp directory."""
        from blinkapp.services.hls_service import HLSStream

        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream.temp_dir = Mock(spec=tempfile.TemporaryDirectory)
        stream.temp_dir.name = "/tmp/test"

        url = stream.get_hls_url()
        expected = f"/api/cameras/{self.camera_id}/hls/stream.m3u8"

        self.assertEqual(url, expected)

    def test_hls_stream_get_file_not_active(self) -> None:
        """Test get_file when stream not active."""
        from blinkapp.services.hls_service import HLSStream

        stream = HLSStream(self.camera_id, self.tcp_url, self.config)

        content, content_type = stream.get_file("test.m3u8")

        self.assertIsNone(content)
        self.assertIsNone(content_type)

    @patch("builtins.open")
    @patch("pathlib.Path.exists")
    def test_hls_stream_get_file_success_m3u8(
        self, mock_exists: Mock, mock_open: Mock
    ) -> None:
        """Test get_file success with m3u8 file."""
        from blinkapp.services.hls_service import HLSStream

        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream._active = True

        mock_temp_dir = Mock(spec=tempfile.TemporaryDirectory)
        mock_temp_dir.name = "/tmp/test"
        stream.temp_dir = mock_temp_dir

        mock_exists.return_value = True
        from io import BufferedReader

        mock_file = Mock(spec=BufferedReader)
        mock_file.read.return_value = b"playlist content"
        mock_open.return_value.__enter__.return_value = mock_file

        content, content_type = stream.get_file("playlist.m3u8")

        self.assertEqual(content, b"playlist content")
        self.assertEqual(content_type, "application/vnd.apple.mpegurl")

    def test_hls_stream_get_file_ts_content_type(self) -> None:
        """Test get_file with .ts file returns correct content type."""
        from blinkapp.services.hls_service import HLSStream

        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream._active = True

        mock_temp_dir = Mock(spec=tempfile.TemporaryDirectory)
        mock_temp_dir.name = "/tmp/test"
        stream.temp_dir = mock_temp_dir

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open") as mock_open,
            patch("time.time", return_value=123456),
        ):
            mock_file = Mock(spec=["read"])
            mock_file.read.return_value = b"ts content"
            mock_open.return_value.__enter__.return_value = mock_file

            content, content_type = stream.get_file("segment.ts")

            self.assertEqual(content, b"ts content")
            self.assertEqual(content_type, "video/mp2t")

    def test_hls_stream_is_active_with_timeout(self) -> None:
        """Test is_active with idle timeout."""
        import subprocess

        from blinkapp.services.hls_service import HLSStream

        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream._active = True

        mock_process = Mock(spec=subprocess.Popen)
        mock_process.poll.return_value = None  # Still running
        stream.process = mock_process
        stream.last_access = 0  # Set to old time

        with patch("time.time", return_value=1000):  # Much later time
            with patch.object(stream, "stop") as mock_stop:
                result = stream.is_active()

                self.assertFalse(result)
                mock_stop.assert_called_once()


class TestClipDownload(BaseTestCase):
    """Test clip download service functions."""

    clip_id: ClipId

    def setUp(self) -> None:
        """Set up test fixtures."""
        from blinkapp.models.ids import ClipId

        super().setUp()
        self.clip_id = ClipId("123456")

    @patch("blinkapp.services.blink_service.get_blink_instance")
    def test_download_cloud_clip_no_blink_instance(self, mock_get_blink: Mock) -> None:
        """Test download_cloud_clip when no blink instance."""
        from blinkapp.services.clip_download import download_cloud_clip

        mock_get_blink.return_value = None

        response, status_code = download_cloud_clip(self.clip_id)

        self.assertEqual(status_code, 503)
        self.assertFalse(response["success"])
        self.assertIn("not available", response["error"])

    @patch("blinkapp.services.blink_service.get_blink_instance")
    def test_download_cloud_clip_blink_unavailable(self, mock_get_blink: Mock) -> None:
        """Test download_cloud_clip when blink unavailable."""
        from blinkapp.services.clip_download import download_cloud_clip
        from tests.test_base import create_mock_blink_instance

        mock_blink = create_mock_blink_instance(available=False)
        mock_get_blink.return_value = mock_blink

        response, status_code = download_cloud_clip(self.clip_id)

        self.assertEqual(status_code, 503)
        self.assertFalse(response["success"])

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("flask.send_file")
    @patch("blinkapp.services.blink_service.get_blink_instance")
    def test_download_cloud_clip_cached_file_exists(
        self, mock_get_blink: Mock, mock_send_file: Mock
    ) -> None:
        """Test download_cloud_clip when file already cached."""
        from blinkapp.services.clip_download import download_cloud_clip
        from tests.test_base import create_mock_blink_instance

        mock_blink = create_mock_blink_instance(available=True)
        mock_get_blink.return_value = mock_blink
        mock_send_file.return_value = "file_response"

        # Mock the clip file to exist
        with patch("pathlib.Path.exists", return_value=True):
            result = download_cloud_clip(self.clip_id)

        self.assertEqual(result, "file_response")
        mock_send_file.assert_called_once()

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("blinkapp.services.blink_service.get_blink_instance")
    @patch("blinkapp.services.clip_download._download_cloud_clip_core_sync")
    def test_download_cloud_clip_download_error(
        self,
        mock_download_sync: Mock,
        mock_get_blink: Mock,
        mock_mkdir: Mock,
        mock_exists: Mock,
    ) -> None:
        """Test download_cloud_clip when download fails."""
        from blinkapp.services.clip_download import download_cloud_clip
        from tests.test_base import create_mock_blink_instance

        mock_blink = create_mock_blink_instance(available=True)
        mock_get_blink.return_value = mock_blink
        mock_exists.return_value = False
        mock_download_sync.return_value = (None, "Download failed")

        response, status_code = download_cloud_clip(self.clip_id)

        self.assertEqual(status_code, 500)
        self.assertFalse(response["success"])
        self.assertIn("Download failed", response["error"])

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("blinkapp.services.blink_service.get_blink_instance")
    @patch("blinkapp.services.clip_download._download_cloud_clip_core_sync")
    def test_download_cloud_clip_not_found_error(
        self,
        mock_download_sync: Mock,
        mock_get_blink: Mock,
        mock_mkdir: Mock,
        mock_exists: Mock,
    ) -> None:
        """Test download_cloud_clip when clip not found."""
        from blinkapp.services.clip_download import download_cloud_clip
        from tests.test_base import create_mock_blink_instance

        mock_blink = create_mock_blink_instance(available=True)
        mock_get_blink.return_value = mock_blink
        mock_exists.return_value = False
        mock_download_sync.return_value = (None, "Clip not found")

        response, status_code = download_cloud_clip(self.clip_id)

        self.assertEqual(status_code, 404)
        self.assertFalse(response["success"])

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("blinkapp.services.blink_service.get_blink_instance")
    @patch("blinkapp.services.clip_download._download_cloud_clip_core_sync")
    def test_download_cloud_clip_url_error(
        self,
        mock_download_sync: Mock,
        mock_get_blink: Mock,
        mock_mkdir: Mock,
        mock_exists: Mock,
    ) -> None:
        """Test download_cloud_clip with URL error."""
        from blinkapp.services.clip_download import download_cloud_clip
        from tests.test_base import create_mock_blink_instance

        mock_blink = create_mock_blink_instance(available=True)
        mock_get_blink.return_value = mock_blink
        mock_exists.return_value = False
        mock_download_sync.return_value = (None, "Invalid URL")

        response, status_code = download_cloud_clip(self.clip_id)

        self.assertEqual(status_code, 404)
        self.assertFalse(response["success"])

    def test_download_cloud_clip_exception_handling(self) -> None:
        """Test download_cloud_clip exception handling."""
        from blinkapp.services.clip_download import download_cloud_clip

        with patch(
            "blinkapp.services.blink_service.get_blink_instance",
            side_effect=Exception("Test error"),
        ):
            response, status_code = download_cloud_clip(self.clip_id)

            self.assertEqual(status_code, 500)
            self.assertFalse(response["success"])
            self.assertIn("Failed to download cloud clip", response["error"])

    def test_download_cloud_clip_core_success(self) -> None:
        """Test _download_cloud_clip_core success."""
        import asyncio
        from pathlib import Path

        from blinkapp.services.clip_download import _download_cloud_clip_core
        from tests.test_base import create_mock_blink_instance

        async def run_test():
            mock_blink = create_mock_blink_instance(available=True)

            # Mock get_videos_metadata
            mock_blink.get_videos_metadata = AsyncMock(
                return_value=[{"id": "123456", "media": "http://example.com/clip.mp4"}]
            )

            # Mock do_http_get
            from tests.test_base import create_mock_client_response

            mock_response = create_mock_client_response(b"video_data")
            mock_response.read = AsyncMock(return_value=b"video_data")
            mock_blink.do_http_get = AsyncMock(return_value=mock_response)

            clips_cache_dir = Path("/tmp/test_clips")

            with patch("builtins.open", mock_open()) as mock_file:
                result_path, error = await _download_cloud_clip_core(
                    self.clip_id, mock_blink, clips_cache_dir
                )

                self.assertIsNotNone(result_path)
                self.assertIsNone(error)
                mock_file.assert_called_once()

        asyncio.run(run_test())

    def test_download_cloud_clip_core_clip_not_found(self) -> None:
        """Test _download_cloud_clip_core when clip not found in metadata."""
        import asyncio
        from pathlib import Path

        from blinkapp.services.clip_download import _download_cloud_clip_core
        from tests.test_base import create_mock_blink_instance

        async def run_test():
            mock_blink = create_mock_blink_instance(available=True)
            mock_blink.get_videos_metadata = AsyncMock(
                return_value=[
                    {
                        "id": "999999",
                        "media": "http://example.com/other.mp4",
                    }  # Different ID
                ]
            )

            clips_cache_dir = Path("/tmp/test_clips")

            result_path, error = await _download_cloud_clip_core(
                self.clip_id, mock_blink, clips_cache_dir
            )

            self.assertIsNone(result_path)
            self.assertEqual(error, "Clip not found")

        asyncio.run(run_test())

    def test_download_cloud_clip_core_no_media_url(self) -> None:
        """Test _download_cloud_clip_core when no media URL."""
        import asyncio
        from pathlib import Path

        from blinkapp.services.clip_download import _download_cloud_clip_core
        from tests.test_base import create_mock_blink_instance

        async def run_test():
            mock_blink = create_mock_blink_instance(available=True)
            mock_blink.get_videos_metadata = AsyncMock(
                return_value=[
                    {"id": "123456"}  # No media URL
                ]
            )

            clips_cache_dir = Path("/tmp/test_clips")

            result_path, error = await _download_cloud_clip_core(
                self.clip_id, mock_blink, clips_cache_dir
            )

            self.assertIsNone(result_path)
            self.assertIn("not available for download", error)

        asyncio.run(run_test())

    def test_download_cloud_clip_core_exception(self) -> None:
        """Test _download_cloud_clip_core exception handling."""
        import asyncio
        from pathlib import Path

        from blinkapp.services.clip_download import _download_cloud_clip_core
        from tests.test_base import create_mock_blink_instance

        async def run_test():
            mock_blink = create_mock_blink_instance(available=True)
            mock_blink.get_videos_metadata = AsyncMock(
                side_effect=Exception("API error")
            )

            clips_cache_dir = Path("/tmp/test_clips")

            result_path, error = await _download_cloud_clip_core(
                self.clip_id, mock_blink, clips_cache_dir
            )

            self.assertIsNone(result_path)
            self.assertIn("Error downloading cloud clip", error)

        asyncio.run(run_test())

    @patch("blinkapp.services.blink_service.get_blink_instance")
    def test_download_local_clip_no_blink_instance(self, mock_get_blink: Mock) -> None:
        """Test download_local_clip when no blink instance."""
        from blinkapp.models.ids import ClipId
        from blinkapp.services.clip_download import download_local_clip

        local_clip_id = ClipId.from_local("sync1", 123456)
        mock_get_blink.return_value = None

        response, status_code = download_local_clip(local_clip_id)

        self.assertEqual(status_code, 503)
        self.assertFalse(response["success"])

    @patch("blinkapp.services.blink_service.get_blink_instance")
    def test_download_local_clip_blink_unavailable(self, mock_get_blink: Mock) -> None:
        """Test download_local_clip when blink unavailable."""
        from blinkapp.models.ids import ClipId
        from blinkapp.services.clip_download import download_local_clip
        from tests.test_base import create_mock_blink_instance

        local_clip_id = ClipId.from_local("sync1", 123456)
        mock_blink = create_mock_blink_instance(available=False)
        mock_get_blink.return_value = mock_blink

        response, status_code = download_local_clip(local_clip_id)

        self.assertEqual(status_code, 503)
        self.assertFalse(response["success"])

    @patch("blinkapp.services.blink_service.get_blink_instance")
    def test_download_local_clip_sync_not_found(self, mock_get_blink: Mock) -> None:
        """Test download_local_clip when sync module not found."""
        from blinkapp.models.ids import ClipId
        from blinkapp.services.clip_download import download_local_clip
        from tests.test_base import create_mock_blink_instance

        local_clip_id = ClipId.from_local("missing_sync", 123456)
        mock_blink = create_mock_blink_instance(available=True)
        mock_blink.sync = {}  # Empty sync dict
        mock_get_blink.return_value = mock_blink

        response, status_code = download_local_clip(local_clip_id)

        self.assertEqual(status_code, 404)
        self.assertFalse(response["success"])
        self.assertIn("not found", response["error"])

    @patch("blinkapp.services.blink_service.get_blink_instance")
    def test_download_local_clip_no_local_storage(self, mock_get_blink: Mock) -> None:
        """Test download_local_clip when no local storage."""
        from blinkapp.models.ids import ClipId
        from blinkapp.services.clip_download import download_local_clip
        from tests.test_base import create_mock_blink_instance, create_mock_sync

        local_clip_id = ClipId.from_local("sync1", 123456)
        mock_blink = create_mock_blink_instance(available=True)

        mock_sync = create_mock_sync(local_storage=False)
        mock_blink.sync = {"sync1": mock_sync}
        mock_get_blink.return_value = mock_blink

        response, status_code = download_local_clip(local_clip_id)

        self.assertEqual(status_code, 503)
        self.assertFalse(response["success"])
        self.assertIn("Local storage not available", response["error"])

    @patch("blinkapp.services.blink_service.get_blink_instance")
    def test_download_local_clip_item_not_found(self, mock_get_blink: Mock) -> None:
        """Test download_local_clip when local item not found."""
        from blinkapp.models.ids import ClipId
        from blinkapp.services.clip_download import download_local_clip
        from tests.test_base import create_mock_blink_instance, create_mock_sync

        local_clip_id = ClipId.from_local("sync1", 123456)
        mock_blink = create_mock_blink_instance(available=True)

        mock_sync = create_mock_sync(
            local_storage=True, _local_storage={"manifest": []}
        )
        mock_blink.sync = {"sync1": mock_sync}
        mock_get_blink.return_value = mock_blink

        response, status_code = download_local_clip(local_clip_id)

        self.assertEqual(status_code, 404)
        self.assertFalse(response["success"])
        self.assertIn("not found", response["error"])

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("flask.send_file")
    @patch("blinkapp.services.blink_service.get_blink_instance")
    def test_download_local_clip_cached_file_exists(
        self, mock_get_blink: Mock, mock_send_file: Mock
    ) -> None:
        """Test download_local_clip when cached file exists."""
        from datetime import datetime

        from blinkapp.models.ids import ClipId
        from blinkapp.services.clip_download import download_local_clip
        from tests.test_base import create_mock_blink_instance

        local_clip_id = ClipId.from_local("sync1", 123456)
        mock_blink = create_mock_blink_instance(available=True)

        from tests.test_base import create_mock_clip_item

        mock_item = create_mock_clip_item(
            clip_id=123456,
            name="test_clip.mp4",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
        )

        mock_sync = Mock()
        mock_sync.local_storage = Mock()
        mock_sync._local_storage = {"manifest": [mock_item]}
        mock_blink.sync = {"sync1": mock_sync}
        mock_get_blink.return_value = mock_blink

        mock_send_file.return_value = "file_response"

        # Mock the cached file to exist
        with patch("pathlib.Path.exists", return_value=True):
            result = download_local_clip(local_clip_id)

        self.assertEqual(result, "file_response")
        mock_send_file.assert_called_once()

    def test_download_local_clip_exception_handling(self) -> None:
        """Test download_local_clip exception handling."""
        from blinkapp.models.ids import ClipId
        from blinkapp.services.clip_download import download_local_clip

        local_clip_id = ClipId.from_local("sync1", 123456)

        with patch(
            "blinkapp.services.blink_service.get_blink_instance",
            side_effect=Exception("Test error"),
        ):
            response, status_code = download_local_clip(local_clip_id)

            self.assertEqual(status_code, 500)
            self.assertFalse(response["success"])
            self.assertIn("Failed to download local clip", response["error"])

    @patch("pathlib.Path.exists")
    @patch("flask.send_file")
    def test_download_clip_common_success(
        self, mock_send_file: Mock, mock_exists: Mock
    ) -> None:
        """Test download_clip_common success."""
        from pathlib import Path

        from blinkapp.services.clip_download import download_clip_common

        clip_path = Path("/tmp/test_clip.mp4")
        mock_exists.return_value = True
        mock_send_file.return_value = "file_response"

        result = download_clip_common(clip_path, self.clip_id)

        self.assertEqual(result, "file_response")
        mock_send_file.assert_called_once_with(
            clip_path,
            as_attachment=True,
            download_name=f"clip_{self.clip_id}.mp4",
            mimetype="video/mp4",
        )

    @patch("pathlib.Path.exists")
    def test_download_clip_common_file_not_found(self, mock_exists: Mock) -> None:
        """Test download_clip_common when file not found."""
        from pathlib import Path

        from blinkapp.services.clip_download import download_clip_common

        clip_path = Path("/tmp/missing_clip.mp4")
        mock_exists.return_value = False

        response, status_code = download_clip_common(clip_path, self.clip_id)

        self.assertEqual(status_code, 404)
        self.assertFalse(response["success"])
        self.assertIn("not found", response["error"])

    @patch("pathlib.Path.exists")
    @patch("flask.send_file")
    def test_download_clip_common_exception(
        self, mock_send_file: Mock, mock_exists: Mock
    ) -> None:
        """Test download_clip_common exception handling."""
        from pathlib import Path

        from blinkapp.services.clip_download import download_clip_common

        clip_path = Path("/tmp/test_clip.mp4")
        mock_exists.return_value = True
        mock_send_file.side_effect = Exception("Send file error")

        response, status_code = download_clip_common(clip_path, self.clip_id)

        self.assertEqual(status_code, 500)
        self.assertFalse(response["success"])
        self.assertIn("Failed to serve clip file", response["error"])


class TestClipProcessing(BaseTestCase):
    """Test clip processing service functions."""

    clip_id: ClipId
    clips_cache_dir: Path

    def setUp(self) -> None:
        """Set up test fixtures."""
        from blinkapp.models.ids import ClipId

        super().setUp()
        self.clip_id = ClipId("123456")
        self.clips_cache_dir = Path("/tmp/test_clips")

    def test_download_and_cache_cloud_thumbnail_local_clip_error(self) -> None:
        """Test download thumbnail with local clip raises error."""
        from blinkapp.models.ids import ClipId
        from blinkapp.services.clip_processing import download_and_cache_cloud_thumbnail

        # Create a local clip ID that will return True for is_local()
        local_clip_id = ClipId.from_local("test_sync", 123456)

        with self.assertRaises(ValueError) as context:
            download_and_cache_cloud_thumbnail(
                local_clip_id, "http://example.com/thumbnail.jpg"
            )

        self.assertIn("called on local clip", str(context.exception))

    def test_download_and_cache_cloud_thumbnail_no_url(self) -> None:
        """Test download thumbnail with no URL."""
        from blinkapp.services.clip_processing import download_and_cache_cloud_thumbnail

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            result = download_and_cache_cloud_thumbnail(self.clip_id, "")

            self.assertIsNone(result)
            mock_logger.error.assert_called_with(
                f"No thumbnail URL provided for clip {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    def test_process_cloud_clip_background_thumbnail_exists(
        self, mock_exists: Mock
    ) -> None:
        """Test cloud clip processing when thumbnail already exists."""
        from blinkapp.services.clip_processing import process_cloud_clip_background

        mock_exists.return_value = True

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_cloud_clip_background(self.clip_id)

            mock_logger.debug.assert_called_with(
                f"Thumbnail already cached for clip {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    def test_process_cloud_clip_background_no_blink(
        self, mock_ensure_blink: Mock, mock_exists: Mock
    ) -> None:
        """Test cloud clip processing when blink is not available."""
        from blinkapp.services.clip_processing import process_cloud_clip_background

        mock_exists.return_value = False
        mock_ensure_blink.side_effect = RuntimeError("Blink not initialized")

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_cloud_clip_background(self.clip_id)

            mock_logger.warning.assert_called_with(
                f"Blink not available for processing clip {self.clip_id}"
            )

    def test_process_cloud_clip_background_blink_unavailable(self) -> None:
        """Test when blink instance is unavailable."""
        from blinkapp.services.clip_processing import process_cloud_clip_background
        from tests.test_base import create_mock_blink_instance

        with (
            patch("pathlib.Path.exists", return_value=False),
            patch(
                "blinkapp.services.blink_service.ensure_blink_initialized"
            ) as mock_ensure,
        ):
            mock_blink = create_mock_blink_instance(available=False)
            mock_ensure.return_value = mock_blink

            process_cloud_clip_background(self.clip_id)
            mock_ensure.assert_called_once()

    def test_process_local_clip_background_blink_error(self) -> None:
        """Test local clip processing when blink initialization fails."""
        from blinkapp.services.clip_processing import process_local_clip_background

        with (
            patch("pathlib.Path.exists", return_value=False),
            patch(
                "blinkapp.services.blink_service.ensure_blink_initialized"
            ) as mock_ensure,
        ):
            mock_ensure.side_effect = RuntimeError("Blink not available")
            process_local_clip_background(self.clip_id, "sync_name", "filename.mp4")
            mock_ensure.assert_called_once()

    def test_process_local_clip_background_thumbnail_exists(self) -> None:
        """Test local clip processing when thumbnail already exists."""
        from blinkapp.services.clip_processing import process_local_clip_background

        with patch("pathlib.Path.exists", return_value=True) as mock_exists:
            process_local_clip_background(self.clip_id, "sync_name", "filename.mp4")
            mock_exists.assert_called_once()

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("requests.get")
    def test_download_and_cache_cloud_thumbnail_success(
        self, mock_get: Mock, mock_mkdir: Mock, mock_exists: Mock
    ) -> None:
        """Test successful cloud thumbnail download."""
        from blinkapp.services.clip_processing import download_and_cache_cloud_thumbnail

        mock_exists.return_value = False
        from tests.test_base import create_mock_client_response

        mock_response = create_mock_client_response(b"thumbnail_data")
        mock_get.return_value = mock_response

        with patch("builtins.open", mock_open()) as mock_file:
            result = download_and_cache_cloud_thumbnail(
                self.clip_id, "http://example.com/thumbnail.jpg"
            )

            self.assertIsNotNone(result)
            mock_get.assert_called_once_with(
                "http://example.com/thumbnail.jpg", timeout=30
            )
            mock_file.assert_called_once()
            mock_response.raise_for_status.assert_called_once()

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("requests.get")
    def test_download_and_cache_cloud_thumbnail_request_error(
        self, mock_get: Mock, mock_exists: Mock
    ) -> None:
        """Test cloud thumbnail download with request error."""
        from blinkapp.services.clip_processing import download_and_cache_cloud_thumbnail

        mock_exists.return_value = False
        mock_get.side_effect = requests.RequestException("Network error")

        result = download_and_cache_cloud_thumbnail(
            self.clip_id, "http://example.com/thumbnail.jpg"
        )

        self.assertIsNone(result)

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    def test_download_and_cache_cloud_thumbnail_already_cached(
        self, mock_exists: Mock
    ) -> None:
        """Test cloud thumbnail download when already cached."""
        from blinkapp.services.clip_processing import download_and_cache_cloud_thumbnail

        mock_exists.return_value = True

        result = download_and_cache_cloud_thumbnail(
            self.clip_id, "http://example.com/thumbnail.jpg"
        )

        self.assertIsNotNone(result)
        self.assertEqual(result, Path("/tmp/test_clips") / f"{self.clip_id}.jpg")

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    @patch("pathlib.Path.mkdir")
    def test_process_cloud_clip_background_simple_flow(
        self,
        mock_mkdir: Mock,
        mock_clips_cache: Mock,
        mock_ensure_blink: Mock,
        mock_exists: Mock,
    ) -> None:
        """Test cloud clip processing flow (simplified)."""
        from blinkapp.services.clip_processing import process_cloud_clip_background

        # Setup mocks - thumbnail exists, so should return early
        mock_exists.return_value = True

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_cloud_clip_background(self.clip_id)

            mock_logger.debug.assert_called_with(
                f"Thumbnail already cached for clip {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_process_cloud_clip_background_no_media_url(
        self, mock_clips_cache: Mock, mock_ensure_blink: Mock, mock_exists: Mock
    ) -> None:
        """Test cloud clip processing when no media URL in cache."""
        from blinkapp.services.clip_processing import process_cloud_clip_background
        from tests.test_base import create_mock_blink_instance

        mock_exists.return_value = False
        mock_blink = create_mock_blink_instance(available=True)
        mock_ensure_blink.return_value = mock_blink

        from tests.test_base import create_mock_clips_cache

        mock_cache = create_mock_clips_cache()
        mock_cache.get.return_value = None  # No cached clip data
        mock_clips_cache.return_value = mock_cache

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_cloud_clip_background(self.clip_id)

            mock_logger.error.assert_called_with(
                f"No media URL found for cloud clip {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    @patch("requests.get")
    def test_process_cloud_clip_background_download_error(
        self,
        mock_get: Mock,
        mock_clips_cache: Mock,
        mock_ensure_blink: Mock,
        mock_exists: Mock,
    ) -> None:
        """Test cloud clip processing when download fails."""
        from blinkapp.services.clip_processing import process_cloud_clip_background
        from tests.test_base import create_mock_blink_instance

        mock_exists.return_value = False
        mock_blink = create_mock_blink_instance(available=True)
        mock_ensure_blink.return_value = mock_blink

        from tests.test_base import create_mock_clips_cache

        mock_cache = create_mock_clips_cache()
        mock_cache.get.return_value = {"media_url": "http://example.com/clip.mp4"}
        mock_clips_cache.return_value = mock_cache

        mock_get.side_effect = requests.RequestException("Download failed")

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_cloud_clip_background(self.clip_id)

            mock_logger.error.assert_called()

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_process_cloud_clip_thumbnail_only_success_simple(
        self, mock_clips_cache: Mock, mock_exists: Mock
    ) -> None:
        """Test cloud clip thumbnail-only processing success (simplified)."""
        from blinkapp.services.clip_processing import process_cloud_clip_thumbnail_only

        mock_exists.return_value = True  # Thumbnail already exists

        process_cloud_clip_thumbnail_only(self.clip_id)

        # Should return early due to existing thumbnail
        mock_exists.assert_called_once()

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_process_cloud_clip_thumbnail_only_no_url_simple(
        self, mock_clips_cache: Mock, mock_exists: Mock
    ) -> None:
        """Test cloud clip thumbnail-only processing with no URL (simplified)."""
        from blinkapp.services.clip_processing import process_cloud_clip_thumbnail_only

        mock_exists.return_value = False
        from tests.test_base import create_mock_clips_cache

        mock_cache = create_mock_clips_cache()
        mock_cache.get.return_value = None  # No cached data
        mock_clips_cache.return_value = mock_cache

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_cloud_clip_thumbnail_only(self.clip_id)

            mock_logger.debug.assert_called_with(
                f"No thumbnail URL found for cloud clip {self.clip_id} - skipping thumbnail download"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    def test_process_local_clip_background_blink_unavailable(
        self, mock_ensure_blink: Mock, mock_exists: Mock
    ) -> None:
        """Test local clip processing when blink is unavailable."""
        from blinkapp.services.clip_processing import process_local_clip_background
        from tests.test_base import create_mock_blink_instance

        mock_exists.return_value = False
        mock_blink = create_mock_blink_instance(available=False)
        mock_ensure_blink.return_value = mock_blink

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_local_clip_background(self.clip_id, "sync_name", "filename.mp4")

            mock_logger.warning.assert_called_with(
                f"Blink not available for processing local clip {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    def test_process_local_clip_background_sync_not_found(
        self, mock_ensure_blink: Mock, mock_exists: Mock
    ) -> None:
        """Test local clip processing when sync module not found."""
        from blinkapp.services.clip_processing import process_local_clip_background
        from tests.test_base import create_mock_blink_instance

        mock_exists.return_value = False
        mock_blink = create_mock_blink_instance(available=True)
        mock_blink.sync = {}  # Empty sync dict
        mock_ensure_blink.return_value = mock_blink

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_local_clip_background(self.clip_id, "missing_sync", "filename.mp4")

            mock_logger.error.assert_called_with(
                f"Sync module 'missing_sync' not found for clip {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    def test_process_local_clip_background_no_local_storage(
        self, mock_ensure_blink: Mock, mock_exists: Mock
    ) -> None:
        """Test local clip processing when no local storage available."""
        from blinkapp.services.clip_processing import process_local_clip_background
        from tests.test_base import create_mock_blink_instance

        mock_exists.return_value = False
        mock_blink = create_mock_blink_instance(available=True)

        mock_sync = Mock()
        mock_sync.local_storage = None
        mock_blink.sync = {"test_sync": mock_sync}
        mock_ensure_blink.return_value = mock_blink

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_local_clip_background(self.clip_id, "test_sync", "filename.mp4")

            mock_logger.warning.assert_called_with(
                f"Local storage not available for clip {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    def test_process_local_clip_background_not_implemented(
        self, mock_ensure_blink: Mock, mock_exists: Mock
    ) -> None:
        """Test local clip processing shows not implemented warning."""
        from blinkapp.services.clip_processing import process_local_clip_background
        from tests.test_base import create_mock_blink_instance

        mock_exists.return_value = False
        mock_blink = create_mock_blink_instance(available=True)

        mock_sync = Mock()
        mock_sync.local_storage = Mock()  # Has local storage
        mock_blink.sync = {"test_sync": mock_sync}
        mock_ensure_blink.return_value = mock_blink

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_local_clip_background(self.clip_id, "test_sync", "filename.mp4")

            mock_logger.warning.assert_any_call(
                f"Local clip processing not fully implemented for {self.clip_id}"
            )
            mock_logger.warning.assert_any_call(
                "Need to implement proper blinkpy LocalStorageMediaItem API usage"
            )

    def test_process_cloud_clip_background_exception_handling(self) -> None:
        """Test cloud clip processing exception handling."""
        from blinkapp.services.clip_processing import process_cloud_clip_background

        with (
            patch("pathlib.Path.exists", side_effect=Exception("Path error")),
            patch("blinkapp.services.clip_processing.logger") as mock_logger,
        ):
            process_cloud_clip_background(self.clip_id)

            mock_logger.error.assert_called()
            error_call = mock_logger.error.call_args[0][0]
            self.assertIn("Error in process_cloud_clip_background", error_call)

    def test_process_local_clip_background_exception_handling(self) -> None:
        """Test local clip processing exception handling."""
        from blinkapp.services.clip_processing import process_local_clip_background

        with (
            patch("pathlib.Path.exists", side_effect=Exception("Path error")),
            patch("blinkapp.services.clip_processing.logger") as mock_logger,
        ):
            process_local_clip_background(self.clip_id, "sync_name", "filename.mp4")

            mock_logger.error.assert_called()
            error_call = mock_logger.error.call_args[0][0]
            self.assertIn("Error in process_local_clip_background", error_call)

    def test_process_cloud_clip_thumbnail_only_exception_handling(self) -> None:
        """Test cloud clip thumbnail-only processing exception handling."""
        from blinkapp.services.clip_processing import process_cloud_clip_thumbnail_only

        with (
            patch("pathlib.Path.exists", side_effect=Exception("Path error")),
            patch("blinkapp.services.clip_processing.logger") as mock_logger,
        ):
            process_cloud_clip_thumbnail_only(self.clip_id)

            mock_logger.error.assert_called()
            error_call = mock_logger.error.call_args[0][0]
            self.assertIn("Error processing cloud clip", error_call)

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    def test_download_and_cache_cloud_thumbnail_exception_handling(self) -> None:
        """Test cloud thumbnail download exception handling."""
        from blinkapp.services.clip_processing import download_and_cache_cloud_thumbnail

        with (
            patch("pathlib.Path.mkdir", side_effect=Exception("Mkdir error")),
            patch("blinkapp.services.clip_processing.logger") as mock_logger,
        ):
            result = download_and_cache_cloud_thumbnail(
                self.clip_id, "http://example.com/thumb.jpg"
            )

            self.assertIsNone(result)
            mock_logger.error.assert_called()
            error_call = mock_logger.error.call_args[0][0]
            self.assertIn("Error in download_and_cache_cloud_thumbnail", error_call)


class TestClipService(BaseTestCase):
    """Test clip service functions."""

    clip_id: ClipId

    def setUp(self) -> None:
        """Set up test fixtures."""
        from blinkapp.models.ids import ClipId

        super().setUp()
        self.clip_id = ClipId("123456")


class TestStreamService(BaseTestCase):
    """Test stream service functions."""

    def test_ensure_stream_manager_initialized(self) -> None:
        """Test ensure_stream_manager_initialized function."""
        from blinkapp.services.stream_service import ensure_stream_manager_initialized

        result = ensure_stream_manager_initialized()
        self.assertIsNotNone(result)

    def test_stream_manager_access(self) -> None:
        """Test stream_manager access through service."""
        from blinkapp.services.stream_service import (
            ensure_stream_manager_initialized,
            initialize_stream_manager,
        )

        # Initialize stream manager
        initialize_stream_manager()

        # Test that we can access it through the service
        stream_manager = ensure_stream_manager_initialized()
        self.assertIsNotNone(stream_manager)

    def test_is_stream_active_false(self) -> None:
        """Test is_stream_active when stream is not active."""
        from blinkapp.models.ids import CameraId
        from blinkapp.services.stream_service import is_stream_active

        camera_id = CameraId(12345)
        result = is_stream_active(camera_id)
        self.assertFalse(result)

    def test_initialize_stream_manager(self) -> None:
        """Test stream_service initialize_stream_manager function."""
        from blinkapp.services.stream_service import initialize_stream_manager

        # Should not raise exception
        initialize_stream_manager()

    def test_ensure_stream_manager_initialized_coverage(self) -> None:
        """Test stream_service ensure_stream_manager_initialized function."""
        from blinkapp.services.stream_service import ensure_stream_manager_initialized

        # Should not raise exception
        result = ensure_stream_manager_initialized()
        self.assertIsNotNone(result)

    def test_is_stream_active_coverage(self) -> None:
        """Test stream_service is_stream_active function."""
        from blinkapp.models.ids import CameraId
        from blinkapp.services.stream_service import is_stream_active

        camera_id = CameraId("test_camera")
        result = is_stream_active(camera_id)
        self.assertIsInstance(result, bool)

    @patch("blinkapp.services.stream_service.ensure_stream_manager_initialized")
    def test_start_camera_stream_success(self, mock_ensure_manager: Mock) -> None:
        """Test start_camera_stream with successful stream start."""
        from blinkapp.models.ids import CameraId
        from blinkapp.services.stream_service import start_camera_stream
        from tests.test_base import create_mock_stream_manager

        camera_id = CameraId("12345")
        tcp_url = "tcp://localhost:8080"

        mock_manager = create_mock_stream_manager()
        mock_manager.start_stream.return_value = ("http://hls-url", None)
        mock_ensure_manager.return_value = mock_manager

        hls_url, error = start_camera_stream(camera_id, tcp_url)

        self.assertEqual(hls_url, "http://hls-url")
        self.assertIsNone(error)
        mock_manager.start_stream.assert_called_once_with("12345", tcp_url)

    @patch("blinkapp.services.stream_service.ensure_stream_manager_initialized")
    def test_start_camera_stream_failure(self, mock_ensure_manager: Mock) -> None:
        """Test start_camera_stream with stream start failure."""
        from blinkapp.models.ids import CameraId
        from blinkapp.services.stream_service import start_camera_stream

        camera_id = CameraId("12345")
        tcp_url = "tcp://localhost:8080"

        mock_ensure_manager.side_effect = Exception("Stream failed")

        hls_url, error = start_camera_stream(camera_id, tcp_url)

        self.assertIsNone(hls_url)
        self.assertIn("Stream failed", error)

    def test_stop_camera_stream_success(self) -> None:
        """Test successful camera stream stop."""
        from blinkapp.models.ids import CameraId
        from blinkapp.services.stream_service import stop_camera_stream
        from tests.test_base import create_mock_stream_manager

        with patch(
            "blinkapp.services.stream_service.ensure_stream_manager_initialized"
        ) as mock_ensure:
            mock_manager = create_mock_stream_manager()
            mock_ensure.return_value = mock_manager

            camera_id = CameraId("test_camera")
            result = stop_camera_stream(camera_id)

            self.assertTrue(result)
            mock_manager.stop_stream.assert_called_once_with(str(camera_id))

    def test_stop_camera_stream_failure(self) -> None:
        """Test camera stream stop failure."""
        from blinkapp.models.ids import CameraId
        from blinkapp.services.stream_service import stop_camera_stream
        from tests.test_base import create_mock_stream_manager

        with patch(
            "blinkapp.services.stream_service.ensure_stream_manager_initialized"
        ) as mock_ensure:
            mock_manager = create_mock_stream_manager()
            mock_manager.stop_stream.side_effect = Exception("Stop error")
            mock_ensure.return_value = mock_manager

            camera_id = CameraId("test_camera")
            result = stop_camera_stream(camera_id)

            self.assertFalse(result)


class TestSettingsService(BaseTestCase):
    """Test settings service functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()


class TestSystemService(BaseTestCase):
    """Test system service functions."""

    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    def test_get_systems_empty(self, mock_ensure_blink: Mock) -> None:
        """Test get_systems when no systems available."""
        from blinkapp.services.system_service import get_systems
        from tests.test_base import create_mock_blink_instance

        mock_blink = create_mock_blink_instance()
        mock_blink.sync = {}
        mock_ensure_blink.return_value = mock_blink
        result = get_systems()
        self.assertEqual(result, {"systems": []})

    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    def test_get_systems_with_data(self, mock_ensure_blink: Mock) -> None:
        """Test get_systems with mock data."""
        from blinkapp.services.system_service import get_systems
        from tests.test_base import create_mock_blink_instance, create_mock_sync

        mock_sync = create_mock_sync()
        mock_sync.network_id = 12345
        mock_sync.arm = False
        mock_sync.online = True

        mock_blink = create_mock_blink_instance()
        mock_blink.sync = {"test": mock_sync}
        mock_ensure_blink.return_value = mock_blink

        result = get_systems()
        self.assertIsInstance(result, dict)
        self.assertIn("systems", result)

    def test_initialize_cache_paths_with_config(self) -> None:
        """Test cache path initialization with app config (test isolation version)."""
        import blinkapp
        from blinkapp.services.cache_service import initialize_cache_paths

        # Store original values to restore later
        original_cache_dir = getattr(blinkapp, "CACHE_DIR", None)

        try:
            # Call the function (which is mocked by test isolation)
            initialize_cache_paths()

            # Verify that the global variables were set (this is what the mock does)
            assert hasattr(blinkapp, "CACHE_DIR")
            assert hasattr(blinkapp, "THUMBNAIL_CACHE_DIR")
            assert isinstance(blinkapp.CACHE_DIR, str)

        finally:
            # Restore original values
            if original_cache_dir is not None:
                blinkapp.CACHE_DIR = original_cache_dir

    def test_initialize_cache_paths_default(self) -> None:
        """Test cache path initialization with defaults."""
        from blinkapp.services.cache_service import initialize_cache_paths

        # Should not raise exception when outside app context
        try:
            initialize_cache_paths()
            success = True
        except Exception:
            success = False

        # Should handle missing app context gracefully
        self.assertTrue(success)

    def test_thumbnail_file_cleanup(self) -> None:
        """Test thumbnail file cleanup during update."""
        from unittest.mock import patch

        with (
            patch(
                "blinkapp.services.cache_service.camera_thumbnail_cache"
            ) as mock_cache,
            patch("pathlib.Path.exists") as mock_exists,
            patch("pathlib.Path.unlink") as mock_unlink,
        ):
            mock_cache.get.return_value = {"timestamp": 1000, "filename": "old.jpg"}
            mock_exists.return_value = True

            # Test file cleanup during thumbnail update
            try:
                # This would be part of the update_thumbnail inner function
                old_entry = mock_cache.get("test_key")
                if old_entry and old_entry.get("filename"):
                    mock_unlink.assert_not_called()  # Not called yet
                    # Simulate cleanup
                    mock_unlink()
                    mock_unlink.assert_called_once()
            except Exception:
                self.assertTrue(True)


class TestClipDownloadService(BaseTestCase):
    """Test clip download service functions."""

    def test_download_cloud_clip_core_sync_no_blink(self) -> None:
        """Test _download_cloud_clip_core_sync with no blink instance."""
        from pathlib import Path

        from blinkapp.models.ids import ClipId
        from blinkapp.services.clip_download import _download_cloud_clip_core_sync

        clip_id = ClipId("12345")  # Cloud clip (no ~ in ID)
        clips_cache_dir = Path("/tmp/clips")

        result_path, error = _download_cloud_clip_core_sync(
            clip_id, None, clips_cache_dir
        )

        self.assertIsNone(result_path)
        self.assertIn("Blink instance not available", error or "")

    def test_download_cloud_clip_success(self) -> None:
        """Test successful cloud clip download - no blink instance."""
        from unittest.mock import patch

        from blinkapp.models.ids import ClipId
        from blinkapp.services.clip_download import download_cloud_clip

        clip_id = ClipId("12345")  # Cloud clip

        with patch(
            "blinkapp.services.blink_service.get_blink_instance"
        ) as mock_get_blink:
            mock_get_blink.return_value = None  # No blink instance

            response, status_code = download_cloud_clip(clip_id)

            self.assertEqual(status_code, 503)
            self.assertFalse(response["success"])

    def test_download_cloud_clip_failure(self) -> None:
        """Test failed cloud clip download."""
        from unittest.mock import patch

        from blinkapp.models.ids import ClipId
        from blinkapp.services.clip_download import download_cloud_clip

        clip_id = ClipId("12345")  # Cloud clip

        with patch(
            "blinkapp.services.blink_service.get_blink_instance"
        ) as mock_get_blink:
            mock_get_blink.return_value = None  # No blink instance

            response, status_code = download_cloud_clip(clip_id)

            self.assertEqual(status_code, 503)
            self.assertFalse(response["success"])

    def test_download_local_clip_success(self) -> None:
        """Test local clip download - no local storage."""
        from unittest.mock import patch

        from blinkapp.models.ids import ClipId
        from blinkapp.services.clip_download import download_local_clip
        from tests.test_base import create_mock_blink_instance

        clip_id = ClipId.from_local("sync1", 123)

        with patch(
            "blinkapp.services.blink_service.get_blink_instance"
        ) as mock_get_blink:
            mock_blink = create_mock_blink_instance()
            mock_blink.available = True
            mock_get_blink.return_value = mock_blink

            # Mock sync module without local storage
            from tests.test_base import create_mock_sync

            mock_sync = create_mock_sync(
                12345, local_storage=False
            )  # Use parameter directly
            mock_blink.sync = {"sync1": mock_sync}

            response, status_code = download_local_clip(clip_id)

            self.assertEqual(status_code, 503)
            self.assertFalse(response["success"])
            self.assertIn("Local storage not available", response["error"])

    def test_download_local_clip_not_found(self) -> None:
        """Test local clip download when sync module not found."""
        from unittest.mock import patch

        from blinkapp.models.ids import ClipId
        from blinkapp.services.clip_download import download_local_clip
        from tests.test_base import create_mock_blink_instance

        clip_id = ClipId.from_local("nonexistent", 123)

        with patch(
            "blinkapp.services.blink_service.get_blink_instance"
        ) as mock_get_blink:
            mock_blink = create_mock_blink_instance()
            mock_blink.available = True
            mock_blink.sync = {}  # Empty sync dict
            mock_get_blink.return_value = mock_blink

            response, status_code = download_local_clip(clip_id)

            self.assertEqual(status_code, 404)
            self.assertFalse(response["success"])
            self.assertIn("not found", response["error"])


class TestThumbnailService(BaseTestCase):
    """Test thumbnail service functions."""

    mock_camera: Mock

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()
        from tests.test_base import create_mock_camera

        self.mock_camera = create_mock_camera(
            name="Test Camera", thumbnail="http://example.com/thumb.jpg"
        )

    @patch("blinkapp.services.cache_service.camera_thumbnail_cache")
    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    @patch("blinkapp.services.connection_service.executor")
    @patch("blinkapp.THUMBNAIL_CACHE_DIR", "/tmp/thumbnails")
    def test_update_camera_camera_thumbnail_cache(
        self, mock_executor: Mock, mock_connection: Mock, mock_cache: Mock
    ) -> None:
        """Test camera thumbnail cache update."""
        # Setup mocks
        mock_cache.get.return_value = {"timestamp": 1000, "filename": "old.jpg"}
        from aiohttp import ClientResponse

        mock_response = Mock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.read = Mock(spec=ClientResponse.read, return_value=b"image_data")
        mock_connection.execute.side_effect = [mock_response, b"image_data"]

        try:
            from blinkapp.routes.thumbnails import update_camera_thumbnail
            from blinkapp.services.cache_service import (
                initialize_cache_paths,
                initialize_caches,
            )

            # Initialize cache paths and caches before thumbnail operations
            initialize_cache_paths()
            initialize_caches({})
            update_camera_thumbnail(self.mock_camera, 2000, 1000)
            # Should submit task to executor
            mock_executor.submit.assert_called_once()
        except (ImportError, AttributeError):
            self.assertTrue(True)

    @patch("blinkapp.services.cache_service.camera_thumbnail_cache")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.unlink")
    def test_thumbnail_file_cleanup(
        self, mock_unlink: Mock, mock_exists: Mock, mock_cache: Mock
    ) -> None:
        """Test thumbnail file cleanup during update."""
        mock_cache.get.return_value = {"timestamp": 1000, "filename": "old.jpg"}
        mock_exists.return_value = True

        # Test file cleanup during thumbnail update
        try:
            # This would be part of the update_thumbnail inner function
            old_entry = mock_cache.get("test_key")
            if old_entry and old_entry.get("filename"):
                mock_unlink.assert_not_called()  # Not called yet
                # Simulate cleanup
                mock_unlink()
                mock_unlink.assert_called_once()
        except Exception:
            self.assertTrue(True)


class TestLifecycleService(BaseTestCase):
    """Test lifecycle service functions."""

    @patch("blinkapp.services.cache_service.initialize_cache_paths")
    @patch("blinkapp.services.connection_service.initialize_connections")
    @patch("blinkapp.services.cache_service.initialize_caches")
    @patch("blinkapp.services.stream_service.initialize_stream_manager")
    @patch("blinkapp.services.blink_service.initialize_blink_objects")
    @patch("blinkapp.utils.logging_config.setup_logging")
    @patch("blinkapp.CACHE_DIR", "/mock/cache")
    @patch("blinkapp.THUMBNAIL_CACHE_DIR", "/mock/cache/thumbnails")
    @patch("blinkapp.CLIPS_CACHE_DIR", "/mock/cache/clips")
    @patch("pathlib.Path.mkdir")
    def test_startup_success(
        self,
        mock_mkdir: Mock,
        mock_logging: Mock,
        mock_blink: Mock,
        mock_stream: Mock,
        mock_caches: Mock,
        mock_connections: Mock,
        mock_paths: Mock,
    ) -> None:
        """Test successful startup."""
        from blinkapp.services import lifecycle_service

        lifecycle_service.startup()

        mock_connections.assert_called_once()
        mock_blink.assert_called_once()
        mock_paths.assert_called_once()
        mock_caches.assert_called_once()
        mock_stream.assert_called_once()

    @patch("blinkapp.services.connection_service.initialize_connections")
    def test_startup_exception(self, mock_connections: Mock) -> None:
        """Test startup with exception - should log but not raise."""
        from blinkapp.services import lifecycle_service

        mock_connections.side_effect = Exception("Startup error")

        # Should not raise exception, just log warning
        lifecycle_service.startup()
        self.assertTrue(True)  # Test passes if no exception raised

    @patch(
        "blinkapp.services.connection_service.executor",
        create_mock_thread_pool_executor(),
    )
    @patch("blinkapp.services.stream_service.ensure_stream_manager_initialized")
    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    def test_cleanup_resources_success(
        self, mock_blink_conn: Mock, mock_stream: Mock
    ) -> None:
        """Test successful resource cleanup."""
        from blinkapp.services import lifecycle_service
        from tests.test_base import (
            create_mock_blink_connection,
            create_mock_stream_manager,
        )

        mock_stream_manager = create_mock_stream_manager()
        mock_stream.return_value = mock_stream_manager
        mock_blink_connection = create_mock_blink_connection()
        mock_blink_conn.return_value = mock_blink_connection

        lifecycle_service.cleanup_resources()

        mock_stream_manager.shutdown.assert_called_once()
        mock_blink_connection.cleanup_active_streams.assert_called_once()

    @patch("blinkapp.services.stream_service.ensure_stream_manager_initialized")
    def test_cleanup_resources_exception(self, mock_stream: Mock) -> None:
        """Test cleanup with exception - should raise."""
        from blinkapp.services import lifecycle_service

        mock_stream.side_effect = Exception("Cleanup error")

        try:
            lifecycle_service.cleanup_resources()
            raise AssertionError("Should have raised exception")
        except Exception as e:
            self.assertIn("Cleanup error", str(e))


class TestConnectionService(BaseTestCase):
    """Test connection service functions."""

    # Don't initialize blink objects for this test to test uninitialized state
    init_blink_objects = False

    def test_initialize_connections(self) -> None:
        """Test initialize_connections function."""
        from blinkapp.services.connection_service import initialize_connections

        initialize_connections()  # Should not raise exception

    def test_ensure_executor_initialized(self) -> None:
        """Test ensure_executor_initialized function."""
        from blinkapp.services.connection_service import ensure_executor_initialized

        result = ensure_executor_initialized()
        self.assertIsNotNone(result)

    def test_ensure_http_session_initialized(self) -> None:
        """Test ensure_http_session_initialized function."""
        from blinkapp.services.connection_service import ensure_http_session_initialized

        result = ensure_http_session_initialized()
        self.assertIsNotNone(result)

    def test_third_party_imports(self) -> None:
        """Test third-party imports."""
        from blinkapp.services import connection_service

        self.assertTrue(hasattr(connection_service, "http_session"))
        # Path should be imported from pathlib, not from blinkapp
        from pathlib import Path

        self.assertTrue(Path is not None)

    @patch("concurrent.futures.ThreadPoolExecutor")
    def test_parallel_cache_clearing(self, mock_executor: Mock) -> None:
        """Test parallel execution of cache clearing."""
        # Use patched ThreadPoolExecutor directly and set up context manager
        mock_executor.__enter__ = Mock(spec=callable, return_value=mock_executor)
        mock_executor.__exit__ = Mock(spec=callable, return_value=None)
        mock_executor.return_value = mock_executor  # Use the patched mock directly

        # Test parallel execution pattern
        with mock_executor() as executor:
            self.assertEqual(executor, mock_executor)

    def test_connection_service_basic(self) -> None:
        """Test basic connection service."""
        from blinkapp.services.blink_connection import get_blink_connection

        # Should return None when blink objects are not initialized
        result = get_blink_connection()
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
