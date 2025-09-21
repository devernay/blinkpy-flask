"""Thumbnail service for Blink Camera Flask application.

This module handles all thumbnail-related business logic including
thumbnail generation, caching, and processing operations.
"""

from __future__ import annotations

__all__ = [
    "generate_local_clip_thumbnail",
    "get_camera_thumbnail",
    "notify_thumbnail_ready",
    "refresh_camera_thumbnail",
]

import logging
import re
import subprocess
from pathlib import Path

from flask import Response

from blinkapp.config import Config
from blinkapp.models.ids import CameraId, ClipId
from blinkapp.models.types import JsonDict
from blinkapp.services.cache_service import get_thumbnail_cache_dir

logger = logging.getLogger(__name__)


def generate_local_clip_thumbnail(
    clip_id: ClipId, clip_path: Path, thumbnail_path: Path
) -> Path | None:
    """Generate thumbnail image from local video clip using FFmpeg.

    This function only works with local clips and extracts the middle frame
    for better representation. Cloud clip thumbnails should be fetched via
    the Blink API using download_and_cache_cloud_thumbnail.

    Args:
        clip_id: Clip identifier (must be a local clip)
        clip_path: Path to source video file (must exist)
        thumbnail_path: Path where thumbnail should be saved

    Returns:
        Path to generated thumbnail file, or None if generation failed

    Raises:
        ValueError: If clip_id is not a local clip

    Process:
        1. Verify this is a local clip (raise exception if not)
        2. Check if thumbnail already exists (skip if found)
        3. Use FFmpeg to extract middle frame as JPEG
        4. Save to specified thumbnail path

    FFmpeg Command:
        ffmpeg -i video.mp4 -ss {duration/2} -vframes 1 -f image2 thumb.jpg

    Error Handling:
        - Non-local clip: Raises ValueError
        - Missing FFmpeg: Returns None, logs error
        - Corrupted video: Returns None, logs error
        - Timeout: Returns None after configured timeout
    """
    # Verify this is a local clip - raise exception if not
    if not clip_id.is_local():
        raise ValueError(
            f"generate_local_clip_thumbnail called on cloud clip {clip_id}. Use download_and_cache_cloud_thumbnail instead."
        )

    # Check if thumbnail already exists
    if thumbnail_path.exists():
        logger.debug(f"Thumbnail already exists for {clip_id}")
        return thumbnail_path

    # Verify source video exists
    if not clip_path.exists():
        logger.error(f"Source video file not found: {clip_path}")
        return None

    try:
        # Get video duration first
        duration_cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(clip_path),
        ]

        duration_result = subprocess.run(
            duration_cmd,
            capture_output=True,
            text=True,
            timeout=Config.FFPROBE_TIMEOUT,
            check=True,
        )

        duration = float(duration_result.stdout.strip())
        middle_time = duration / 2  # Extract middle frame

        # Extract middle frame using FFmpeg
        cmd = [
            "ffmpeg",
            "-i",
            str(clip_path),
            "-ss",
            str(middle_time),
            "-vframes",
            "1",
            "-f",
            "image2",
            "-y",  # Overwrite output file
            str(thumbnail_path),
        ]

        subprocess.run(
            cmd, capture_output=True, check=True, timeout=Config.FFMPEG_TIMEOUT
        )

        logger.info(f"Generated thumbnail for local clip {clip_id}")
        return thumbnail_path

    except subprocess.TimeoutExpired:
        logger.error(f"Thumbnail generation timed out for {clip_id}")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(
            f"FFmpeg error generating thumbnail for {clip_id}: {e.stderr.decode() if e.stderr else str(e)}"
        )
        return None
    except Exception as e:
        logger.error(f"Error generating thumbnail for {clip_id}: {e}")
        return None


def notify_thumbnail_ready(clip_id: ClipId) -> None:
    """Thumbnail ready notification (no longer needed with polling approach).

    Args:
        clip_id: "ClipId" object representing the clip with ready thumbnail.
    """
    from blinkapp import logger

    logger.debug(f"Thumbnail ready for clip: {clip_id}")


def get_camera_thumbnail(
    camera_id: CameraId, timestamp: bool = False
) -> Response | JsonDict | tuple[JsonDict, int]:
    """Get camera thumbnail with intelligent caching based on timestamp.

    Args:
        camera_id: Camera identifier
        timestamp: If True, return timestamp info instead of image

    Returns:
        Response with thumbnail image or timestamp data
    """
    from ..services.cache_service import ensure_camera_thumbnail_cache_initialized
    from ..services.camera_service import find_camera_by_id

    try:
        camera = find_camera_by_id(camera_id)
        if not camera:
            return {"success": False, "error": "Camera not found"}, 404

        # Get cached thumbnail info
        cache = ensure_camera_thumbnail_cache_initialized()
        cached_entry = cache.get(camera_id)

        # Extract timestamp from camera thumbnail URL
        current_ts = None
        if camera is not None and camera.thumbnail:
            # Extract ts parameter from URL like ?ts=1742459551&ext=
            ts_match = re.search(r"[?&]ts=(\d+)", camera.thumbnail)
            if ts_match:
                current_ts = int(ts_match.group(1))

        if timestamp:
            # Return timestamp information directly
            if cached_entry:
                return {
                    "success": True,
                    "timestamp": cached_entry["timestamp"],
                }
            if current_ts:
                return {"success": True, "timestamp": current_ts}
            return {"success": False, "error": "No timestamp available"}, 404

        # Check if we need to update cached thumbnail
        should_update = not cached_entry or (
            current_ts and current_ts > cached_entry["timestamp"]
        )

        if should_update and current_ts and camera.thumbnail:
            # Download and cache new thumbnail
            _download_camera_thumbnail(camera_id, camera.thumbnail, current_ts)
            cached_entry = cache.get(camera_id)

        if cached_entry:
            # Serve cached thumbnail
            thumbnail_cache_dir = get_thumbnail_cache_dir()
            thumbnail_path = thumbnail_cache_dir / cached_entry["filename"]
            if thumbnail_path.exists():
                with open(thumbnail_path, "rb") as f:
                    return Response(f.read(), mimetype="image/jpeg")

        return {"success": False, "error": "Thumbnail not available"}, 404

    except Exception as e:
        from blinkapp import logger

        logger.error(f"Error getting camera thumbnail for {camera_id}: {e}")
        return {"success": False, "error": "Internal server error"}, 500


