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
    from concurrent.futures import ThreadPoolExecutor

    import blinkapp
    from blink_connection import BlinkConnection
    from config import Config
    from stream_manager import StreamConfig, StreamManager

    # Initialize executor for background tasks if not already initialized
    if blinkapp.executor is None:
        blinkapp.executor = ThreadPoolExecutor(
            max_workers=Config.THREAD_POOL_MAX_WORKERS
        )

    # Initialize Blink connection if not already initialized
    if blinkapp.blink_connection is None:
        blinkapp.blink_connection = BlinkConnection(
            timeout=Config.BLINK_CONNECTION_TIMEOUT
        )

    # Initialize stream manager if not already initialized
    if blinkapp.stream_manager is None:
        stream_config = StreamConfig(
            segment_time=Config.HLS_SEGMENT_TIME,
            list_size=Config.HLS_LIST_SIZE,
            timeout=Config.FFMPEG_TIMEOUT,
            idle_timeout=Config.STREAM_IDLE_TIMEOUT,
        )
        blinkapp.stream_manager = StreamManager(stream_config)

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

        if not hasattr(blinkapp, "clips_cache") or blinkapp.clips_cache is None:
            blinkapp.clips_cache = MagicMock()
        if not hasattr(blinkapp, "thumbnail_cache") or blinkapp.thumbnail_cache is None:
            blinkapp.thumbnail_cache = MagicMock()
