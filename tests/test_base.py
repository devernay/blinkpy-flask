"""Centralized test base classes and utilities.

This module provides all test utilities in one place:
- BaseTestCase for consistent setup/teardown
- Test initialization functions
- Mock utilities
- Decorators for test setup
"""

import functools
import os
import sys
import unittest
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar
from unittest.mock import MagicMock, Mock

from blinkpy.blinkpy import Blink
from blinkpy.camera import BlinkCamera
from blinkpy.livestream import BlinkLiveStream
from blinkpy.sync_module import BlinkSyncModule

from blinkapp.models.cache import CameraThumbnailCache, ClipsCache
from blinkapp.services.stream_service import StreamManager

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# Standalone mock factory functions (can be used without inheriting from BaseTestCase)
def create_mock_camera(
    camera_id: int | str = 12345,
    name: str = "Test Camera",
    battery: str | None = "ok",
    temperature: int | float | None = 72,
    wifi_strength: int | None = -45,
    motion_enabled: bool = True,
    thumbnail: str | None = None,
    last_record: Any = None,
    updated_at: str | None = None,
    temperature_calibrated: float | None = None,
    battery_voltage: int | None = None,
    armed: bool | None = None,
    enabled: bool | None = None,
) -> Mock:
    """Create a mock camera with common attributes."""
    from unittest.mock import Mock

    mock_camera = Mock(spec=BlinkCamera)
    mock_camera.camera_id = camera_id
    mock_camera.name = name
    mock_camera.snap_picture = Mock(spec=callable)
    mock_camera.motion_enabled = motion_enabled
    mock_camera.battery = battery
    mock_camera.temperature = temperature
    mock_camera.temperature_calibrated = (
        temperature_calibrated
        if temperature_calibrated is not None
        else (temperature + 0.5 if temperature is not None else None)
    )
    mock_camera.wifi_strength = wifi_strength
    mock_camera.thumbnail = thumbnail
    mock_camera.last_record = last_record
    mock_camera.updated_at = updated_at

    # Optional attributes
    if battery_voltage is not None:
        mock_camera.battery_voltage = battery_voltage
    if armed is not None:
        mock_camera.armed = armed
    if enabled is not None:
        mock_camera.enabled = enabled

    return mock_camera


def create_mock_blink_instance(
    available: bool = True,
    sync_data: dict[str, Any] | None = None,
    networks: dict[str, Any] | None = None,
    cameras: dict[int | str, Any] | None = None,
    refresh: Callable[[], Any] | None = None,
    start: Callable[[], Any] | None = None,
    save: Callable[[], Any] | None = None,
    videos: dict[str, list[Any]] | None = None,
) -> Mock:
    """Create a mock blink instance with common methods."""
    from unittest.mock import Mock

    mock_blink = Mock(spec=Blink)
    mock_blink.available = available
    mock_blink.get_clip_url = Mock(return_value="http://example.com/clip.mp4")

    # Create async mock for get_videos_metadata
    async def mock_get_videos_metadata(stop: int = 25) -> list[dict[str, Any]]:
        # Return metadata that includes the test clip ID
        return [
            {
                "id": "123456",
                "media": "http://example.com/video.mp4",
                "thumbnail": "http://example.com/thumb.jpg",
                "created_at": "2023-01-01T00:00:00Z",
            }
        ]

    mock_blink.get_videos_metadata = mock_get_videos_metadata

    # Create async mock for do_http_get
    async def mock_do_http_get(url: str) -> Mock:
        mock_response = Mock()

        async def mock_read() -> bytes:
            return b"video_content"

        mock_response.read = mock_read
        return mock_response

    mock_blink.do_http_get = mock_do_http_get
    mock_blink.sync = sync_data or {}
    mock_blink.networks = networks or {}
    mock_blink.cameras = cameras or {}
    mock_blink.videos = videos or {"all": []}
    if refresh:
        mock_blink.refresh = refresh
    if start:
        mock_blink.start = start
    if save:
        mock_blink.save = save
    return mock_blink


def create_mock_stream_manager(
    active_streams: dict[str, Any] | None = None, cleanup_on_exit: bool = True
) -> Mock:
    """Create a mock StreamManager with common attributes."""
    from unittest.mock import Mock

    mock_manager = Mock(spec=StreamManager)
    mock_manager.active_streams = active_streams or {}
    mock_manager.cleanup_on_exit = cleanup_on_exit
    mock_manager.cleanup = Mock(spec=callable)
    return mock_manager


