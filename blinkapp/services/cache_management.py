"""
Cache management services for the Blink Camera Flask application.

This module provides centralized cache operations including path initialization,
cache clearing, and directory management. Extracted from the main app factory
to improve separation of concerns and maintainability.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Any

from blinkapp.config import Config

logger = logging.getLogger(__name__)

__all__ = [
    "initialize_cache_paths",
    "clear_all_caches",
    "get_cache_directories",
    "ensure_cache_directories_exist",
    "logger",  # Logger used in tests
]


def initialize_cache_paths() -> None:
    """Initialize cache directory paths from Flask config or defaults.

    Sets up cache directory structure and initializes global path variables.
    Creates directories if they don't exist and ensures proper permissions.

    Side Effects:
        - Creates cache directories if missing
        - Sets global CACHE_DIR, THUMBNAIL_CACHE_DIR, CLIPS_CACHE_DIR variables
        - Logs cache directory initialization

    Raises:
        OSError: If cache directories cannot be created
    """
    import blinkapp

    # Get cache directory from Flask config or use default
    try:
        from flask import current_app

        cache_dir_config = getattr(
            current_app.config, "CACHE_DIR", Config.DEFAULT_CACHE_DIR
        )
    except RuntimeError:
        # Outside of application context, use default
        cache_dir_config = Config.DEFAULT_CACHE_DIR

    cache_dir = Path(cache_dir_config)

    # Create cache directory if it doesn't exist
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Cache directory initialized: {cache_dir}")
    except OSError as e:
        logger.error(f"Failed to create cache directory {cache_dir}: {e}")
        raise

    # Initialize global cache path variables in main module
    blinkapp.CACHE_DIR = str(cache_dir)
    blinkapp.CREDENTIALS_FILE = str(cache_dir / Config.CREDENTIALS_FILENAME)
    blinkapp.THUMBNAIL_CACHE_DIR = str(cache_dir / Config.THUMBNAILS_SUBDIR)
    blinkapp.CLIPS_CACHE_DIR = str(cache_dir / Config.CLIPS_SUBDIR)
    blinkapp.SETTINGS_FILE = str(cache_dir / Config.SETTINGS_FILENAME)

    # Create subdirectories for thumbnails and clips
    thumbnail_dir = Path(blinkapp.THUMBNAIL_CACHE_DIR)
    clips_dir = Path(blinkapp.CLIPS_CACHE_DIR)

    try:
        thumbnail_dir.mkdir(parents=True, exist_ok=True)
        clips_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Cache subdirectories created: {thumbnail_dir}, {clips_dir}")
    except OSError as e:
        logger.error(f"Failed to create cache subdirectories: {e}")
        raise


def clear_all_caches() -> dict[str, Any]:
    """Clear all caches except credentials (background operation).

    Clears both memory caches and file caches in parallel for optimal performance.
    This operation preserves user credentials but removes all cached thumbnails,
    clips, and temporary data.

    Returns:
        Dictionary with operation status and message

    Example:
        >>> result = clear_all_caches()
        >>> print(result["status"])  # "success" or "warning"
    """
    from blinkapp.services.cache_service import (
        ensure_clips_cache_initialized,
        ensure_thumbnail_cache_initialized,
    )
    from blinkapp.services.connection_service import ensure_executor_initialized
    from blinkapp.utils.decorators import error_context
    from blinkapp.utils.errors import CacheError

    with error_context("clear cache", CacheError):
        # Clear memory caches first (fast operation) using OO cache methods
        thumbnail_cache_instance = ensure_thumbnail_cache_initialized()
        clips_cache_instance = ensure_clips_cache_initialized()

        thumbnail_cache_instance.clear()
        clips_cache_instance.clear()

        # Clear file caches (slow I/O operations)
        def clear_file_cache(cache_dir: str, cache_name: str) -> None:
            try:
                if os.path.exists(cache_dir):
                    shutil.rmtree(cache_dir)
                    os.makedirs(cache_dir, exist_ok=True)
                    logger.debug(f"Cleared {cache_name} directory")
            except OSError as e:
                logger.warning(f"Could not clear {cache_name} directory: {e}")

        # Execute file operations in parallel
        import blinkapp

        assert blinkapp.THUMBNAIL_CACHE_DIR is not None
        executor_instance = ensure_executor_initialized()
        thumbnail_future = executor_instance.submit(
            clear_file_cache, blinkapp.THUMBNAIL_CACHE_DIR, "thumbnail"
        )
        assert blinkapp.CLIPS_CACHE_DIR is not None
        clips_future = executor_instance.submit(
            clear_file_cache, blinkapp.CLIPS_CACHE_DIR, "clips"
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


def get_cache_directories() -> dict[str, str | None]:
    """Get current cache directory paths.

    Returns:
        Dictionary with cache directory paths

    Example:
        >>> dirs = get_cache_directories()
        >>> print(dirs["cache_dir"])  # Main cache directory
    """
    import blinkapp

    return {
        "cache_dir": blinkapp.CACHE_DIR,
        "thumbnail_cache_dir": blinkapp.THUMBNAIL_CACHE_DIR,
        "clips_cache_dir": blinkapp.CLIPS_CACHE_DIR,
    }


def ensure_cache_directories_exist() -> None:
    """Ensure all cache directories exist, creating them if necessary.

    Raises:
        OSError: If directories cannot be created
    """
    import blinkapp

    if not blinkapp.CACHE_DIR:
        raise RuntimeError(
            "Cache paths not initialized. Call initialize_cache_paths() first."
        )

    directories = [
        blinkapp.CACHE_DIR,
        blinkapp.THUMBNAIL_CACHE_DIR,
        blinkapp.CLIPS_CACHE_DIR,
    ]
    for directory in directories:
        if directory:
            try:
                Path(directory).mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.error(f"Failed to create directory {directory}: {e}")
                raise
