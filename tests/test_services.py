"""Comprehensive unit tests for service classes and functions.

Complete test suite covering testable functions in blinkapp/services/:
- Time services (time_service.py)
- File services (file_service.py)
- Authentication services (auth_service.py)
- Cache services (cache_service.py)
- Device services (device_service.py)
"""

import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from tests.test_base import BaseTestCase


class TestTimeService(BaseTestCase):
    """Test time service functions."""

    def test_get_current_timestamp_with_provider(self) -> None:
        """Test get current timestamp with custom provider."""
        from blinkapp.services.time_service import get_current_timestamp

        mock_provider = Mock(return_value=1234567890)
        result = get_current_timestamp(mock_provider)
        self.assertEqual(result, 1234567890)
        mock_provider.assert_called_once()

    def test_get_current_timestamp_default_provider(self) -> None:
        """Test get current timestamp with default provider."""
        from blinkapp.services.time_service import get_current_timestamp

        result = get_current_timestamp()
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_get_current_time_with_provider(self) -> None:
        """Test get current time with custom provider."""
        from blinkapp.services.time_service import get_current_time

        mock_time = datetime(2024, 1, 1, 12, 0, 0)
        mock_provider = Mock(return_value=mock_time)
        result = get_current_time(mock_provider)
        self.assertEqual(result, mock_time)
        mock_provider.assert_called_once()

    def test_get_current_time_default_provider(self) -> None:
        """Test get current time with default provider."""
        from blinkapp.services.time_service import get_current_time

        result = get_current_time()
        self.assertIsInstance(result, datetime)


class TestFileService(BaseTestCase):
    """Test file service functions."""

    def test_write_file_safely_success(self) -> None:
        """Test successful file write."""
        from blinkapp.services.file_service import write_file_safely

        mock_writer = Mock()
        result = write_file_safely(Path("/test"), b"data", mock_writer)
        self.assertTrue(result)
        mock_writer.assert_called_once_with(Path("/test"), b"data")

    def test_read_file_safely_success(self) -> None:
        """Test successful file read."""
        from blinkapp.services.file_service import read_file_safely

        mock_reader = Mock(return_value=b"data")
        result = read_file_safely(Path("/test"), mock_reader)
        self.assertEqual(result, b"data")
        mock_reader.assert_called_once_with(Path("/test"))

    def test_check_file_exists_true(self) -> None:
        """Test file exists check returns true."""
        from blinkapp.services.file_service import check_file_exists

        mock_checker = Mock(return_value=True)
        result = check_file_exists(Path("/test"), mock_checker)
        self.assertTrue(result)

    def test_check_file_exists_false(self) -> None:
        """Test file exists check returns false."""
        from blinkapp.services.file_service import check_file_exists

        mock_checker = Mock(return_value=False)
        result = check_file_exists(Path("/test"), mock_checker)
        self.assertFalse(result)

    def test_create_directory_safely_success(self) -> None:
        """Test successful directory creation."""
        from blinkapp.services.file_service import create_directory_safely

        mock_creator = Mock()
        result = create_directory_safely(Path("/test"), mock_creator)
        self.assertTrue(result)
        mock_creator.assert_called_once_with(Path("/test"))