def create_mock_live_stream(
    stream_id: str = "test_stream", stop_error: Exception | None = None
) -> Mock:
    """Create a mock BlinkLiveStream with common attributes."""
    from unittest.mock import Mock

    mock_stream = Mock(spec=BlinkLiveStream)
    mock_stream.id = stream_id
    if stop_error:
        mock_stream.stop.side_effect = stop_error
    else:
        mock_stream.stop = Mock(spec=callable)
    return mock_stream


def create_mock_camera_cache(
    size: int = 10, max_size: int | None = 100, hit_rate: float | None = 0.85
) -> Mock:
    """Create a mock CameraThumbnailCache with common attributes."""
    from unittest.mock import Mock

    mock_cache = Mock(spec=CameraThumbnailCache)
    mock_cache.__len__ = Mock(return_value=size)
    if max_size is not None:
        mock_cache.max_size = max_size
    if hit_rate is not None:
        mock_cache.hit_rate = hit_rate
    return mock_cache


def create_mock_clips_cache(size: int = 5, max_size: int = 50) -> Mock:
    """Create a mock ClipsCache with common attributes."""
    from unittest.mock import Mock

    mock_cache = Mock(spec=ClipsCache)
    mock_cache.__len__ = Mock(return_value=size)
    mock_cache.max_size = max_size
    mock_cache.get = Mock(return_value=None)
    mock_cache.add_clip = Mock(spec=callable)
    return mock_cache


def create_mock_sync(
    network_id: int = 12345,
    armed: bool = False,
    online: bool = True,
    cameras: dict[str, Any] | None = None,
    local_storage: bool = False,
    local_storage_manifest_ready: bool = False,
    name: str | None = None,
    refresh: Callable[[], Any] | None = None,
    _local_storage: dict[str, Any] | None = None,
) -> Mock:
    """Create a mock sync module with common attributes."""
    from unittest.mock import Mock

    mock_sync = Mock(spec=BlinkSyncModule)
    mock_sync.network_id = network_id
    mock_sync.arm = armed
    mock_sync.online = online
    mock_sync.cameras = cameras or {}
    mock_sync.local_storage = local_storage
    mock_sync.local_storage_manifest_ready = local_storage_manifest_ready
    mock_sync._local_storage = _local_storage or (
        {"manifest": []} if local_storage else {}
    )
    if name:
        mock_sync.name = name
    if refresh is not None:
        mock_sync.refresh = refresh
    else:
        mock_sync.refresh = Mock(spec=callable)
    return mock_sync


def create_mock_clip_item(
    clip_id: str | int = "123",
    created_at: Any = None,
    name: str = "Test Camera",
    size: int | None = None,
    url: str | None = None,
    is_local_storage: bool = True,
) -> Mock:
    """Create a mock clip item with proper spec."""
    from datetime import datetime
    from unittest.mock import Mock

    if is_local_storage:
        from blinkpy.sync_module import LocalStorageMediaItem

        mock_item = Mock(spec=LocalStorageMediaItem)
        # LocalStorageMediaItem.url is a method that returns URL
        mock_item.url = Mock(return_value=url or "http://example.com/local_video.mp4")
    else:
        # Cloud clips are dict[str, str | bool | None]
        # Keys: "id", "created_at", "device_name", "media", "thumbnail", "deleted"
        # Values: strings, bools, or None (no integers in cloud clips)
        mock_item = Mock(spec=dict[str, str | bool | None])
        if url:
            mock_item.url = url

    mock_item.id = clip_id
    mock_item.created_at = created_at or datetime(2023, 1, 1, 12, 0, 0)
    mock_item.name = name

    if size is not None:
        mock_item.size = size

    return mock_item


# Test constants
class TestData:
    """Centralized test data constants."""

    CAMERA_ID = 12345
    NETWORK_ID = 12345
    USERNAME = "test@example.com"
    PASSWORD = "password123"
    TWO_FA_CODE = "123456"
    CACHE_DIR = "/tmp/test_cache"

    # API Response constants
    SUCCESS_STATUS = 200
    NOT_FOUND_STATUS = 404
    ERROR_STATUS = 500


