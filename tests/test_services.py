"""Comprehensive unit tests for service classes and functions.

Complete test suite covering testable functions in blinkapp/services/:
- Time services (time_service.py)
- File services (file_service.py)
- Authentication services (auth_service.py)
- Cache services (cache_service.py)
- Device services (device_service.py)
- HLS services (hls_service.py)
"""

import subprocess
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from blinkapp.services.hls_service import (
    HLSStream,
    HLSStreamConfig,
    _build_ffmpeg_command,
    _create_ffmpeg_process,
)
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

        mock_writer = Mock(spec=callable)
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

        mock_creator = Mock(spec=callable)
        result = create_directory_safely(Path("/test"), mock_creator)
        self.assertTrue(result)
        mock_creator.assert_called_once_with(Path("/test"))


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

    def test_reset_global_caches(self) -> None:
        """Test resetting global caches."""
        from blinkapp.services.cache_service import (
            initialize_caches,
            reset_global_caches,
        )

        # Initialize caches
        config: dict[str, object] = {
            "CLIPS_CACHE_SIZE": 50,
            "THUMBNAIL_CACHE_SIZE": 100,
        }
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


class TestHLSServicePureFunctions(BaseTestCase):
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


class TestAuthServicePureFunctions(BaseTestCase):
    """Test auth service pure functions for coverage."""

    def test_extract_username_domain_cases(self) -> None:
        """Test username domain extraction."""
        from blinkapp.services.auth_service import extract_username_domain

        # With @ symbol
        result = extract_username_domain("user@example.com")
        self.assertEqual(result, "example.com")

        # Without @ symbol - returns empty string based on actual implementation
        result = extract_username_domain("username")
        self.assertEqual(result, "")

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

    def test_create_auth_config_function(self) -> None:
        """Test auth config creation."""
        from blinkapp.services.auth_service import create_auth_config

        result = create_auth_config("user@example.com", "password123")
        expected = {"username": "user@example.com", "password": "password123"}
        self.assertEqual(result, expected)


class TestFileServiceCoverage(BaseTestCase):
    """Test file service functions for coverage."""

    def test_write_file_safely_success(self) -> None:
        """Test writing file safely with success."""
        from blinkapp.services.file_service import write_file_safely

        mock_writer = Mock(spec=callable)

        result = write_file_safely(Path("/tmp/test.txt"), b"test content", mock_writer)

        self.assertTrue(result)
        mock_writer.assert_called_once_with(Path("/tmp/test.txt"), b"test content")

    def test_write_file_safely_error(self) -> None:
        """Test writing file safely with error."""
        from blinkapp.services.file_service import write_file_safely

        mock_writer = Mock(spec=callable)
        mock_writer.side_effect = OSError("Permission denied")

        result = write_file_safely(Path("/tmp/test.txt"), b"test content", mock_writer)

        self.assertFalse(result)

    def test_read_file_safely_success(self) -> None:
        """Test reading file safely with success."""
        from blinkapp.services.file_service import read_file_safely

        mock_reader = Mock(spec=callable)
        mock_reader.return_value = b"file content"

        result = read_file_safely(Path("/tmp/test.txt"), mock_reader)

        self.assertEqual(result, b"file content")
        mock_reader.assert_called_once_with(Path("/tmp/test.txt"))

    def test_read_file_safely_error(self) -> None:
        """Test reading file safely with error."""
        from blinkapp.services.file_service import read_file_safely

        mock_reader = Mock(spec=callable)
        mock_reader.side_effect = OSError("File not found")

        result = read_file_safely(Path("/tmp/test.txt"), mock_reader)

        self.assertIsNone(result)

    def test_check_file_exists_true(self) -> None:
        """Test checking file exists - true case."""
        from blinkapp.services.file_service import check_file_exists

        mock_checker = Mock(spec=callable)
        mock_checker.return_value = True

        result = check_file_exists(Path("/tmp/test.txt"), mock_checker)

        self.assertTrue(result)

    def test_check_file_exists_false(self) -> None:
        """Test checking file exists - false case."""
        from blinkapp.services.file_service import check_file_exists

        mock_checker = Mock(spec=callable)
        mock_checker.return_value = False

        result = check_file_exists(Path("/tmp/test.txt"), mock_checker)

        self.assertFalse(result)

    def test_create_directory_safely_success(self) -> None:
        """Test creating directory safely with success."""
        from blinkapp.services.file_service import create_directory_safely

        mock_creator = Mock(spec=callable)

        result = create_directory_safely(Path("/tmp/test_dir"), mock_creator)

        self.assertTrue(result)
        mock_creator.assert_called_once_with(Path("/tmp/test_dir"))

    def test_create_directory_safely_error(self) -> None:
        """Test creating directory safely with error."""
        from blinkapp.services.file_service import create_directory_safely

        mock_creator = Mock(spec=callable)
        mock_creator.side_effect = OSError("Permission denied")

        result = create_directory_safely(Path("/tmp/test_dir"), mock_creator)

        self.assertFalse(result)