class TestAuthService(BaseTestCase):
    """Test authentication service functions."""

    def test_is_blink_authenticated_true(self) -> None:
        """Test blink authentication check returns true."""
        from blinkapp.services.auth_service import is_blink_authenticated

        mock_blink = Mock()
        mock_blink.auth.token = "valid_token"
        result = is_blink_authenticated(mock_blink)
        self.assertTrue(result)

    def test_is_blink_authenticated_false_no_token(self) -> None:
        """Test blink authentication check returns false when no token."""
        from blinkapp.services.auth_service import is_blink_authenticated

        mock_blink = Mock()
        mock_blink.auth.token = None
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

    def test_extract_username_domain_valid(self) -> None:
        """Test username extraction from email (returns domain part)."""
        from blinkapp.services.auth_service import extract_username_domain

        # The function actually returns the domain part, not username
        result = extract_username_domain("test@example.com")
        self.assertEqual(result, "example.com")

    def test_extract_username_domain_invalid(self) -> None:
        """Test username extraction from invalid email."""
        from blinkapp.services.auth_service import extract_username_domain

        result = extract_username_domain("invalid_email")
        self.assertEqual(result, "")

    @patch("blinkapp.services.auth_service.logger")
    def test_validate_credentials_valid(self, mock_logger) -> None:
        """Test credential validation with valid inputs."""
        from blinkapp.services.auth_service import validate_credentials

        result = validate_credentials("test@example.com", "password123")
        self.assertTrue(result)

    @patch("blinkapp.services.auth_service.logger")
    def test_validate_credentials_invalid_email(self, mock_logger) -> None:
        """Test credential validation with invalid email."""
        from blinkapp.services.auth_service import validate_credentials

        result = validate_credentials("invalid", "password123")
        self.assertFalse(result)

    @patch("blinkapp.services.auth_service.logger")
    def test_validate_credentials_empty_password(self, mock_logger) -> None:
        """Test credential validation with empty password."""
        from blinkapp.services.auth_service import validate_credentials

        result = validate_credentials("test@example.com", "")
        self.assertFalse(result)

    def test_create_auth_config(self) -> None:
        """Test auth config creation."""
        from blinkapp.services.auth_service import create_auth_config

        result = create_auth_config("test@example.com", "password123")
        self.assertIn("username", result)
        self.assertIn("password", result)
        self.assertEqual(result["username"], "test@example.com")
        self.assertEqual(result["password"], "password123")


class TestCacheService(BaseTestCase):
    """Test cache service functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Reset global caches before each test
        from blinkapp.services.cache_service import reset_global_caches

        reset_global_caches()

    def test_initialize_caches(self) -> None:
        """Test cache initialization."""
        from blinkapp.services.cache_service import initialize_caches

        config = {"CLIPS_CACHE_SIZE": 50, "THUMBNAIL_CACHE_SIZE": 100}
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

        config = {"CLIPS_CACHE_SIZE": 50, "THUMBNAIL_CACHE_SIZE": 100}
        initialize_caches(config)

        cache = ensure_clips_cache_initialized()
        self.assertIsNotNone(cache)

    def test_ensure_camera_thumbnail_cache_initialized_after_init(self) -> None:
        """Test camera thumbnail cache initialization after global init."""
        from blinkapp.services.cache_service import (
            ensure_camera_thumbnail_cache_initialized,
            initialize_caches,
        )

        config = {"CLIPS_CACHE_SIZE": 50, "THUMBNAIL_CACHE_SIZE": 100}
        initialize_caches(config)

        cache = ensure_camera_thumbnail_cache_initialized()
        self.assertIsNotNone(cache)

    def test_reset_global_caches(self) -> None:
        """Test resetting global caches."""
        from blinkapp.services.cache_service import (
            initialize_caches,
            reset_global_caches,
        )

        # Initialize caches
        config = {"CLIPS_CACHE_SIZE": 50, "THUMBNAIL_CACHE_SIZE": 100}
        initialize_caches(config)

        # Reset caches
        reset_global_caches()

        # Verify caches are reset
        from blinkapp.services.cache_service import camera_thumbnail_cache, clips_cache

        self.assertIsNone(clips_cache)
        self.assertIsNone(camera_thumbnail_cache)


class TestDeviceService(BaseTestCase):
    """Test device service functions."""

    def test_format_device_temperature_celsius_conversion(self) -> None:
        """Test device temperature formatting with Celsius conversion."""
        from blinkapp.services.device_service import format_device_temperature

        # The function converts Fahrenheit to Celsius
        result = format_device_temperature(77, "C")  # 77°F = 25°C
        self.assertEqual(result, "25.0°C")

    def test_format_device_temperature_fahrenheit_no_conversion(self) -> None:
        """Test device temperature formatting in Fahrenheit without conversion."""
        from blinkapp.services.device_service import format_device_temperature

        result = format_device_temperature(77, "F")
        self.assertEqual(result, "77.0°F")

    def test_format_device_temperature_none(self) -> None:
        """Test device temperature formatting with None value."""
        from blinkapp.services.device_service import format_device_temperature

        result = format_device_temperature(None, "C")
        self.assertEqual(result, "N/A")


if __name__ == "__main__":
    unittest.main()
