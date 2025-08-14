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
