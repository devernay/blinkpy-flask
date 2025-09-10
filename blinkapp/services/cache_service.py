"""Cache service for Blink Camera Flask application.

This module handles all cache-related business logic including
cache initialization, management, and cleanup operations.
"""

from __future__ import annotations

__all__ = [
    "initialize_caches",
    "ensure_clips_cache_initialized",
    "ensure_camera_thumbnail_cache_initialized",
    "ensure_cache_paths_initialized",
    "get_cache_stats",
    "load_camera_thumbnail_cache",
    "initialize_cache_paths",
    "clear_all_caches",
    "clear_camera_thumbnail_cache_files",
    "clear_clips_cache_files",
    "load_clips_cache",
    "camera_thumbnail_cache",
    "clips_cache",
    "ensure_cache_directory",
    "validate_cache_directory",
    "cleanup_global_caches",
]

import logging
from typing import TYPE_CHECKING

from blinkpy.camera import BlinkCamera

if TYPE_CHECKING:
    from blinkapp.models.cache import CameraThumbnailCache, ClipsCache

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

    if (
        not blinkapp.CACHE_DIR
        or not blinkapp.CREDENTIALS_FILE
        or not blinkapp.THUMBNAIL_CACHE_DIR
        or not blinkapp.CLIPS_CACHE_DIR
        or not blinkapp.SETTINGS_FILE
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

    import blinkapp
    from blinkapp.models.ids import CameraId
    from blinkapp.services.blink_service import ensure_blink_initialized

    blink = ensure_blink_initialized()

    # Ensure thumbnail cache is initialized
    camera_thumbnail_cache = ensure_camera_thumbnail_cache_initialized()

    assert blinkapp.THUMBNAIL_CACHE_DIR is not None
    cache_dir = Path(blinkapp.THUMBNAIL_CACHE_DIR)
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
def initialize_cache_paths() -> None:
    """Initialize cache directory paths from Flask config or defaults."""
    from pathlib import Path

    import blinkapp
    from blinkapp.config import Config

    try:
        from flask import current_app

        cache_dir_config: str = current_app.config.get(
            "CACHE_DIR", Config.DEFAULT_CACHE_DIR
        )
    except RuntimeError:
        cache_dir_config = Config.DEFAULT_CACHE_DIR

    cache_dir = Path(cache_dir_config)
    cache_dir.mkdir(parents=True, exist_ok=True)

    blinkapp.CACHE_DIR = str(cache_dir)
    blinkapp.CREDENTIALS_FILE = str(cache_dir / Config.CREDENTIALS_FILENAME)
    blinkapp.THUMBNAIL_CACHE_DIR = str(cache_dir / Config.THUMBNAILS_SUBDIR)
    blinkapp.CLIPS_CACHE_DIR = str(cache_dir / Config.CLIPS_SUBDIR)
    blinkapp.HLS_OUTPUT_DIR = str(cache_dir / "hls")
    blinkapp.SETTINGS_FILE = str(cache_dir / Config.SETTINGS_FILENAME)

    Path(blinkapp.THUMBNAIL_CACHE_DIR).mkdir(parents=True, exist_ok=True)
    Path(blinkapp.CLIPS_CACHE_DIR).mkdir(parents=True, exist_ok=True)
    Path(blinkapp.HLS_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


def clear_all_caches() -> dict[str, str]:
    """Clear all caches except credentials including memory and file caches.

    Returns:
        dict[str, str]: Status messages for each cache clearing operation.
    """
    import os
    import shutil

    import blinkapp
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
    if blinkapp.THUMBNAIL_CACHE_DIR:
        executor_instance.submit(
            clear_file_cache, blinkapp.THUMBNAIL_CACHE_DIR, "thumbnail"
        )
    if blinkapp.CLIPS_CACHE_DIR:
        executor_instance.submit(clear_file_cache, blinkapp.CLIPS_CACHE_DIR, "clips")

    return {"status": "success", "message": "All caches cleared successfully"}


def load_clips_cache() -> None:
    """Load clips cache directory and populate memory cache."""
    from pathlib import Path

    import blinkapp
    from blinkapp.models.ids import ClipId

    if not blinkapp.CLIPS_CACHE_DIR:
        return

    cache_dir = Path(blinkapp.CLIPS_CACHE_DIR)
    if not cache_dir.exists():
        return

    clips_cache_instance = ensure_clips_cache_initialized()

    for video_file in cache_dir.glob("*.mp4"):
        filename = video_file.name
        try:
            parts = filename.replace(".mp4", "").split("_", 1)
            if len(parts) >= 2:
                clip_id = ClipId(parts[0])
                from blinkapp.models.cache import ClipCacheData

                clip_data: ClipCacheData = {
                    "id": str(clip_id),
                    "camera_name": parts[1] if len(parts) > 1 else "unknown",
                    "system_name": "cached",
                    "time": "",
                    "event_type": "cached",
                    "thumbnail": "",
                    "media_url": str(video_file),
                }
                clips_cache_instance.add_clip(clip_id, clip_data)
        except Exception as e:
            logger.debug(f"Error processing cached clip {filename}: {e}")


def clear_camera_thumbnail_cache_files() -> None:
    """Clear thumbnail cache files only."""
    import shutil
    from pathlib import Path

    import blinkapp

    if blinkapp.THUMBNAIL_CACHE_DIR:
        cache_path = Path(blinkapp.THUMBNAIL_CACHE_DIR)
        if cache_path.exists():
            shutil.rmtree(cache_path)
            cache_path.mkdir(parents=True, exist_ok=True)


def clear_clips_cache_files() -> None:
    """Clear clips cache files only."""
    import shutil
    from pathlib import Path

    import blinkapp

    if blinkapp.CLIPS_CACHE_DIR:
        cache_path = Path(blinkapp.CLIPS_CACHE_DIR)
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
