#!/usr/bin/env python3
"""
Blink Camera Flask Web Interface

A comprehensive web application for managing Blink camera systems with features
including:
- Multi-system support with real-time camera thumbnails
- Live streaming via TCP to HLS transcoding using Blink's init_livestream()
- Cloud and local clip management with thumbnail generation
- User settings (temperature units, clip retention, thumbnail sizes)
- Mobile-optimized responsive interface
- Background processing for clip downloads and thumbnail generation

Main components:
- Flask web server with RESTful API
- Async Blink connection management
- HLS stream manager for live video from TCP streams
- Intelligent caching with configurable retention
- Thread-safe operations with proper cleanup

Author: Fredderic Devernay
License: MIT
"""

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Authentication and session management
# Caching system for thumbnails, clips, and metadata

# ID validation and type safety
# Type definitions for better code clarity
# Blink camera library - third-party integration

# Application configuration
from blinkapp.config import Config
from blinkapp.models.ids import ClipId
from blinkapp.models.responses import create_api_response

# Admin routes
from blinkapp.routes.admin import register_admin_routes
from blinkapp.routes.auth import (
    register_auth_routes,
    setup_auth_routes,
)

# Camera operations and route handlers
from blinkapp.routes.camera import (
    setup_camera_routes,
)

# Clip management routes
from blinkapp.routes.clips import setup_clips_routes

# Settings management routes
from blinkapp.routes.settings import register_settings_routes, setup_settings_routes

# System management routes
from blinkapp.routes.system import setup_system_routes

# Route decorators and error handling
# Route decorators for API endpoints
from blinkapp.utils.decorators import (
    ensure_blink_available,
    error_context,
)

# Utilities
from blinkapp.utils.error_handlers import handle_api_error, require_sync_module

# Utilities
from blinkapp.utils.errors import (
    CacheError,
)
from blinkapp.utils.logging_config import setup_logging

# Live streaming management


if TYPE_CHECKING:
    pass

# Third-party imports

# Flask framework components
# Type alias for Flask responses
from flask import (
    Flask,
)

# Explicitly define what this module exports
__all__ = [
    # Flask application instance
    "app",
    # Core initialization functions
    # Utility functions (now imported from utils modules)
    "handle_api_error",
    "require_sync_module",
    "setup_logging",
    "initialize_cache_paths",
    # Cache management
    "clear_all_caches",
    "load_clips_cache",
    # Configuration and debugging
    "dump_cloud_videos",
    # Application lifecycle
    "startup",
    "cleanup_resources",
    "main",
    # API utilities
    "create_api_response",
]

# ============================================================================
# Flask Application Setup
# ============================================================================

# Create Flask app instance with secure configuration
app = Flask(__name__, template_folder="../templates")
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-change-in-production")

# ============================================================================
# Global Application State
# ============================================================================

# File system paths for application data storage
# Cache configuration - initialized in initialize_cache_paths()
CACHE_DIR: str = ""  # Base cache directory
CREDENTIALS_FILE: str = ""  # Encrypted credentials storage
THUMBNAIL_CACHE_DIR: str = ""  # Camera thumbnail cache
CLIPS_CACHE_DIR: str = ""  # Downloaded clips storage
SETTINGS_FILE: str = ""  # User settings persistence

# ============================================================================
# Error Handling and API Response Utilities
# ============================================================================


# Configure logging - will be reconfigured after cache paths are set
logger = logging.getLogger(__name__)


# ============================================================================
# Cache and File System Management
# ============================================================================


def _init_cache_paths(cache_dir: Path) -> None:
    """Initialize cache path constants."""
    global \
        CACHE_DIR, \
        CREDENTIALS_FILE, \
        THUMBNAIL_CACHE_DIR, \
        CLIPS_CACHE_DIR, \
        SETTINGS_FILE
    CACHE_DIR = str(cache_dir)  # pyright: ignore[reportConstantRedefinition]
    CREDENTIALS_FILE = str(cache_dir / Config.CREDENTIALS_FILENAME)  # pyright: ignore[reportConstantRedefinition]
    THUMBNAIL_CACHE_DIR = str(cache_dir / Config.THUMBNAILS_SUBDIR)  # pyright: ignore[reportConstantRedefinition]
    CLIPS_CACHE_DIR = str(cache_dir / Config.CLIPS_SUBDIR)  # pyright: ignore[reportConstantRedefinition]
    SETTINGS_FILE = str(cache_dir / Config.SETTINGS_FILENAME)  # pyright: ignore[reportConstantRedefinition]


