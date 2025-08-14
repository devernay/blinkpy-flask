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
from typing import Any, cast
from unittest.mock import MagicMock, Mock

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Test constants
TEST_CAMERA_ID = 12345
TEST_NETWORK_ID = 12345
TEST_USERNAME = "test@example.com"
TEST_PASSWORD = "password123"
TEST_2FA_CODE = "123456"
TEST_CACHE_DIR = "/tmp/test_cache"


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
    if blinkapp.CACHE_DIR is None:
        blinkapp.initialize_cache_paths()

    # Initialize cache objects
    try:
        from blinkapp.services.cache_service import initialize_caches

        initialize_caches({"thumbnail_cache_size": 10, "clips_cache_size": 10})
    except Exception:
        import blinkapp.services.cache_service as cache_service

        if (
            not hasattr(cache_service, "clips_cache")
            or cache_service.clips_cache is None
        ):
            cache_service.clips_cache = MagicMock()
        if (
            not hasattr(cache_service, "thumbnail_cache")
            or cache_service.thumbnail_cache is None
        ):
            cache_service.thumbnail_cache = MagicMock()


def setup_test_globals():
    """Function to call in setUp methods to initialize globals."""
    initialize_for_testing()


def with_app_initialized[F: Callable[..., Any]](func: F) -> F:
    """Decorator to ensure app globals are initialized for testing."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        initialize_for_testing()
        return cast(Any, func)(*args, **kwargs)

    return cast(F, wrapper)


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

        mock_blink = Mock()
        mock_blink.available = available

        if sync_data:
            mock_blink.sync = sync_data
        else:
            mock_blink.sync = {}

        if cameras:
            for sync_name, camera_list in cameras.items():
                mock_sync = Mock()
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

    def create_mock_camera(self, camera_id=TEST_CAMERA_ID, name="Test Camera"):
        """Create a mock camera with common attributes."""
        from unittest.mock import Mock

        mock_camera = Mock()
        mock_camera.camera_id = camera_id
        mock_camera.name = name
        mock_camera.snap_picture = Mock()
        return mock_camera

    def create_mock_sync(
        self, network_id=TEST_NETWORK_ID, armed=False, online=True, cameras=None
    ):
        """Create a mock sync module with common attributes."""
        from unittest.mock import Mock

        mock_sync = Mock()
        mock_sync.network_id = network_id
        mock_sync.arm = armed
        mock_sync.online = online
        mock_sync.cameras = cameras or {}
        return mock_sync


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