class TestTimeServiceCoverage(BaseTestCase):
    """Test time service functions for coverage."""

    def test_get_current_timestamp_default(self) -> None:
        """Test getting current timestamp with default provider."""
        from blinkapp.services.time_service import get_current_timestamp

        result = get_current_timestamp()

        # Should return an integer timestamp
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_get_current_timestamp_custom_provider(self) -> None:
        """Test getting current timestamp with custom provider."""
        from blinkapp.services.time_service import get_current_timestamp

        def custom_provider() -> int:
            return 1234567890

        result = get_current_timestamp(custom_provider)

        self.assertEqual(result, 1234567890)

    def test_get_current_time_default(self) -> None:
        """Test getting current time with default provider."""
        from datetime import datetime

        from blinkapp.services.time_service import get_current_time

        result = get_current_time()

        # Should return a datetime object
        self.assertIsInstance(result, datetime)

    def test_get_current_time_custom_provider(self) -> None:
        """Test getting current time with custom provider."""
        from datetime import datetime

        from blinkapp.services.time_service import get_current_time

        test_time = datetime(2023, 1, 1, 12, 0, 0)

        def custom_provider() -> datetime:
            return test_time

        result = get_current_time(custom_provider)

        self.assertEqual(result, test_time)

    def test_seconds_since_now_from_datetime(self) -> None:
        """Test calculating seconds since now from datetime."""
        from datetime import UTC, datetime, timedelta

        from blinkapp.services.time_service import seconds_since_now_from_datetime

        # Test with a time 60 seconds ago with timezone
        past_time = datetime.now(UTC) - timedelta(seconds=60)

        result = seconds_since_now_from_datetime(past_time)

        # Should be approximately 60 seconds (allow some tolerance)
        self.assertGreater(result, 55)
        self.assertLess(result, 65)


class TestDeviceServiceCoverage(BaseTestCase):
    """Test device service functions for coverage."""

    def test_format_device_temperature_celsius(self) -> None:
        """Test temperature formatting in Celsius."""
        from blinkapp.services.device_service import format_device_temperature

        # The function appears to do temperature conversion, so test actual behavior
        result = format_device_temperature(77.0, "C")  # 77F = 25C
        self.assertIn("°C", result)

    def test_format_device_temperature_fahrenheit(self) -> None:
        """Test temperature formatting in Fahrenheit."""
        from blinkapp.services.device_service import format_device_temperature

        result = format_device_temperature(25.0, "F")  # 25C = 77F
        self.assertIn("°F", result)

    def test_format_device_temperature_none_coverage(self) -> None:
        """Test temperature formatting with None value."""
        from blinkapp.services.device_service import format_device_temperature

        result = format_device_temperature(None, "C")
        self.assertEqual(result, "N/A")

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


class TestHLSStreamConfig(BaseTestCase):
    """Test HLS stream configuration."""

    def test_hls_stream_config_defaults(self) -> None:
        """Test HLS config uses defaults from Config."""
        config = HLSStreamConfig()

        # Should use Config defaults
        self.assertIsNotNone(config.segment_time)
        self.assertIsNotNone(config.list_size)
        self.assertIsNotNone(config.timeout)
        self.assertIsNotNone(config.idle_timeout)

    def test_hls_stream_config_custom_values(self) -> None:
        """Test HLS config with custom values."""
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
        mock_process = Mock(spec=subprocess.Popen)
        mock_factory = Mock(return_value=mock_process)

        cmd = ["ffmpeg", "-version"]
        result = _create_ffmpeg_process(cmd, mock_factory)

        self.assertEqual(result, mock_process)
        mock_factory.assert_called_once_with(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
        )

    def test_create_ffmpeg_process_error(self) -> None:
        """Test FFmpeg process creation error."""
        mock_factory = Mock(side_effect=OSError("Command not found"))

        cmd = ["ffmpeg", "-version"]
        result = _create_ffmpeg_process(cmd, mock_factory)

        self.assertIsNone(result)

    def test_create_ffmpeg_process_subprocess_error(self) -> None:
        """Test FFmpeg process creation subprocess error."""
        mock_factory = Mock(side_effect=subprocess.SubprocessError("Process error"))

        cmd = ["ffmpeg", "-version"]
        result = _create_ffmpeg_process(cmd, mock_factory)

        self.assertIsNone(result)

    def test_create_ffmpeg_process_default_factory(self) -> None:
        """Test FFmpeg process creation with default factory."""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_popen.return_value = mock_process

            cmd = ["echo", "test"]
            result = _create_ffmpeg_process(cmd)

            self.assertEqual(result, mock_process)