def initialize_cache_paths() -> None:
    """Initialize cache directory paths from Flask config or defaults.

    Sets global path variables for cache directories and credential file.
    Uses Flask app config 'CACHE_DIR' or defaults to Config.DEFAULT_CACHE_DIR.
    This function must be called before any cache operations or logging setup.

    The cache directory structure created:
    - CACHE_DIR/: Base cache directory
    - CACHE_DIR/thumbnails/: Camera thumbnail cache
    - CACHE_DIR/clips/: Downloaded clips storage
    - CACHE_DIR/blink.json: Encrypted credentials
    - CACHE_DIR/settings.json: User preferences
    - CACHE_DIR/blink_app.log: Application logs

    Side Effects:
        Updates global variables: CACHE_DIR, CREDENTIALS_FILE,
        THUMBNAIL_CACHE_DIR, CLIPS_CACHE_DIR, SETTINGS_FILE

    Raises:
        OSError: If cache directory cannot be created or accessed
    """
    global \
        CACHE_DIR, \
        CREDENTIALS_FILE, \
        THUMBNAIL_CACHE_DIR, \
        CLIPS_CACHE_DIR, \
        SETTINGS_FILE

    # Get cache directory from Flask config or use sensible default
    cache_dir_str = app.config.get("CACHE_DIR", Config.DEFAULT_CACHE_DIR)
    assert isinstance(cache_dir_str, str)
    cache_dir = Path(cache_dir_str)

    # Initialize cache-related paths using the base cache directory
    _init_cache_paths(cache_dir)


# Cache configuration constants
CLIPS_CACHE_SIZE = Config.CLIPS_CACHE_SIZE  # Maximum number of clips to cache

# ============================================================================
# Global Variable Validation and Type Guards
# ============================================================================


# Camera thumbnail update functionality


def clear_all_caches() -> dict[str, object]:
    """Clear all caches except credentials (background operation)."""
    with error_context("clear cache", CacheError):
        # Clear memory caches first (fast operation) using OO cache methods
        from blinkapp.services.cache_service import (
            ensure_clips_cache_initialized,
            ensure_thumbnail_cache_initialized,
        )

        thumbnail_cache_instance = ensure_thumbnail_cache_initialized()
        clips_cache_instance = ensure_clips_cache_initialized()

        thumbnail_cache_instance.clear()
        clips_cache_instance.clear()

        # Clear file caches (slow I/O operations)
        def clear_file_cache(cache_dir: str, cache_name: str) -> None:
            try:
                if os.path.exists(cache_dir):
                    import shutil

                    shutil.rmtree(cache_dir)
                    os.makedirs(cache_dir, exist_ok=True)
                    logger.debug(f"Cleared {cache_name} directory")
            except OSError as e:
                logger.warning(f"Could not clear {cache_name} directory: {e}")

        # Execute file operations in parallel
        assert THUMBNAIL_CACHE_DIR is not None
        from blinkapp.services.connection_service import ensure_executor_initialized

        executor_instance = ensure_executor_initialized()
        thumbnail_future = executor_instance.submit(
            clear_file_cache, THUMBNAIL_CACHE_DIR, "thumbnail"
        )
        assert CLIPS_CACHE_DIR is not None
        clips_future = executor_instance.submit(
            clear_file_cache, CLIPS_CACHE_DIR, "clips"
        )

        # Wait for completion with timeout
        try:
            thumbnail_future.result(timeout=Config.CACHE_CLEAR_TIMEOUT)
            clips_future.result(timeout=Config.CACHE_CLEAR_TIMEOUT)
            logger.info("All caches cleared successfully")
            return {"status": "success", "message": "All caches cleared successfully"}
        except Exception as e:
            logger.warning(f"Cache clearing completed with errors: {e}")
            return {
                "status": "warning",
                "message": f"Cache clearing completed with errors: {e}",
            }


# ============================================================================
# API Routes - System Management
# ============================================================================


# ============================================================================
# API Routes - Clip Management
# ============================================================================


@ensure_blink_available
# ============================================================================
# API Routes - Configuration and Settings
# ============================================================================


def dump_cloud_videos(videos: list[dict[str, object]]) -> None:
    """Dump cloud videos information."""
    logger.info("=== CLOUD VIDEOS ===")
    try:
        logger.info(f"Found {len(videos)} cloud videos:")
        for video in videos:
            logger.info(f"  - {video}")
    except Exception as e:
        logger.error(f"Error processing cloud videos: {e}")


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
                from blinkapp.services.utils_service import dump_blink_system_info

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


# Removed generate_thumbnail_async - thumbnails only generated on clip download


# Stream management functionality


async def cleanup_blink_session() -> None:
    """Clean up Blink aiohttp session."""
    from blinkapp.services.blink_service import blink_connection

    if blink_connection and blink_connection.blink:
        blink = blink_connection.blink
        try:
            await blink.auth.session.close()
        except Exception as e:
            logger.debug(f"Error closing Blink session: {e}")


def cleanup_resources() -> None:
    """Clean up all resources on application shutdown.

    Stops all active HLS streams and their FFmpeg processes.
    Terminates the Blink event loop gracefully.
    Called automatically on exit via atexit handler and signal handlers.
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


# LRUCache automatically handles eviction, no manual cleanup needed


# Set up authentication routes
setup_auth_routes(app)

# Set up camera routes
setup_camera_routes(app)

# Set up clip routes
setup_clips_routes(app)

# Set up system routes
setup_system_routes(app)

# Set up settings routes
setup_settings_routes(app)

# Set up admin routes
register_admin_routes(app)

# Register additional auth routes (index)
register_auth_routes(app)

# Register additional settings routes (config)
register_settings_routes(app)

# Import main function for module execution
if __name__ == "__main__":
    from blinkapp.__main__ import main

    main()
