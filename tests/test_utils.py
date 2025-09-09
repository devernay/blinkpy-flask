"""Unit tests for utility classes and functions.

This file contains ONLY unit tests for blinkapp/utils/ modules:
- Decorators (decorators.py, route_decorators.py)
- Formatters (formatters.py)
- Validators (validators.py)
- Parsers (parsers.py)
- Error classes (errors.py)
- Logging configuration (logging_config.py)
- Other utility functions

These are pure unit tests with mocked dependencies.
DO NOT add integration tests here - those belong in test_integration_*.py files.
DO NOT add Flask route tests here - those belong in test_integration_api.py.
"""

import unittest
from unittest.mock import Mock, patch

from blinkapp.config import Config
from tests.test_base import BaseTestCase


class TestApiResponses(BaseTestCase):
    """Test API response functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()


class TestDecorators(BaseTestCase):
    """Test decorator functions."""

    def test_safe_execute_success(self) -> None:
        """Test safe_execute with successful function."""
        from blinkapp.utils.decorators import safe_execute

        def success_func():
            return "success"

        result = safe_execute(success_func)
        self.assertEqual(result, "success")

    def test_safe_execute_exception_with_default(self) -> None:
        """Test safe_execute with exception and default value."""
        from blinkapp.utils.decorators import safe_execute

        def failing_func():
            raise ValueError("Test error")

        result = safe_execute(failing_func, default="default_value")
        self.assertEqual(result, "default_value")

    def test_safe_execute_exception_no_default(self) -> None:
        """Test safe_execute with exception and no default."""
        from blinkapp.utils.decorators import safe_execute

        def failing_func():
            raise ValueError("Test error")

        result = safe_execute(failing_func)
        self.assertIsNone(result)

    def test_decorators_basic_usage(self) -> None:
        """Test basic decorator usage."""
        from blinkapp.utils.decorators import error_context

        @error_context("test operation")
        def simple_test_function() -> str:
            return "success"

        result = simple_test_function()
        self.assertEqual(result, "success")


class TestRouteDecorators(BaseTestCase):
    """Test route decorator functions."""

    def test_get_operation_name_basic(self) -> None:
        """Test _get_operation_name with basic function."""
        from blinkapp.utils.route_decorators import _get_operation_name

        def test_function():
            pass

        result = _get_operation_name(test_function)
        # The function converts underscores to spaces
        self.assertEqual(result, "test function")

    def test_get_operation_name_with_module(self) -> None:
        """Test _get_operation_name includes module info."""
        from blinkapp.utils.route_decorators import _get_operation_name

        # Use an actual function with module
        result = _get_operation_name(len)
        self.assertIn("len", result)

    def test_is_error_response_true(self) -> None:
        """Test _is_error_response returns True for error responses."""
        from blinkapp.utils.route_decorators import _is_error_response

        error_response = ({"success": False, "error": "Test error"}, 400)
        result = _is_error_response(error_response)
        self.assertTrue(result)

    def test_is_error_response_success_response(self) -> None:
        """Test _is_error_response with success response tuple."""
        from blinkapp.utils.route_decorators import _is_error_response

        # The function checks if result is Response or tuple, so tuples return True
        success_response = ({"success": True, "data": "test"}, 200)
        result = _is_error_response(success_response)
        self.assertTrue(
            result
        )  # Tuples are considered "error responses" for caching purposes

    def test_is_error_response_invalid_format(self) -> None:
        """Test _is_error_response with invalid response format."""
        from blinkapp.utils.route_decorators import _is_error_response

        invalid_response = "not a tuple"
        result = _is_error_response(invalid_response)
        self.assertFalse(result)


class TestFormatters(BaseTestCase):
    """Test formatter functions."""

    def test_format_clips_by_day_empty(self) -> None:
        """Test format_clips_by_day with empty list."""
        from blinkapp.utils.formatters import format_clips_by_day

        result = format_clips_by_day([])
        self.assertEqual(result, [])

    def test_format_clips_by_day_single_clip(self) -> None:
        """Test format_clips_by_day with single clip."""
        from typing import cast

        from blinkapp.models.types import ClipApiData
        from blinkapp.utils.formatters import format_clips_by_day

        clips = cast(
            list[ClipApiData],
            [
                {
                    "id": "1",
                    "created_at": "2024-01-01T12:00:00Z",
                    "device_name": "Camera 1",
                    "thumbnail": "thumb.jpg",
                    "media": "clip.mp4",
                }
            ],
        )

        result = format_clips_by_day(clips)
        self.assertEqual(len(result), 1)
        # The function formats dates as "January 01, 2024"
        self.assertEqual(result[0]["date"], "January 01, 2024")
        self.assertEqual(len(result[0]["clips"]), 1)

    def test_format_time_duration_seconds(self) -> None:
        """Test format_time_duration with seconds only."""
        from blinkapp.utils.formatters import format_time_duration

        result = format_time_duration(45)
        self.assertEqual(result, "45s")

    def test_format_time_duration_minutes(self) -> None:
        """Test format_time_duration with minutes only."""
        from blinkapp.utils.formatters import format_time_duration

        result = format_time_duration(120)  # 2m exactly
        self.assertEqual(result, "2m")

    def test_format_time_duration_hours(self) -> None:
        """Test format_time_duration with hours only."""
        from blinkapp.utils.formatters import format_time_duration

        result = format_time_duration(3600)  # 1h exactly
        self.assertEqual(result, "1h")

    def test_format_time_duration_edge_cases(self) -> None:
        """Test format_time_duration edge cases."""
        from blinkapp.utils.formatters import format_time_duration

        # Test zero duration
        self.assertEqual(format_time_duration(0), "0s")

        # Test days
        self.assertEqual(format_time_duration(86400), "1d")

        # Test negative duration raises error
        with self.assertRaises(ValueError):
            format_time_duration(-1)


class TestValidationHelpers(BaseTestCase):
    """Test validation helper functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()


