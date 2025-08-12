"""Cache service for Blink Camera Flask application.

This module handles all cache-related business logic including
cache initialization, management, and cleanup operations.
"""

from __future__ import annotations

__all__ = [
    "initialize_caches",
    "ensure_clips_cache_initialized",
    "ensure_thumbnail_cache_initialized",
    "ensure_cache_paths_initialized",
    "load_thumbnail_cache",
    "get_cache_stats",
]

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from blinkapp.models.cache import ClipsCache, ThumbnailCache

logger = logging.getLogger(__name__)

# Global cache instances
clips_cache: ClipsCache | None = None
thumbnail_cache: ThumbnailCache | None = None


def initialize_caches(config: dict[str, Any]) -> None:
    """Initialize global cache instances with configuration.

    Args:
        config: Configuration dictionary with cache settings
    """
    global thumbnail_cache, clips_cache
    from blinkapp.models.cache import ClipsCache, ThumbnailCache

    thumbnail_cache = ThumbnailCache(maxsize=config.get("thumbnail_cache_size", 100))
    clips_cache = ClipsCache(maxsize=config.get("clips_cache_size", 50))

    logger.info("Cache instances initialized successfully")


def ensure_clips_cache_initialized():
    """Ensure clips cache is initialized.

    Returns:
        Initialized clips cache instance

    Raises:
        RuntimeError: If clips_cache hasn't been initialized
    """
    if clips_cache is None:
        raise RuntimeError(
            "Clips cache not initialized. Call initialize_caches() first."
        )
    return clips_cache


def ensure_thumbnail_cache_initialized():
    """Ensure thumbnail cache is initialized.

    Returns:
        Initialized thumbnail cache instance

    Raises:
        RuntimeError: If thumbnail_cache hasn't been initialized
    """
    if thumbnail_cache is None:
        raise RuntimeError(
            "Thumbnail cache not initialized. Call initialize_caches() first."
        )
    return thumbnail_cache


def ensure_cache_paths_initialized() -> None:
    """Ensure cache paths are initialized, raising an error if not.

    This function serves as a type guard for mypy to understand that
    the cache path variables are not None after this call.

    Raises:
        RuntimeError: If cache paths haven't been initialized
    """
    import blinkapp

    if (
        blinkapp.CACHE_DIR is None
        or blinkapp.CREDENTIALS_FILE is None
        or blinkapp.THUMBNAIL_CACHE_DIR is None
        or blinkapp.CLIPS_CACHE_DIR is None
        or blinkapp.SETTINGS_FILE is None
    ):
        raise RuntimeError(
            "Cache paths not initialized. Call initialize_blink() first."
        )


def get_cache_stats() -> dict[str, dict[str, int | float]]:
    """Get statistics for all cache instances.

    Returns:
        Dictionary with statistics for each cache type
    """
    stats = {}

    thumbnail_cache = ensure_thumbnail_cache_initialized()
    if thumbnail_cache:
        stats["thumbnail_cache"] = thumbnail_cache.get_stats()

    clips_cache = ensure_clips_cache_initialized()
    if clips_cache:
        stats["clips_cache"] = clips_cache.get_stats()

    return stats


def load_thumbnail_cache() -> None:
    """Load and validate thumbnail cache from disk.

    Scans thumbnail cache directory for existing files and populates
    the in-memory cache with validated entries. Performs cleanup of
    invalid, duplicate, and orphaned thumbnail files.

    Process:
        1. Scans cache directory for .jpg files
        2. Parses filenames (format: camera_id_timestamp.jpg)
        3. Validates camera IDs against current Blink system
        4. Keeps only newest thumbnail per camera
        5. Removes invalid/old files in background

    File Format:
        - Valid: "camera123_1642459551.jpg"
        - Invalid: "invalid_format.jpg" (removed)

    Thread Safety:
        - Uses thread-safe cache operations
        - File removal happens in background thread
        - Race conditions prevented with proper error handling

    Error Handling:
        - Invalid filenames: Logged and removed
        - Missing cameras: Files removed if system available
        - File system errors: Logged, operation continues
    """
    from pathlib import Path
    from typing import cast

    import blinkapp
    from blinkapp.models.ids import CameraId
    from blinkapp.services.blink_service import blink

    # Ensure thumbnail cache is initialized
    thumbnail_cache = ensure_thumbnail_cache_initialized()

    assert blinkapp.THUMBNAIL_CACHE_DIR is not None
    cache_dir = Path(cast(str, blinkapp.THUMBNAIL_CACHE_DIR))
    if not cache_dir.exists():
        logger.warning(f"Thumbnail cache directory does not exist: {cache_dir}")
        return

    try:
        # Get valid camera IDs from current system
        valid_camera_ids = set()
        if blink and blink.available:
            for sync_name, sync in blink.sync.items():
                for cam_name, cam in sync.cameras.items():
                    valid_camera_ids.add(cam.camera_id)

        # Group thumbnails by camera ID
        camera_thumbnails: dict[str, list[tuple[int, str, Path]]] = {}
        files_to_remove = []

        for file_path in cache_dir.glob("*.jpg"):
            filename = file_path.name
            # Parse filename format: camera_id_timestamp.jpg
            parts = filename.replace(".jpg", "").split("_")
            if len(parts) >= 2:
                try:
                    camera_id = "_".join(
                        parts[:-1]
                    )  # Handle camera IDs with underscores
                    timestamp = int(parts[-1])

                    # Check if camera ID is valid for current system
                    if valid_camera_ids and camera_id not in valid_camera_ids:
                        logger.debug(
                            f"Removing thumbnail for invalid camera {camera_id}"
                        )
                        files_to_remove.append(file_path)
                        continue

                    # Group by camera ID
                    if camera_id not in camera_thumbnails:
                        camera_thumbnails[camera_id] = []
                    camera_thumbnails[camera_id].append(
                        (timestamp, filename, file_path)
                    )

                except (ValueError, IndexError) as e:
                    logger.warning(
                        f"Could not parse thumbnail filename {filename}: {e}"
                    )
                    files_to_remove.append(file_path)

        # Keep only the newest thumbnail per camera
        for camera_id, thumbnails in camera_thumbnails.items():
            # Sort by timestamp (newest first)
            thumbnails.sort(key=lambda x: x[0], reverse=True)

            # Keep the newest, mark others for removal
            if thumbnails:
                newest_ts, newest_filename, newest_path = thumbnails[0]
                thumbnail_cache[CameraId(camera_id)] = {
                    "timestamp": newest_ts,
                    "filename": newest_filename,
                }
                logger.debug(
                    f"Loaded cached thumbnail for camera {camera_id} with timestamp {newest_ts}"
                )

                # Mark older thumbnails for removal
                for old_ts, old_filename, old_path in thumbnails[1:]:
                    logger.debug(
                        f"Removing old thumbnail {old_filename} for camera {camera_id}"
                    )
                    files_to_remove.append(old_path)

        # Remove invalid/old files in background
        def remove_files(files_list: list[Path]) -> None:
            for file_path in files_list:
                try:
                    file_path.unlink()
                    logger.debug(f"Removed invalid thumbnail: {file_path.name}")
                except (OSError, PermissionError) as e:
                    logger.warning(f"Could not remove thumbnail file {file_path}: {e}")

        if files_to_remove:
            from blinkapp.services.connection_service import ensure_executor_initialized

            ensure_executor_initialized().submit(remove_files, files_to_remove)

    except Exception as e:
        logger.error(f"Error scanning thumbnail cache: {e}")
