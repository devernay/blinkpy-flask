"""Thumbnail service for Blink Camera Flask application.

This module handles all thumbnail-related business logic including
thumbnail generation, caching, and processing operations.
"""

from __future__ import annotations

__all__ = [
    "generate_local_clip_thumbnail",
    "notify_thumbnail_ready",
    "get_thumbnail_cache_stats",
]

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from blinkapp.models.ids import ClipId

from blinkapp.config import Config

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
    import subprocess

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
    """Thumbnail ready notification (no longer needed with polling approach)."""
    from blinkapp import logger

    logger.debug(f"Thumbnail ready for clip: {clip_id}")


def get_thumbnail_cache_stats() -> dict[str, Any]:
    """Get thumbnail cache statistics.

    Returns:
        Dictionary with cache statistics
    """
    from blinkapp.services.cache_service import ensure_thumbnail_cache_initialized

    try:
        thumbnail_cache = ensure_thumbnail_cache_initialized()
        return {
            "size": len(thumbnail_cache),
            "max_size": getattr(thumbnail_cache, "max_size", "unknown"),
            "hit_rate": getattr(thumbnail_cache, "hit_rate", "unknown"),
        }
    except Exception as e:
        logger.error(f"Failed to get thumbnail cache stats: {e}")
        return {"error": str(e)}