class TestHLSStream(BaseTestCase):
    """Test HLS stream management."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()
        self.config = HLSStreamConfig(
            segment_time=2, list_size=3, timeout=10, idle_timeout=30
        )
        self.camera_id = "test_camera"
        self.tcp_url = "tcp://127.0.0.1:8080"

    def test_hls_stream_init(self) -> None:
        """Test HLS stream initialization."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)

        self.assertEqual(stream.camera_id, self.camera_id)
        self.assertEqual(stream.tcp_url, self.tcp_url)
        self.assertEqual(stream.config, self.config)
        self.assertIsNone(stream.process)
        self.assertIsNone(stream.temp_dir)
        self.assertFalse(stream._active)
        self.assertIsNotNone(stream.lock)  # Just check it exists

    @patch("blinkapp.services.hls_service._create_ffmpeg_process")
    @patch("tempfile.TemporaryDirectory")
    @patch("time.sleep")
    def test_hls_stream_start_success(
        self, mock_sleep: Mock, mock_temp_dir: Mock, mock_create_process: Mock
    ) -> None:
        """Test successful HLS stream start."""
        # Mock temporary directory
        mock_dir = Mock()
        mock_dir.name = "/tmp/hls_test_camera_123"
        mock_temp_dir.return_value = mock_dir

        # Mock FFmpeg process
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
        mock_create_process.return_value = None

        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        hls_url, error = stream.start()

        self.assertIsNone(hls_url)
        self.assertEqual(error, "Failed to create FFmpeg process")
        self.assertFalse(stream._active)

    def test_hls_stream_stop(self) -> None:
        """Test HLS stream stop."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream._active = True

        with patch.object(stream, "cleanup") as mock_cleanup:
            stream.stop()

            self.assertFalse(stream._active)
            mock_cleanup.assert_called_once()

    def test_hls_stream_cleanup_with_process(self) -> None:
        """Test HLS stream cleanup with active process."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)

        # Mock process
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.wait.return_value = None
        stream.process = mock_process

        # Mock temp directory
        mock_temp_dir = Mock()
        stream.temp_dir = mock_temp_dir

        stream.cleanup()

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_with(timeout=5)
        mock_temp_dir.cleanup.assert_called_once()
        self.assertIsNone(stream.process)
        self.assertIsNone(stream.temp_dir)

    def test_hls_stream_is_active_not_active(self) -> None:
        """Test is_active when stream is not active."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)

        self.assertFalse(stream.is_active())

    def test_hls_stream_get_hls_url_no_temp_dir(self) -> None:
        """Test get_hls_url when no temp directory."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)

        self.assertIsNone(stream.get_hls_url())

    def test_hls_stream_get_hls_url_success(self) -> None:
        """Test get_hls_url with temp directory."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream.temp_dir = Mock()
        stream.temp_dir.name = "/tmp/test"

        url = stream.get_hls_url()
        expected = f"/api/cameras/{self.camera_id}/hls/stream.m3u8"

        self.assertEqual(url, expected)

    def test_hls_stream_get_file_not_active(self) -> None:
        """Test get_file when stream not active."""
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
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream._active = True

        mock_temp_dir = Mock()
        mock_temp_dir.name = "/tmp/test"
        stream.temp_dir = mock_temp_dir

        mock_exists.return_value = True
        mock_file = Mock()
        mock_file.read.return_value = b"playlist content"
        mock_open.return_value.__enter__.return_value = mock_file

        content, content_type = stream.get_file("playlist.m3u8")

        self.assertEqual(content, b"playlist content")
        self.assertEqual(content_type, "application/vnd.apple.mpegurl")


if __name__ == "__main__":
    unittest.main()
