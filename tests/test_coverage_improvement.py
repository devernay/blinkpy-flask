#!/usr/bin/env python3
"""Tests to improve code coverage to 70%."""

from unittest.mock import Mock, patch

from test_base import FlaskTestCase


class TestAuthService(FlaskTestCase):
    """Test auth_service.py (currently 18% coverage)."""

    def test_is_authenticated_false(self) -> None:
        """Test is_authenticated when not authenticated."""
        from blinkapp.services.auth_service import is_authenticated

        result = is_authenticated()
        self.assertFalse(result)

    @patch("blinkapp.services.blink_service.blink")
    def test_is_authenticated_true(self, mock_blink: Mock) -> None:
        """Test is_authenticated when authenticated."""
        from blinkapp.services.auth_service import is_authenticated

        mock_blink.available = True
        result = is_authenticated()
        self.assertTrue(result)


class TestUtilsService(FlaskTestCase):
    """Test utils_service.py (currently 17% coverage)."""


class TestStreamService(FlaskTestCase):
    """Test stream_service.py (currently 31% coverage)."""

    def test_initialize_stream_manager(self) -> None:
        """Test initialize_stream_manager function."""
        from blinkapp.services.stream_service import initialize_stream_manager

        initialize_stream_manager()

    def test_ensure_stream_manager_initialized(self) -> None:
        """Test ensure_stream_manager_initialized function."""
        from blinkapp.services.stream_service import ensure_stream_manager_initialized

        result = ensure_stream_manager_initialized()
        self.assertIsNotNone(result)

    def test_is_stream_active_false(self) -> None:
        """Test is_stream_active when stream is not active."""
        from blinkapp.models.ids import CameraId
        from blinkapp.services.stream_service import is_stream_active

        camera_id = CameraId(12345)
        result = is_stream_active(camera_id)
        self.assertFalse(result)


class TestMainApp(FlaskTestCase):
    """Test main app functions (currently 20% coverage)."""

    def test_create_api_response_success(self) -> None:
        """Test create_api_response with success."""
        from blinkapp import create_api_response

        response, status = create_api_response(success=True, data={"test": "data"})
        self.assertEqual(status, 200)
        self.assertTrue(response["success"])

    def test_create_api_response_error(self) -> None:
        """Test create_api_response with error."""
        from blinkapp import create_api_response

        response, status = create_api_response(success=False, error="Test error")
        self.assertEqual(status, 200)  # Default status is 200
        self.assertFalse(response["success"])

    def test_create_api_response_custom_status(self) -> None:
        """Test create_api_response with custom status."""
        from blinkapp import create_api_response

        response, status = create_api_response(
            success=False, error="Test error", status_code=500
        )
        self.assertEqual(status, 500)
        self.assertFalse(response["success"])


class TestCacheService(FlaskTestCase):
    """Test cache_service.py (currently 30% coverage)."""

    def test_get_cache_stats(self) -> None:
        """Test get_cache_stats function."""
        from blinkapp.services.cache_service import get_cache_stats

        stats = get_cache_stats()
        self.assertIsInstance(stats, dict)

    def test_initialize_caches(self) -> None:
        """Test initialize_caches function."""
        from blinkapp.services.cache_service import initialize_caches

        config = {"thumbnail_cache_size": 10, "clips_cache_size": 10}
        initialize_caches(config)

    def test_ensure_thumbnail_cache_initialized(self) -> None:
        """Test ensure_thumbnail_cache_initialized function."""
        from blinkapp.services.cache_service import ensure_thumbnail_cache_initialized

        result = ensure_thumbnail_cache_initialized()
        self.assertIsNotNone(result)


class TestValidators(FlaskTestCase):
    """Test validators.py (currently 18% coverage)."""

    def test_validate_string_input_too_long(self) -> None:
        """Test validate_string_input with too long input."""
        from blinkapp.utils.validators import validate_string_input

        with self.assertRaises(ValueError):
            validate_string_input("very long string", 5, "test_field")

    def test_extract_thumbnail_timestamp_valid(self) -> None:
        """Test extract_thumbnail_timestamp with valid URL."""
        from blinkapp.utils.parsers import extract_thumbnail_timestamp

        url = "https://example.com/thumb.jpg?ts=1234567890"
        result = extract_thumbnail_timestamp(url)
        self.assertEqual(result, 1234567890)

    def test_extract_thumbnail_timestamp_none(self) -> None:
        """Test extract_thumbnail_timestamp with None."""
        from blinkapp.utils.parsers import extract_thumbnail_timestamp

        result = extract_thumbnail_timestamp(None)
        self.assertEqual(result, 0)

    def test_format_time_ago_recent(self) -> None:
        """Test format_time_ago with recent timestamp."""
        from blinkapp.utils.formatters import format_time_ago

        result = format_time_ago("2025-01-01T10:00:00")
        self.assertIsInstance(result, str)


class TestDecorators(FlaskTestCase):
    """Test decorators.py (currently 27% coverage)."""

    def test_error_context_decorator(self) -> None:
        """Test error_context decorator."""
        from blinkapp.utils.decorators import error_context

        @error_context("test operation")
        def test_function() -> str:
            return "success"

        result = test_function()
        self.assertEqual(result, "success")


class TestModelsIds(FlaskTestCase):
    """Test models/ids.py (currently 62% coverage)."""

    def test_camera_id_creation(self) -> None:
        """Test CameraId creation."""
        from blinkapp.models.ids import CameraId

        camera_id = CameraId(12345)
        self.assertEqual(int(camera_id), 12345)

    def test_network_id_creation(self) -> None:
        """Test NetworkId creation."""
        from blinkapp.models.ids import NetworkId

        network_id = NetworkId(12345)
        self.assertEqual(int(network_id), 12345)

    def test_network_id_validation_invalid(self) -> None:
        """Test NetworkId validation with invalid input."""
        from blinkapp.models.ids import NetworkId

        with self.assertRaises(ValueError):
            NetworkId("invalid")

    def test_clip_id_creation(self) -> None:
        """Test ClipId creation."""
        from blinkapp.models.ids import ClipId

        clip_id = ClipId("test_clip_123")
        self.assertEqual(str(clip_id), "test_clip_123")

    def test_clip_id_validation_invalid(self) -> None:
        """Test ClipId validation with invalid input."""
        from blinkapp.models.ids import ClipId

        with self.assertRaises(ValueError):
            ClipId("")


class TestSystemService(FlaskTestCase):
    """Test system_service.py (currently 13% coverage)."""

    @patch("blinkapp.services.blink_service.blink")
    def test_get_systems_empty(self, mock_blink: Mock) -> None:
        """Test get_systems when no systems available."""
        from blinkapp.services.system_service import get_systems

        mock_blink.sync = {}
        result = get_systems()
        self.assertEqual(result, {"systems": []})

    @patch("blinkapp.services.blink_service.blink")
    def test_get_systems_with_data(self, mock_blink: Mock) -> None:
        """Test get_systems with mock data."""
        from blinkapp.services.system_service import get_systems

        mock_sync = Mock()
        mock_sync.network_id = 12345
        mock_sync.arm = False
        mock_sync.online = True
        mock_blink.sync = {"test": mock_sync}

        result = get_systems()
        self.assertIsInstance(result, dict)
        self.assertIn("systems", result)


class TestConnectionService(FlaskTestCase):
    """Test connection_service.py (currently 40% coverage)."""

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