def refresh_camera_thumbnail(camera_id: CameraId) -> JsonDict | tuple[JsonDict, int]:
    """Force refresh of camera thumbnail by clearing cache and re-downloading.

    Args:
        camera_id: Camera identifier

    Returns:
        Success response or error
    """
    from ..services.cache_service import ensure_camera_thumbnail_cache_initialized
    from ..services.camera_service import find_camera_by_id

    try:
        camera = find_camera_by_id(camera_id)
        if not camera:
            return {"success": False, "error": "Camera not found"}, 404

        # Clear cached entry
        cache = ensure_camera_thumbnail_cache_initialized()
        if camera_id in cache:
            old_entry = cache[camera_id]
            thumbnail_cache_dir = get_thumbnail_cache_dir()
            old_path = thumbnail_cache_dir / old_entry["filename"]
            if old_path.exists():
                old_path.unlink()
            del cache[camera_id]

        # Extract current timestamp and download new thumbnail
        if camera is not None and camera.thumbnail:
            ts_match = re.search(r"[?&]ts=(\d+)", camera.thumbnail)
            if ts_match:
                current_ts = int(ts_match.group(1))
                _download_camera_thumbnail(camera_id, camera.thumbnail, current_ts)
                return {
                    "success": True,
                    "data": {"message": "Thumbnail refresh initiated"},
                }

        return {"success": False, "error": "No thumbnail URL available"}, 404

    except Exception as e:
        from blinkapp import logger

        logger.error(f"Error refreshing camera thumbnail for {camera_id}: {e}")
        return {"success": False, "error": "Internal server error"}, 500


def _download_camera_thumbnail(
    camera_id: CameraId, thumbnail_url: str, timestamp: int
) -> None:
    """Download and cache camera thumbnail.

    Args:
        camera_id: Camera identifier
        thumbnail_url: URL to download thumbnail from
        timestamp: Timestamp for cache entry
    """
    from ..models.cache import CameraThumbnailCacheEntry
    from ..services.cache_service import ensure_camera_thumbnail_cache_initialized

    try:
        thumbnail_cache_dir = get_thumbnail_cache_dir()
        if not thumbnail_cache_dir:
            return

        # Check for race condition - another thread may have updated the cache
        cache = ensure_camera_thumbnail_cache_initialized()
        current_cached = cache.get(camera_id)
        if current_cached and timestamp <= current_cached["timestamp"]:
            # Another thread already updated with newer or same timestamp
            logger.debug(
                f"Skipping thumbnail update for camera {camera_id} due to race condition"
            )
            return

        cache_dir = get_thumbnail_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Clean up old thumbnail file if it exists
        if current_cached and current_cached["filename"]:
            old_file_path = cache_dir / current_cached["filename"]
            try:
                if old_file_path.exists():
                    old_file_path.unlink()
            except OSError as e:
                logger.warning(
                    f"Failed to remove old thumbnail file {old_file_path}: {e}"
                )

        # Generate filename: camera_id_timestamp.jpg
        filename = f"{camera_id}_{timestamp}.jpg"
        file_path = cache_dir / filename

        # Download thumbnail using BlinkConnection for proper authentication
        from blinkapp.services.blink_service import ensure_blink_connection_initialized

        blink_connection = ensure_blink_connection_initialized()

        async def download_thumbnail_with_auth() -> bytes | None:
            """Download thumbnail using authenticated Blink connection.

            Returns:
                Thumbnail image data as bytes, or None if download fails.

            Raises:
                Exception: If Blink is not authenticated or camera not found.
            """
            from blinkapp.services.auth_service import is_blink_authenticated

            blink = blink_connection.blink
            if not blink or not is_blink_authenticated(blink):
                raise Exception("Blink not authenticated")

            # Find the camera object
            camera = None
            for sync in blink.sync.values():
                for cam in sync.cameras.values():
                    if str(cam.camera_id) == str(camera_id):
                        camera = cam
                        break
                if camera:
                    break

            if not camera:
                raise Exception(f"Camera {camera_id} not found")

            # Use blinkpy's authenticated thumbnail download
            response = await camera.get_thumbnail(thumbnail_url)
            if response:
                return await response.read()
            return None

        # Execute the download through BlinkConnection
        response_data = blink_connection.execute(download_thumbnail_with_auth())

        if not response_data:
            raise Exception("Failed to download thumbnail")

        # Save to cache using safe download
        from blinkapp.utils.safe_download import safe_download_bytes

        if not safe_download_bytes(file_path, response_data):
            raise Exception("Failed to save thumbnail")

        # Update cache entry
        cache[camera_id] = CameraThumbnailCacheEntry(
            timestamp=timestamp, filename=filename
        )

        logger.info(f"Downloaded and cached thumbnail for camera {camera_id}")

    except Exception as e:
        logger.error(f"Error downloading thumbnail for camera {camera_id}: {e}")