# Backward compatibility
TEST_CAMERA_ID = TestData.CAMERA_ID
TEST_NETWORK_ID = TestData.NETWORK_ID
TEST_USERNAME = TestData.USERNAME
TEST_PASSWORD = TestData.PASSWORD
TEST_2FA_CODE = TestData.TWO_FA_CODE
TEST_CACHE_DIR = TestData.CACHE_DIR


def initialize_for_testing() -> None:
    """Initialize global variables for testing."""
    import blinkapp
    from blinkapp.services.blink_service import initialize_blink_objects
    from blinkapp.services.connection_service import initialize_connections

    initialize_connections()
    initialize_blink_objects()

    # Initialize stream manager
    try:
        from blinkapp.services.stream_service import ensure_stream_manager_initialized

        ensure_stream_manager_initialized()
    except RuntimeError:
        from blinkapp.services.stream_service import initialize_stream_manager

        initialize_stream_manager()

    # Initialize cache directories
    if not blinkapp.CACHE_DIR:
        from blinkapp.services.cache_service import initialize_cache_paths

        initialize_cache_paths()

    # Initialize cache objects
    try:
        from blinkapp.services.cache_service import initialize_caches

        initialize_caches({"camera_thumbnail_cache_size": 10, "clips_cache_size": 10})
    except Exception:
        import blinkapp.services.cache_service as cache_service

        if (
            not hasattr(cache_service, "clips_cache")
            or cache_service.clips_cache is None
        ):
            cache_service.clips_cache = MagicMock(spec=ClipsCache)
        if (
            not hasattr(cache_service, "camera_thumbnail_cache")
            or cache_service.camera_thumbnail_cache is None
        ):
            cache_service.camera_thumbnail_cache = MagicMock(spec=CameraThumbnailCache)


def setup_test_globals() -> None:
    """Function to call in setUp methods to initialize globals."""
    initialize_for_testing()


P = ParamSpec("P")
T = TypeVar("T")


