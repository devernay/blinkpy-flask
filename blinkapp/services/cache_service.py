"""Cache service for Blink Camera Flask application.

This module handles all cache-related business logic including
cache initialization, management, and cleanup operations.
"""

from __future__ import annotations

import pathlib

__all__ = [
    "_get_cache_dir_config",
    "camera_thumbnail_cache",
    "cleanup_global_caches",
    "clear_all_caches",
    "clear_camera_thumbnail_cache_files",
    "clear_clips_cache_files",
    "clips_cache",
    "ensure_cache_directory",
    "ensure_cache_paths_initialized",
    "ensure_camera_thumbnail_cache_initialized",
    "ensure_clips_cache_initialized",
    "get_cache_stats",
    "get_clips_cache_dir",
    "get_thumbnail_cache_dir",
    "initialize_cache_paths",
    "initialize_caches",
    "load_camera_thumbnail_cache",
    "load_clips_cache",
    "validate_cache_directory",
]

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from blinkpy.camera import BlinkCamera

if TYPE_CHECKING:
    from blinkapp.models.cache import CameraThumbnailCache, ClipsCache

from blinkapp.models.ids import ClipId

logger = logging.getLogger(__name__)

# Global cache instances
clips_cache: ClipsCache | None = None
camera_thumbnail_cache: CameraThumbnailCache | None = None


def initialize_caches(config: dict[str, object]) -> None:
    """Initialize global cache instances with configuration.

    Args:
        config: Configuration dictionary with cache settings
    """
    global camera_thumbnail_cache, clips_cache
    from blinkapp.models.cache import CameraThumbnailCache, ClipsCache

    camera_thumbnail_cache = CameraThumbnailCache(
        maxsize=int(str(config.get("camera_thumbnail_cache_size") or "100"))
    )
    clips_cache = ClipsCache(maxsize=int(str(config.get("clips_cache_size") or "100")))

    logger.info("Cache instances initialized successfully")


def cleanup_global_caches() -> None:
    """Reset global cache instances to None for cleanup/testing."""
    global camera_thumbnail_cache, clips_cache
    camera_thumbnail_cache = None
    clips_cache = None


def ensure_clips_cache_initialized() -> ClipsCache:
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


def ensure_camera_thumbnail_cache_initialized() -> CameraThumbnailCache:
    """Ensure thumbnail cache is initialized.

    Returns:
        Initialized thumbnail cache instance

    Raises:
        RuntimeError: If camera_thumbnail_cache hasn't been initialized
    """
    if camera_thumbnail_cache is None:
        raise RuntimeError(
            "Thumbnail cache not initialized. Call initialize_caches() first."
        )
    return camera_thumbnail_cache


def ensure_cache_paths_initialized() -> None:
    """Ensure cache paths are initialized, raising an error if not.

    This function serves as a type guard for mypy to understand that
    the cache path variables are not None after this call.

    Raises:
        RuntimeError: If cache paths haven't been initialized
    """
    import blinkapp
    from blinkapp.services.auth_service import get_credentials_file_path
    from blinkapp.services.settings_service import get_settings_file_path

    if (
        not blinkapp._CACHE_DIR_PATH
        or not get_credentials_file_path()
        or not get_thumbnail_cache_dir()
        or not get_clips_cache_dir()
        or not get_settings_file_path()
    ):
        raise RuntimeError(
            "Cache paths not initialized. Call initialize_blink() first."
        )


def get_cache_stats() -> dict[str, dict[str, int | float]]:
    """Get statistics for all cache instances.

    Returns:
        Dictionary with statistics for each cache type
    """
    stats: dict[str, dict[str, int | float]] = {}

    camera_thumbnail_cache = ensure_camera_thumbnail_cache_initialized()
    if camera_thumbnail_cache:
        stats["camera_thumbnail_cache"] = camera_thumbnail_cache.get_stats()

    clips_cache = ensure_clips_cache_initialized()
    if clips_cache:
        stats["clips_cache"] = clips_cache.get_stats()

    return stats