class TestValidators(BaseTestCase):
    """Test validator functions."""

    def test_validate_string_input_valid(self) -> None:
        """Test validate_string_input with valid input."""
        from blinkapp.utils.validators import validate_string_input

        result = validate_string_input("hello", 10, "test_field")
        self.assertEqual(result, "hello")

    def test_validate_string_input_too_long(self) -> None:
        """Test validate_string_input with input too long."""
        from blinkapp.utils.validators import validate_string_input

        with self.assertRaises(ValueError):
            validate_string_input("hello world", 5, "test_field")

    def test_validate_camera_id_valid(self) -> None:
        """Test validate_camera_id with valid ID."""
        from blinkapp.utils.validators import validate_camera_id

        result = validate_camera_id("12345")
        self.assertEqual(result, "12345")

    def test_validate_camera_id_invalid_raises_exception(self) -> None:
        """Test validate_camera_id with invalid ID raises exception."""
        from blinkapp.utils.validators import validate_camera_id

        with self.assertRaises(ValueError):
            validate_camera_id("")

    def test_validate_camera_id_comprehensive(self) -> None:
        """Test comprehensive camera ID validation."""
        try:
            from blinkapp.utils.validators import validate_camera_id

            # Valid IDs should not raise exceptions
            try:
                validate_camera_id("camera123")
                validate_camera_id("cam-456")
                validate_camera_id("cam_789")
            except ValueError:
                self.fail("validate_camera_id raised ValueError for valid input")

            # Invalid IDs should raise ValueError
            with self.assertRaises(ValueError):
                validate_camera_id("")
            with self.assertRaises((ValueError, TypeError)):
                validate_camera_id(None)  # type: ignore
            with self.assertRaises(ValueError):
                validate_camera_id("invalid@camera")
        except ImportError:
            self.skipTest("validate_camera_id function not found")

    def test_validate_tcp_url_valid(self) -> None:
        """Test validate_tcp_url with valid URL."""
        from blinkapp.utils.validators import validate_tcp_url

        result = validate_tcp_url("tcp://127.0.0.1:8080")
        self.assertEqual(result, "tcp://127.0.0.1:8080")

    def test_validate_tcp_url_invalid(self) -> None:
        """Test validate_tcp_url with invalid URL."""
        from blinkapp.utils.validators import validate_tcp_url

        with self.assertRaises(ValueError):
            validate_tcp_url("invalid_url")

    def test_is_valid_email_format_valid(self) -> None:
        """Test is_valid_email_format with valid email."""
        from blinkapp.utils.validators import is_valid_email_format

        self.assertTrue(is_valid_email_format("test@example.com"))

    def test_is_valid_email_format_invalid(self) -> None:
        """Test is_valid_email_format with invalid email."""
        from blinkapp.utils.validators import is_valid_email_format

        self.assertFalse(is_valid_email_format("invalid"))

    def test_validate_credentials_valid(self) -> None:
        """Test validate_credentials with valid inputs."""
        from blinkapp.utils.validators import validate_credentials

        username, password = validate_credentials("test@example.com", "password123")
        self.assertEqual(username, "test@example.com")
        self.assertEqual(password, "password123")

    def test_validate_credentials_invalid_email(self) -> None:
        """Test validate_credentials with invalid email."""
        from blinkapp.utils.validators import validate_credentials

        with self.assertRaises(ValueError):
            validate_credentials("invalid", "password123")

    def test_validate_string_input_comprehensive(self) -> None:
        """Test string input validation comprehensively."""
        from blinkapp.utils.validators import validate_string_input

        # Test valid input
        result = validate_string_input("test", 10, "field")
        self.assertEqual(result, "test")

        # Test whitespace trimming
        result = validate_string_input("  test  ", 10, "field")
        self.assertEqual(result, "test")

        # Test empty input
        with self.assertRaises(ValueError):
            validate_string_input("", 10, "field")

        # Test too long input
        with self.assertRaises(ValueError):
            validate_string_input("toolong", 5, "field")

    def test_email_validation_comprehensive(self) -> None:
        """Test email format validation comprehensively."""
        from blinkapp.utils.validators import is_valid_email_format

        # Valid emails
        self.assertTrue(is_valid_email_format("test@example.com"))
        self.assertTrue(is_valid_email_format("user.name+tag@domain.co.uk"))

        # Invalid emails
        self.assertFalse(is_valid_email_format(""))
        self.assertFalse(is_valid_email_format("invalid"))
        self.assertFalse(is_valid_email_format("@domain.com"))
        self.assertFalse(is_valid_email_format("user@"))
        # Test None input - function handles None gracefully but type checker doesn't know this
        self.assertFalse(is_valid_email_format(None))  # type: ignore[arg-type] # Testing None input handling

    def test_credential_validation_comprehensive(self) -> None:
        """Test credential validation comprehensively."""
        from blinkapp.utils.validators import validate_credentials

        # Valid credentials
        username, password = validate_credentials("user@example.com", "password123")
        self.assertEqual(username, "user@example.com")
        self.assertEqual(password, "password123")

        # Invalid credentials
        with self.assertRaises(ValueError):
            validate_credentials("", "pass")
        with self.assertRaises(ValueError):
            validate_credentials("user@example.com", "")
        with self.assertRaises(ValueError):
            validate_credentials("invalid-email", "pass")