def with_app_initialized(func: Callable[P, T]) -> Callable[P, T]:  # noqa: UP047
    """Decorator to ensure app globals are initialized for testing."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        initialize_for_testing()
        return func(*args, **kwargs)

    return wrapper


class BaseTestCase(unittest.TestCase):
    """Unified base test case with setup and cleanup."""

    def setUp(self) -> None:
        """Initialize test environment."""
        super().setUp()
        initialize_for_testing()

    def tearDown(self) -> None:
        """Clean up global state after each test."""
        try:
            from blinkapp.services import blink_service, connection_service

            # Reset Blink objects
            blink_service.blink = None
            blink_service.blink_connection = None

            # Reset connection service
            if hasattr(connection_service, "executor"):
                connection_service.executor = None
        except Exception:
            # Ignore teardown errors to prevent masking test failures
            pass


class FlaskTestCase(BaseTestCase):
    """Base test case for Flask application tests."""

    def setUp(self) -> None:
        """Set up Flask test client and configuration."""
        super().setUp()
        import tempfile

        from blinkapp import app

        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self.app.config["CACHE_DIR"] = tempfile.mkdtemp()
        self.client = self.app.test_client()

        # Initialize cache paths for Flask tests
        import blinkapp

        blinkapp.initialize_cache_paths()

    def setup_mock_blink(self, available=True, sync_data=None, cameras=None):
        """Helper to set up mock Blink objects with common configuration."""
        from unittest.mock import Mock

        mock_blink = Mock(spec=object)
        mock_blink.available = available

        if sync_data:
            mock_blink.sync = sync_data
        else:
            mock_blink.sync = {}

        if cameras:
            for sync_name, camera_list in cameras.items():
                mock_sync = create_mock_sync()
                mock_sync.cameras = {
                    f"camera{i}": cam for i, cam in enumerate(camera_list)
                }
                mock_blink.sync[sync_name] = mock_sync

        return mock_blink

    def setup_mock_connection(self, return_value=None, side_effect=None):
        """Helper to set up mock connection with coroutine cleanup."""
        from unittest.mock import Mock

        return Mock(
            execute=mock_execute_with_coroutine_cleanup(return_value, side_effect)
        )

    def assert_api_success(self, response, expected_status=200):
        """Assert API response is successful with expected format."""
        import json

        self.assertEqual(response.status_code, expected_status)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        return data

    def assert_api_error(self, response, expected_status=500, error_contains=None):
        """Assert API response is an error with expected format."""
        import json

        self.assertEqual(response.status_code, expected_status)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        if error_contains:
            self.assertIn(error_contains, data.get("error", ""))
        return data

    def assert_response_contains(self, response, expected_status=200, *content_checks):
        """Assert response status and content contains specified strings."""
        self.assertEqual(response.status_code, expected_status)
        for content in content_checks:
            if isinstance(content, str):
                self.assertIn(content.encode(), response.data)
            else:
                self.assertIn(content, response.data)
        return response

    def assert_redirect(self, response, expected_location_contains=None):
        """Assert response is a redirect with optional location check."""
        self.assertEqual(response.status_code, 302)
        if expected_location_contains:
            self.assertIn(expected_location_contains, response.location or "")
        return response

    def run_test_cases(self, test_cases):
        """Run multiple test cases with consistent pattern."""
        for case in test_cases:
            with self.subTest(**case):
                method = case.get("method", "GET")
                path = case["path"]
                expected_status = case.get("status", 200)
                kwargs = {
                    k: v
                    for k, v in case.items()
                    if k not in ["method", "path", "status"]
                }
                self.check_endpoint(method, path, expected_status, **kwargs)

    @staticmethod
    def make_test_name(feature, scenario):
        """Generate consistent test method names."""
        return f"test_{feature}_{scenario}"

    def skip_if_no_flask(self):
        """Skip test if Flask app is not available."""
        if not hasattr(self, "client"):
            self.skipTest("Flask client not available")

    def check_endpoint(self, method, path, expected_status=200, **kwargs):
        """Generic endpoint tester to reduce boilerplate."""
        client_method = getattr(self.client, method.lower())
        response = client_method(path, **kwargs)

        # Check status first
        self.assertEqual(response.status_code, expected_status)

        # Only try JSON parsing for API endpoints or endpoints that return JSON errors
        if path.startswith("/api/") or (
            expected_status >= 400 and "json" in response.content_type
        ):
            if expected_status == 200:
                return self.assert_api_success(response)
            else:
                return self.assert_api_error(response, expected_status)
        else:
            return response

    def mock_blink_system(self, available=True, systems=None):
        """Context manager for mocking blink system with common setup."""
        from contextlib import contextmanager
        from unittest.mock import patch

        @contextmanager
        def _mock():
            with (
                patch("blinkapp.services.blink_service.blink") as mock_blink,
                patch("blinkapp.services.blink_service.blink_connection") as mock_conn,
            ):
                mock_blink.available = available
                mock_blink.sync = systems or {}
                mock_conn.execute = mock_execute_with_coroutine_cleanup()
                yield mock_blink, mock_conn

        return _mock()

    def with_blink_mocks(self, available=True, sync_data=None):
        """Decorator to automatically patch blink service with common setup."""
        from unittest.mock import patch

        def decorator(test_method):
            @patch("blinkapp.services.blink_service.blink_connection")
            @patch("blinkapp.services.blink_service.blink")
            def wrapper(self, mock_blink, mock_connection):
                mock_blink.available = available
                mock_blink.sync = sync_data or {}
                mock_connection.execute = mock_execute_with_coroutine_cleanup()
                return test_method(self, mock_blink, mock_connection)

            return wrapper

        return decorator


def mock_execute_with_coroutine_cleanup(return_value=None, side_effect=None):
    """Create a mock execute function that properly handles coroutines."""

    def mock_execute(coro):
        # Close the coroutine to prevent warnings
        if hasattr(coro, "close"):
            coro.close()
        elif hasattr(coro, "__aenter__"):  # Handle async context managers
            try:
                coro.close()
            except Exception:
                pass
        if side_effect:
            if isinstance(side_effect, Exception):
                raise side_effect
            else:
                raise side_effect
        return return_value

    return Mock(side_effect=mock_execute)


def create_video_metadata(
    clip_id: str = "123456",
    created_at: str = "2023-01-01T12:00:00Z",
    device_name: str = "Test Camera",
    deleted: bool = False,
    media: str = "http://example.com/video.mp4",
    thumbnail: str | None = "http://example.com/thumb.jpg",
    size: int | None = 1024,
) -> dict[str, str | int | bool | None]:
    """Create properly typed video metadata for tests."""
    return {
        "id": clip_id,
        "created_at": created_at,
        "device_name": device_name,
        "deleted": deleted,
        "media": media,
        "thumbnail": thumbnail,
        "size": size,
    }