def load_camera_thumbnail_cache() -> None:
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

    from blinkapp.models.ids import CameraId
    from blinkapp.services.blink_service import ensure_blink_initialized

    blink = ensure_blink_initialized()

    # Ensure thumbnail cache is initialized
    camera_thumbnail_cache = ensure_camera_thumbnail_cache_initialized()

    assert get_thumbnail_cache_dir() is not None
    cache_dir = Path(get_thumbnail_cache_dir())
    if not cache_dir.exists():
        logger.warning(f"Thumbnail cache directory does not exist: {cache_dir}")
        return

    try:
        # Get valid camera IDs from current system
        valid_camera_ids: set[str] = set()
        if blink and blink.available:
            # Type guard: blink is definitely Blink here, not None
            assert blink is not None
            for _, sync in blink.sync.items():
                for _, cam in sync.cameras.items():
                    # Use isinstance to properly narrow the type
                    if isinstance(cam, BlinkCamera) and cam.camera_id is not None:
                        valid_camera_ids.add(str(cam.camera_id))

        # Group thumbnails by camera ID
        camera_thumbnails: dict[str, list[tuple[int, str, Path]]] = {}
        files_to_remove: list[Path] = []

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
                newest_ts, newest_filename, _ = thumbnails[0]
                from blinkapp.models.cache import CameraThumbnailCacheEntry

                camera_thumbnail_cache[CameraId(camera_id)] = CameraThumbnailCacheEntry(
                    timestamp=newest_ts,
                    filename=newest_filename,
                )
                logger.debug(
                    f"Loaded cached thumbnail for camera {camera_id} with timestamp {newest_ts}"
                )

                # Mark older thumbnails for removal
                for _, old_filename, old_path in thumbnails[1:]:
                    logger.debug(
                        f"Removing old thumbnail {old_filename} for camera {camera_id}"
                    )
                    files_to_remove.append(old_path)

        # Remove invalid/old files in background
        def remove_files(files_list: list[Path]) -> None:
            """Remove files from filesystem with error handling.

            Args:
                files_list: List of Path objects representing files to remove.
            """
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


# Cache management functions merged from cache_management.py
def _get_cache_dir_config() -> str:
    """Get cache directory configuration from Flask app or defaults."""
    from blinkapp.config import Config

    try:
        from flask import current_app

        # NOTE: pyright doesn't recognize Flask's config.get() return type properly
        # This is a known Flask typing limitation, method exists and works at runtime
        cache_dir_raw: Any = current_app.config.get(  # pyright: ignore[reportUnknownMemberType]
            "CACHE_DIR", Config.DEFAULT_CACHE_DIR
        )
        cache_dir_config: str = (
            cache_dir_raw
            if isinstance(cache_dir_raw, str)
            else Config.DEFAULT_CACHE_DIR
        )
    except RuntimeError:
        cache_dir_config = Config.DEFAULT_CACHE_DIR

    return cache_dir_config


def initialize_cache_paths() -> None:
    """Initialize cache directory paths from Flask config or defaults."""
    import blinkapp
    from blinkapp.config import Config

    cache_dir_config = _get_cache_dir_config()
    cache_dir = pathlib.Path(cache_dir_config)
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Store resolved Path objects to avoid chdir issues
    blinkapp._CACHE_DIR_PATH = cache_dir.resolve()
    blinkapp._CLIPS_CACHE_DIR_PATH = (cache_dir / Config.CLIPS_SUBDIR).resolve()
    blinkapp._THUMBNAIL_CACHE_DIR_PATH = (
        cache_dir / Config.THUMBNAILS_SUBDIR
    ).resolve()
    blinkapp._HLS_OUTPUT_DIR_PATH = (cache_dir / "hls").resolve()
    blinkapp._CREDENTIALS_FILE_PATH = (
        cache_dir / Config.CREDENTIALS_FILENAME
    ).resolve()
    blinkapp._SETTINGS_FILE_PATH = (cache_dir / Config.SETTINGS_FILENAME).resolve()

    # Create directories
    blinkapp._THUMBNAIL_CACHE_DIR_PATH.mkdir(parents=True, exist_ok=True)
    blinkapp._CLIPS_CACHE_DIR_PATH.mkdir(parents=True, exist_ok=True)
    blinkapp._HLS_OUTPUT_DIR_PATH.mkdir(parents=True, exist_ok=True)


def clear_all_caches() -> dict[str, str]:
    """Clear all caches except credentials including memory and file caches.

    Returns:
        dict[str, str]: Status messages for each cache clearing operation.
    """
    import os
    import shutil

    from blinkapp.services.connection_service import ensure_executor_initialized

    camera_thumbnail_cache_instance = ensure_camera_thumbnail_cache_initialized()
    clips_cache_instance = ensure_clips_cache_initialized()

    camera_thumbnail_cache_instance.clear()
    clips_cache_instance.clear()

    def clear_file_cache(cache_dir: str, cache_name: str) -> None:
        """Clear all files from a cache directory.

        Args:
            cache_dir: Path to cache directory to clear
            cache_name: Human-readable name for logging
        """
        try:
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
                os.makedirs(cache_dir, exist_ok=True)
        except OSError as e:
            logger.warning(f"Could not clear {cache_name} directory: {e}")

    executor_instance = ensure_executor_initialized()
    if get_thumbnail_cache_dir():
        executor_instance.submit(
            clear_file_cache, str(get_thumbnail_cache_dir()), "thumbnail"
        )
    if get_clips_cache_dir():
        executor_instance.submit(clear_file_cache, str(get_clips_cache_dir()), "clips")

    return {"status": "success", "message": "All caches cleared successfully"}