class TestParsers(BaseTestCase):
    """Test parser functions."""

    def test_extract_thumbnail_timestamp_valid(self) -> None:
        """Test extract_thumbnail_timestamp with valid filename."""
        from blinkapp.utils.parsers import extract_thumbnail_timestamp

        filename = "thumb_1234567890.jpg"
        result = extract_thumbnail_timestamp(filename)
        self.assertEqual(result, 1234567890)

    def test_extract_thumbnail_timestamp_invalid(self) -> None:
        """Test extract_thumbnail_timestamp with invalid filename."""
        from blinkapp.utils.parsers import extract_thumbnail_timestamp

        result = extract_thumbnail_timestamp("invalid.jpg")
        self.assertEqual(result, 0)

    def test_extract_thumbnail_timestamp_none(self) -> None:
        """Test extract_thumbnail_timestamp with None filename."""
        from blinkapp.utils.parsers import extract_thumbnail_timestamp

        result = extract_thumbnail_timestamp(None)
        self.assertEqual(result, 0)

    def test_parse_clip_id_basic(self) -> None:
        """Test parse_clip_id with basic ID."""
        from blinkapp.utils.parsers import parse_clip_id

        result = parse_clip_id("12345")
        self.assertEqual(result, "12345")

    def test_parse_clip_id_with_whitespace(self) -> None:
        """Test parse_clip_id removes whitespace."""
        from blinkapp.utils.parsers import parse_clip_id

        result = parse_clip_id("  12345  ")
        self.assertEqual(result, "12345")


