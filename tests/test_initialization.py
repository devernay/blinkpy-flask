"""Test initialization utilities.

This module contains functions that are only needed for testing,
moved out of the main application code to keep it clean.
"""

import os
import sys

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def initialize_for_testing() -> None:
    """Initialize global variables for testing.

    This function should only be called from test code to ensure
    that executor and blink_connection are properly initialized
    when testing individual functions.
    """
    # Import here to avoid circular imports

    import blinkapp
    from blinkapp.services.blink_service import initialize_blink_objects

    # Initialize connections (executor and HTTP session) if not already initialized
    from blinkapp.services.connection_service import initialize_connections

    initialize_connections()
    initialize_blink_objects()

    # Initialize stream manager if not already initialized
    try:
        from blinkapp.services.stream_service import ensure_stream_manager_initialized

        ensure_stream_manager_initialized()
    except RuntimeError:
        # Stream manager not initialized, initialize it
        from blinkapp.services.stream_service import initialize_stream_manager

        initialize_stream_manager()

    # Initialize cache directories for testing if not already done
    if blinkapp.CACHE_DIR is None:
        blinkapp.initialize_cache_paths()

    # Initialize cache objects for testing
    try:
        from blinkapp.models.cache import (
            clips_cache,
            initialize_caches,
            thumbnail_cache,
        )

        # Only initialize if not already initialized
        if clips_cache is None or thumbnail_cache is None:
            initialize_caches({"thumbnail_cache_size": 10, "clips_cache_size": 10})
    except Exception:
        # If cache initialization fails, create mock caches
        from unittest.mock import MagicMock

        import blinkapp

        if (
            not hasattr(blinkapp, "clips_cache")
            or blinkapp.services.cache_service.clips_cache is None
        ):
            blinkapp.services.cache_service.clips_cache = MagicMock()
        if (
            not hasattr(blinkapp, "thumbnail_cache")
            or blinkapp.services.cache_service.thumbnail_cache is None
        ):
            blinkapp.services.cache_service.thumbnail_cache = MagicMock()