def load_clips_cache() -> None:
    """Load clips cache directory and populate memory cache."""
    from pathlib import Path

    from blinkapp.models.ids import ClipId

    if not get_clips_cache_dir():
        return

    cache_dir = Path(get_clips_cache_dir())
    if not cache_dir.exists():
        return

    clips_cache_instance = ensure_clips_cache_initialized()

    for video_file in cache_dir.glob("*.mp4"):
        filename = video_file.name
        try:
            # Handle ClipId format: SyncName~ItemId.mp4
            clip_id_str = filename.replace(".mp4", "")
            clip_id = ClipId(clip_id_str)
            from blinkapp.models.cache import ClipCacheData

            # Check for existing thumbnail
            thumbnail_path = cache_dir / f"{clip_id_str}.jpg"

            # Use file modification time to preserve age information
            file_mtime = video_file.stat().st_mtime

            clip_data: ClipCacheData = {
                "id": str(clip_id),
                "camera_name": "cached",
                "system_name": "cached",
                "time": "",
                "event_type": "cached",
                "thumbnail": str(thumbnail_path) if thumbnail_path.exists() else "",
                "media_url": str(video_file),
            }

            # Create enhanced data with file timestamps
            from blinkapp.models.cache import ClipCacheEntry

            enhanced_data: ClipCacheEntry = {
                "clip_data": clip_data,
                "cached_at": file_mtime,  # Use file modification time
                "access_count": 0,
                "last_accessed": file_mtime,  # Use file modification time
            }
            clips_cache_instance[clip_id] = enhanced_data

            # Generate thumbnail if missing
            if not thumbnail_path.exists():
                try:
                    from blinkapp.services.clip_processing import (
                        process_local_clip_background,
                    )
                    from blinkapp.services.connection_service import (
                        ensure_executor_initialized,
                    )

                    # Extract sync_name and item_id for local clips
                    if clip_id.is_local():
                        sync_name, item_id = clip_id.get_local_parts()
                        executor = ensure_executor_initialized()
                        executor.submit(
                            process_local_clip_background,
                            clip_id,
                            sync_name,
                            str(item_id),
                        )
                        logger.debug(
                            f"Queued thumbnail generation for cached clip {clip_id}"
                        )
                except Exception as thumb_error:
                    logger.debug(
                        f"Failed to queue thumbnail generation for {clip_id}: {thumb_error}"
                    )

        except Exception as e:
            logger.debug(f"Error processing cached clip {filename}: {e}")


def clear_camera_thumbnail_cache_files() -> None:
    """Clear thumbnail cache files only."""
    import shutil
    from pathlib import Path

    if get_thumbnail_cache_dir():
        cache_path = Path(get_thumbnail_cache_dir())
        if cache_path.exists():
            shutil.rmtree(cache_path)
            cache_path.mkdir(parents=True, exist_ok=True)


def clear_clips_cache_files() -> None:
    """Clear clips cache files only."""
    import shutil
    from pathlib import Path

    if get_clips_cache_dir():
        cache_path = Path(get_clips_cache_dir())
        if cache_path.exists():
            shutil.rmtree(cache_path)
            cache_path.mkdir(parents=True, exist_ok=True)


def ensure_cache_directory(cache_dir: str) -> str:
    """Ensure cache directory exists and return its path.

    Args:
        cache_dir: Path to the cache directory to create.

    Returns:
        str: Absolute path to the created cache directory.
    """
    from pathlib import Path

    path = Path(cache_dir)
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def validate_cache_directory(cache_dir: str) -> bool:
    """Validate that cache directory is accessible and writable.

    Args:
        cache_dir: Path to the cache directory to validate.

    Returns:
        bool: True if directory exists and is writable, False otherwise.
    """
    from pathlib import Path

    try:
        path = Path(cache_dir)
        if not path.exists():
            return False

        # Test write access
        test_file = path / ".test_write"
        test_file.touch()
        test_file.unlink()
        return True
    except (OSError, PermissionError):
        return False


def get_thumbnail_path(clip_id: ClipId) -> Path:
    """Get the thumbnail file path for a clip.

    Args:
        clip_id: "ClipId" object representing the clip.

    Returns:
        Path: Path to the thumbnail file.
    """
    return get_clips_cache_dir() / f"{clip_id}.jpg"


def get_clips_cache_dir() -> Path:
    """Get the clips cache directory path.

    Returns:
        Path: Resolved path to the clips cache directory.
    """
    import blinkapp

    assert blinkapp._CLIPS_CACHE_DIR_PATH is not None, (
        "Cache paths not initialized. Call initialize_cache_paths() first."
    )
    return blinkapp._CLIPS_CACHE_DIR_PATH


def get_thumbnail_cache_dir() -> Path:
    """Get the thumbnail cache directory path.

    Returns:
        Path: Resolved path to the thumbnail cache directory.
    """
    import blinkapp

    assert blinkapp._THUMBNAIL_CACHE_DIR_PATH is not None, (
        "Cache paths not initialized. Call initialize_cache_paths() first."
    )
    return blinkapp._THUMBNAIL_CACHE_DIR_PATH


def get_cache_dir() -> Path:
    """Get the base cache directory path.

    Returns:
        Path: Resolved path to the base cache directory.
    """
    import blinkapp

    assert blinkapp._CACHE_DIR_PATH is not None, (
        "Cache paths not initialized. Call initialize_cache_paths() first."
    )
    return blinkapp._CACHE_DIR_PATH