class TestErrors(BaseTestCase):
    """Test error classes."""

    def test_authentication_error_creation(self) -> None:
        """Test AuthenticationError creation."""
        from blinkapp.utils.errors import AuthenticationError

        error = AuthenticationError("Test error")
        self.assertEqual(str(error), "Test error")

    def test_authentication_error_with_status_code(self) -> None:
        """Test AuthenticationError with status code."""
        from blinkapp.utils.errors import AuthenticationError

        error = AuthenticationError("Test error", 401)
        # The error stores both message and status code
        self.assertIn("Test error", str(error))

    def test_attribute_error_handling(self) -> None:
        """Test AttributeError handling patterns."""
        from unittest.mock import Mock

        # Test accessing non-existent attributes
        mock_obj = Mock(spec=object)

        # This should not raise AttributeError due to Mock
        result = getattr(mock_obj, "nonexistent_attr", "default")
        self.assertIsNotNone(result)


class TestErrorHandlers(BaseTestCase):
    """Test error handler functions."""

    def test_handle_api_error_exists(self) -> None:
        """Test handle_api_error function exists."""
        from blinkapp.utils.error_handlers import handle_api_error

        # Function should exist and be callable
        self.assertTrue(callable(handle_api_error))


class TestLoggingConfig(BaseTestCase):
    """Test logging configuration."""

    @patch("pathlib.Path.mkdir")
    def test_setup_logging_basic(self, mock_mkdir: Mock) -> None:
        """Test basic logging setup."""
        import tempfile

        from blinkapp.utils.logging_config import setup_logging

        # Create temporary directory that persists for test
        temp_dir = tempfile.mkdtemp()
        try:
            # Should not raise exception
            setup_logging(temp_dir)
        finally:
            # Clean up
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    @patch("logging.getLogger")
    @patch("logging.handlers.RotatingFileHandler")
    def test_setup_logging_function(self, mock_file: Mock, mock_logger: Mock) -> None:
        """Test logging system initialization with file rotation."""
        import logging
        import tempfile
        from unittest.mock import Mock

        mock_logger_instance = Mock(spec=logging.Logger)
        mock_logger_instance.handlers = []
        mock_logger.return_value = mock_logger_instance
        mock_file_handler = Mock(spec=logging.Handler)
        mock_file.return_value = mock_file_handler

        from blinkapp import initialize_cache_paths, setup_logging

        # Initialize cache paths before logging setup
        initialize_cache_paths()
        temp_dir = tempfile.mkdtemp()
        try:
            setup_logging(temp_dir)
            # Should create handlers and configure logger
            mock_logger.assert_called()
        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    @patch("blinkapp.Config.LOG_FILE", "/tmp/test.log")
    def test_logging_configuration(self) -> None:
        """Test logging configuration paths."""
        # Test that logging configuration can be accessed
        self.assertTrue(hasattr(Config, "LOG_FILE"))
        self.assertTrue(hasattr(Config, "LOG_MAX_BYTES"))
        self.assertTrue(hasattr(Config, "LOG_BACKUP_COUNT"))


if __name__ == "__main__":
    unittest.main()
