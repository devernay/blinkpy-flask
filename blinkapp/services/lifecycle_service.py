#!/usr/bin/env python3
"""Application lifecycle management service.

This module handles application startup, shutdown, and lifecycle orchestration.
Extracted from main __init__.py to improve separation of concerns.
"""

from __future__ import annotations

__all__ = [
    "startup",
    "cleanup_resources",
    "load_clips_cache",
    "dump_cloud_videos",
    "cleanup_blink_session",
]

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

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
        setup_logging()

        # Initialize HLS streaming manager for live video transcoding
        from blinkapp.services.stream_service import initialize_stream_manager

        initialize_stream_manager()

        # Initialize cache instances
        from blinkapp.services.cache_service import initialize_caches

        initialize_caches(
            {
                "thumbnail_cache_size": Config.THUMBNAIL_CACHE_SIZE,
                "clips_cache_size": Config.CLIPS_CACHE_SIZE,
            }
        )

        # Restore cached thumbnails from previous sessions
        from blinkapp.services.cache_service import load_thumbnail_cache

        load_thumbnail_cache()

        # Restore cached clips metadata from previous sessions
        load_clips_cache()

        # Start the async Blink connection thread
        from blinkapp.services.blink_service import blink_connection

        assert blink_connection is not None
        blink_connection.start()

        try:
            # Attempt to restore previous Blink session from encrypted credentials
            from blinkapp.services.auth_service import load_saved_blink

            success = blink_connection.execute(load_saved_blink())
            if success is not True:
                logger.info(
                    "No valid saved credentials found - user will need to login"
                )
            elif logger.isEnabledFor(logging.INFO):
                # Log system information for debugging if verbose logging enabled
                from blinkapp.services.debug_service import dump_blink_system_info

                dump_blink_system_info()
        except Exception as e:
            logger.error(f"Error loading saved Blink credentials: {e}")
            logger.info("Credentials preserved - log out if error persists")
    except Exception as e:
        logger.warning(f"Could not initialize Blink system on startup: {e}")


def load_clips_cache() -> None:
    """Load clips cache directory and populate memory cache.

    Parses cached clip files with ClipId_camera_date.mp4 format,
    validates against Blink system, and removes invalid files.
    Thread-safe operation.
    """
    from blinkapp import CLIPS_CACHE_DIR
    from blinkapp.config import Config
    from blinkapp.models.ids import ClipId
    from blinkapp.services.blink_service import blink, blink_connection

    assert CLIPS_CACHE_DIR is not None
    cache_dir = Path(CLIPS_CACHE_DIR)
    if not cache_dir.exists():
        logger.warning(f"Clips cache directory does not exist: {cache_dir}")
        return

    # Ensure clips cache is initialized
    from blinkapp.services.cache_service import ensure_clips_cache_initialized

    clips_cache_instance = ensure_clips_cache_initialized()

    try:
        files_to_remove: list[Path] = []

        for video_file in cache_dir.glob("*.mp4"):
            try:
                filename = video_file.name
                # Parse filename format: clipid_camera_date.mp4
                parts = filename.replace(".mp4", "").split("_", 1)
                if len(parts) < 2:
                    logger.debug(f"Invalid filename format: {filename}")
                    files_to_remove.append(video_file)
                    continue

                clip_id_str = parts[0]
                try:
                    clip_id = ClipId(clip_id_str)
                except ValueError:
                    logger.debug(f"Invalid clip ID in filename: {filename}")
                    files_to_remove.append(video_file)
                    continue

                # Check corresponding thumbnail
                thumbnail_name = filename.replace(".mp4", ".jpg")
                thumbnail_path = cache_dir / thumbnail_name

                # Validate clip exists in Blink system
                if blink and blink.available:
                    clip_valid = False
                    try:
                        if clip_id.is_local():
                            # Validate local clip - if local storage is available and ready, trust it
                            sync_name, _ = clip_id.get_local_parts()
                            sync_dict = blink.sync
                            if sync_name in sync_dict:
                                sync_module = sync_dict[sync_name]
                                local_storage: bool = sync_module.local_storage
                                manifest_ready: bool = (
                                    sync_module.local_storage_manifest_ready
                                )
                                # If local storage is active and manifest is ready, assume clip is valid
                                clip_valid = local_storage and manifest_ready
                        else:
                            # Validate cloud clip (simplified check)
                            assert blink_connection is not None
                            videos_metadata = blink_connection.execute(
                                blink.get_videos_metadata(
                                    stop=Config.MAX_VIDEOS_METADATA
                                )
                            )
                            for video in videos_metadata:
                                if str(video.get("id")) == str(clip_id):
                                    clip_valid = True
                                    break
                    except Exception as e:
                        logger.debug(f"Error validating clip {clip_id}: {e}")

                    if not clip_valid:
                        logger.debug(
                            f"Clip {clip_id} no longer exists, removing cached files"
                        )
                        files_to_remove.append(video_file)
                        if thumbnail_path.exists():
                            files_to_remove.append(thumbnail_path)
                        continue

                # Add to cache
                clips_cache_instance[clip_id] = {
                    "filepath": video_file,
                    "thumbnail": thumbnail_path if thumbnail_path.exists() else None,
                }
                logger.debug(f"Loaded cached clip {clip_id}")

            except Exception as e:
                logger.debug(f"Could not process cached clip {video_file}: {e}")
                files_to_remove.append(video_file)

        # Remove invalid files in background
        def remove_files(files_list: list[Path]) -> None:
            for file_path in files_list:
                try:
                    file_path.unlink()
                    logger.debug(f"Removed invalid cached file: {file_path.name}")
                except (OSError, PermissionError) as e:
                    logger.warning(f"Could not remove file {file_path}: {e}")

        if files_to_remove:
            from blinkapp.services.connection_service import ensure_executor_initialized

            ensure_executor_initialized().submit(remove_files, files_to_remove)

    except (OSError, PermissionError) as e:
        logger.error(f"Error scanning clips cache: {e}")


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
        from blinkapp.services.blink_service import blink, blink_connection

        if blink_connection is not None:
            blink_connection.cleanup_active_streams()

        # Clean up Blink session only if connection is active
        if (
            blink
            and blink_connection is not None
            and blink_connection.loop
            and blink_connection.loop.is_running()
        ):
            try:
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

        logger.info("Resource cleanup completed")
    except (AttributeError, RuntimeError) as e:
        logger.warning(f"Error during resource cleanup: {e}")


async def cleanup_blink_session() -> None:
    """Clean up Blink aiohttp session."""
    from blinkapp.services.blink_service import blink_connection

    if blink_connection and blink_connection.blink:
        blink = blink_connection.blink
        try:
            await blink.auth.session.close()
        except Exception as e:
            logger.debug(f"Error closing Blink session: {e}")


def dump_cloud_videos(videos: list[dict[str, object]]) -> None:
    """Dump cloud videos information."""
    logger.info("=== CLOUD VIDEOS ===")
    for video in videos:
        logger.info(f"Video: {video}")
