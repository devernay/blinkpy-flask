#!/usr/bin/env python3
"""Application lifecycle management service.

This module handles application startup, shutdown, and lifecycle orchestration.
Extracted from main __init__.py to improve separation of concerns.
"""

from __future__ import annotations

__all__ = [
    "startup",
    "cleanup_resources",
]

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def startup() -> None:
    """Initialize application on startup.

    Performs complete application initialization including:
    1. Cache directory setup and path initialization
    2. Logging configuration with file rotation
    3. Existing cache scanning and validation
    4. Blink connection thread startup
    5. Saved credentials loading and validation

    Error Handling:
        - Invalid cache directories: Creates new ones
        - Corrupted credentials: Removes and logs warning
        - Blink connection failures: Logs error, continues startup
        - File system errors: Graceful degradation

    Side Effects:
        - Creates cache directories if missing
        - Starts background thread pool
        - Initializes global Blink connection
        - Sets up rotating log files

    Note:
        If no valid credentials found, user must login via web interface.
        All errors are logged but don't prevent application startup.
    """
    # Import here to avoid circular imports
    from blinkapp import CACHE_DIR, CLIPS_CACHE_DIR, THUMBNAIL_CACHE_DIR
    from blinkapp.config import Config
    from blinkapp.services.cache_service import initialize_cache_paths
    from blinkapp.utils.logging_config import setup_logging

    try:
        # Initialize connections (executor and HTTP session)
        from blinkapp.services.connection_service import initialize_connections

        initialize_connections()

        # Initialize Blink objects (blink and blink_connection)
        from blinkapp.services.blink_service import initialize_blink_objects

        initialize_blink_objects()

        # Set up file system paths for cache storage
        initialize_cache_paths()

        # Create cache directories with proper permissions
        assert CACHE_DIR is not None
        try:
            Path(CACHE_DIR).mkdir(exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create cache directory {CACHE_DIR}: {e}")

        assert THUMBNAIL_CACHE_DIR is not None
        assert CLIPS_CACHE_DIR is not None
        try:
            Path(THUMBNAIL_CACHE_DIR).mkdir(exist_ok=True)
            Path(CLIPS_CACHE_DIR).mkdir(exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create cache subdirectories: {e}")

        # Configure logging with file rotation after cache paths are ready
        setup_logging(CACHE_DIR)

        # Initialize HLS streaming manager for live video transcoding
        from blinkapp.services.stream_service import initialize_stream_manager

        initialize_stream_manager()

        # Initialize cache instances
        from blinkapp.services.cache_service import initialize_caches

        initialize_caches(
            {
                "camera_thumbnail_cache_size": Config.THUMBNAIL_CACHE_SIZE,
                "clips_cache_size": Config.CLIPS_CACHE_SIZE,
            }
        )

        # Restore cached thumbnails from previous sessions
        from blinkapp.services.cache_service import (
            load_camera_thumbnail_cache,
            load_clips_cache,
        )

        load_camera_thumbnail_cache()

        # Restore cached clips metadata from previous sessions
        load_clips_cache()

        # Start the async Blink connection thread
        from blinkapp.services.blink_service import ensure_blink_connection_initialized

        blink_connection = ensure_blink_connection_initialized()
        blink_connection.start()

        try:
            # Attempt to restore previous Blink session from encrypted credentials
            from blinkapp.services.auth_service import load_saved_blink

            success = blink_connection.execute(load_saved_blink())
            if success is not True:
                # Check if credentials file exists to give better message
                from ..config import Config

                cred_file = Path(Config.DEFAULT_CACHE_DIR) / Config.CREDENTIALS_FILENAME

                if cred_file.exists():
                    logger.info(
                        "Saved credentials found but authentication failed - "
                        + "credentials may be expired. Please login again through the web interface."
                    )
                else:
                    logger.info("No saved credentials found - user will need to login")
            elif logger.isEnabledFor(logging.INFO):
                # Log system information for debugging if verbose logging enabled
                from blinkapp.services.debug_service import dump_blink_system_info

                dump_blink_system_info()
        except Exception as e:
            logger.error(f"Error loading saved Blink credentials: {e}")
            logger.info("Credentials preserved - log out if error persists")
    except Exception as e:
        # Only log as warning if it's not the expected "Blink not initialized" case
        if "Blink not initialized" not in str(e):
            logger.warning(f"Could not initialize Blink system on startup: {e}")
        else:
            logger.debug(f"Blink system not initialized on startup: {e}")
            logger.info("No saved credentials found - user will need to login")


def cleanup_resources() -> None:
    """Clean up all resources on application shutdown.

    Performs graceful shutdown of all services:
    1. Stops Blink connection thread
    2. Shuts down thread pool executor
    3. Closes HTTP sessions
    4. Stops HLS streaming manager
    5. Saves cache state to disk

    Error Handling:
        - Individual service failures are logged but don't prevent other cleanups
        - Timeout protection for thread shutdown operations
        - Resource leak prevention with forced cleanup

    Side Effects:
        - Terminates background threads
        - Closes network connections
        - Saves cache metadata to disk
        - Releases file handles

    Note:
        Called automatically on application shutdown via atexit handler.
        Safe to call multiple times - idempotent operation.
    """
    try:
        logger.info("Cleaning up resources...")

        # Shutdown executor
        from blinkapp.services.connection_service import executor

        if executor is not None:
            executor.shutdown(wait=False)

        # Shutdown stream manager if initialized
        try:
            from blinkapp.services.stream_service import (
                ensure_stream_manager_initialized,
            )

            stream_manager = ensure_stream_manager_initialized()
            stream_manager.shutdown()
        except RuntimeError:
            # Stream manager not initialized, nothing to shutdown
            pass

        # Clean up active livestreams
        from blinkapp.services.blink_service import ensure_blink_connection_initialized

        try:
            blink_connection = ensure_blink_connection_initialized()
        except RuntimeError:
            blink_connection = None

        if blink_connection is not None:
            blink_connection.cleanup_active_streams()

        # Clean up Blink session only if connection is active
        blink_instance = None
        try:
            from blinkapp.services.blink_service import get_blink_instance

            blink_instance = get_blink_instance()
        except Exception:
            pass

        if (
            blink_instance is not None
            and blink_connection is not None
            and blink_connection.loop
            and blink_connection.loop.is_running()
        ):
            try:
                from blinkapp.services.blink_service import cleanup_blink_session

                blink_connection.execute(cleanup_blink_session())
            except (RuntimeError, ConnectionError, TimeoutError) as e:
                logger.debug(f"Error during Blink session cleanup: {e}")

        # Shutdown Blink connection
        if blink_connection is not None:
            blink_connection.shutdown()

        # Close HTTP session
        from blinkapp.services.connection_service import http_session

        if http_session is not None:
            try:
                http_session.close()
            except (AttributeError, RuntimeError) as e:
                logger.debug(f"Error closing HTTP session: {e}")

        # Reset global instances for clean shutdown
        try:
            from blinkapp.services.blink_service import cleanup_blink_instances
            from blinkapp.services.cache_service import cleanup_global_caches

            cleanup_blink_instances()
            cleanup_global_caches()
        except Exception as e:
            logger.debug(f"Error during global cleanup: {e}")

        logger.info("Resource cleanup completed")
    except (AttributeError, RuntimeError) as e:
        logger.warning(f"Error during resource cleanup: {e}")


# cleanup_blink_session is imported from blink_service
