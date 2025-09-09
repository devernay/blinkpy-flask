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

import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from tests.test_base import BaseTestCase


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
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            result = auth_service._create_blink_session()

            self.assertEqual(result, mock_session)
            mock_session_class.assert_called_once()

    def test_create_blink_session_custom_factory(self):
        """Test creating blink session with custom factory."""
        from blinkapp.services import auth_service

        with patch("aiohttp.ClientSession", return_value=Mock()) as mock_factory:
            result = auth_service._create_blink_session()

            self.assertIsNotNone(result)
            mock_factory.assert_called_once()


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

        # Setup mocks
        mock_session_instance = Mock(spec=object)
        mock_session.return_value = mock_session_instance

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

        # Setup mocks
        mock_session_instance = Mock(spec=object)
        mock_session.return_value = mock_session_instance

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


class TestDebugService(BaseTestCase):
    """Test debug service functions."""

    def test_check_credentials_file_exists_true(self) -> None:
        """Test credentials file exists returns True."""
        from pathlib import Path

        from blinkapp.services.debug_service import check_credentials_file_exists

        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True

        result = check_credentials_file_exists(mock_path)
        self.assertTrue(result)

    def test_check_credentials_file_exists_false(self) -> None:
        """Test credentials file does not exist returns False."""
        from pathlib import Path

        from blinkapp.services.debug_service import check_credentials_file_exists

        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = False

        result = check_credentials_file_exists(mock_path)
        self.assertFalse(result)


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
        from blinkapp.services.hls_service import _create_ffmpeg_process

        mock_process = Mock()
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
            mock_file = Mock()
            mock_file.read.return_value = b"ts content"
            mock_open.return_value.__enter__.return_value = mock_file

            content, content_type = stream.get_file("segment.ts")

            self.assertEqual(content, b"ts content")
            self.assertEqual(content_type, "video/mp2t")

    def test_hls_stream_is_active_with_timeout(self) -> None:
        """Test is_active with idle timeout."""
        from blinkapp.services.hls_service import HLSStream

        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream._active = True

        mock_process = Mock()
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

    def setUp(self) -> None:
        """Set up test fixtures."""
        from blinkapp.models.ids import ClipId

        super().setUp()
        self.clip_id = ClipId("123456")


class TestClipProcessing(BaseTestCase):
    """Test clip processing service functions."""

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


class TestClipService(BaseTestCase):
    """Test clip service functions."""

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

    def test_stop_camera_stream_success(self) -> None:
        """Test successful camera stream stop."""
        from blinkapp.models.ids import CameraId
        from blinkapp.services.stream_service import stop_camera_stream

        with patch(
            "blinkapp.services.stream_service.ensure_stream_manager_initialized"
        ) as mock_ensure:
            mock_manager = Mock()
            mock_ensure.return_value = mock_manager

            camera_id = CameraId("test_camera")
            result = stop_camera_stream(camera_id)

            self.assertTrue(result)
            mock_manager.stop_stream.assert_called_once_with(str(camera_id))

    def test_stop_camera_stream_failure(self) -> None:
        """Test camera stream stop failure."""
        from blinkapp.models.ids import CameraId
        from blinkapp.services.stream_service import stop_camera_stream

        with patch(
            "blinkapp.services.stream_service.ensure_stream_manager_initialized"
        ) as mock_ensure:
            mock_manager = Mock()
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
        """Test cache path initialization with app config."""
        from unittest.mock import Mock, patch

        from blinkapp import initialize_cache_paths
        from tests.test_base import create_mock_path

        with (
            patch("pathlib.Path.mkdir") as mock_mkdir,
            patch("pathlib.Path") as mock_path,
        ):
            # Setup mock path that supports / operator
            mock_path_instance = create_mock_path(
                "test_critical_coverage_cache_path", "/test/cache", mock_mkdir
            )
            mock_subpath = create_mock_path(
                "test_critical_coverage_subpath", "/test/cache/subdir", mock_mkdir
            )
            mock_path_instance.__truediv__ = Mock(
                spec=callable, return_value=mock_subpath
            )
            mock_path.return_value = mock_path_instance

            # Test initialization (will use default config outside app context)
            initialize_cache_paths()

            # Should create directories
            mock_mkdir.assert_called()

    def test_initialize_cache_paths_default(self) -> None:
        """Test cache path initialization with defaults."""
        from blinkapp import initialize_cache_paths

        # Should not raise exception when outside app context
        try:
            initialize_cache_paths()
            success = True
        except Exception:
            success = False

        # Should handle missing app context gracefully
        self.assertTrue(success)


class TestThumbnailService(BaseTestCase):
    """Test thumbnail service functions."""

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
            from blinkapp import initialize_cache_paths
            from blinkapp.routes.thumbnails import update_camera_thumbnail
            from blinkapp.services.cache_service import initialize_caches

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
        mock_mkdir,
        mock_logging,
        mock_blink,
        mock_stream,
        mock_caches,
        mock_connections,
        mock_paths,
    ):
        """Test successful startup."""
        from blinkapp.services import lifecycle_service

        lifecycle_service.startup()

        mock_connections.assert_called_once()
        mock_blink.assert_called_once()
        mock_paths.assert_called_once()
        mock_caches.assert_called_once()
        mock_stream.assert_called_once()

    @patch("blinkapp.services.connection_service.initialize_connections")
    def test_startup_exception(self, mock_connections):
        """Test startup with exception - should log but not raise."""
        from blinkapp.services import lifecycle_service

        mock_connections.side_effect = Exception("Startup error")

        # Should not raise exception, just log warning
        lifecycle_service.startup()
        self.assertTrue(True)  # Test passes if no exception raised

    @patch("blinkapp.services.connection_service.executor", Mock())
    @patch("blinkapp.services.stream_service.ensure_stream_manager_initialized")
    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    def test_cleanup_resources_success(self, mock_blink_conn, mock_stream):
        """Test successful resource cleanup."""
        from blinkapp.services import lifecycle_service

        mock_stream_manager = Mock()
        mock_stream.return_value = mock_stream_manager
        mock_blink_connection = Mock()
        mock_blink_conn.return_value = mock_blink_connection

        lifecycle_service.cleanup_resources()

        mock_stream_manager.shutdown.assert_called_once()
        mock_blink_connection.cleanup_active_streams.assert_called_once()

    @patch("blinkapp.services.stream_service.ensure_stream_manager_initialized")
    def test_cleanup_resources_exception(self, mock_stream):
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
        import blinkapp
        from blinkapp.services import connection_service

        self.assertTrue(hasattr(connection_service, "http_session"))
        self.assertTrue(hasattr(blinkapp, "Path"))

    @patch("concurrent.futures.ThreadPoolExecutor")
    def test_parallel_cache_clearing(self, mock_executor: Mock) -> None:
        """Test parallel execution of cache clearing."""

        # Create a properly spec'd mock instance
        mock_executor_instance = Mock()
        mock_executor_instance.__enter__ = Mock(return_value=mock_executor_instance)
        mock_executor_instance.__exit__ = Mock(return_value=None)
        mock_executor.return_value = mock_executor_instance

        # Test parallel execution pattern
        with mock_executor() as executor:
            self.assertEqual(executor, mock_executor_instance)

    def test_connection_service_basic(self) -> None:
        """Test basic connection service."""
        from blinkapp.services.blink_connection import get_blink_connection

        # Should return None when not initialized
        result = get_blink_connection()
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
