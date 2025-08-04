"""Test initialization utilities.

This module contains functions that are only needed for testing,
moved out of the main application code to keep it clean.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


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

    # Initialize cache directories for testing if not already done
    if blinkapp.CACHE_DIR is None:
        blinkapp.initialize_cache_paths()
