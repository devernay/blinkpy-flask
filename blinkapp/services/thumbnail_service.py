"""Thumbnail service for Blink Camera Flask application.

This module handles all thumbnail-related business logic including
thumbnail generation, caching, and processing operations.
"""

from __future__ import annotations

__all__ = [
    "generate_clip_thumbnail",
    "notify_thumbnail_ready",
    "get_thumbnail_cache_stats",
]

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from blinkapp.models.ids import ClipId

from config import Config

logger = logging.getLogger(__name__)


def generate_clip_thumbnail(
    video_path: Path, filename: str, middle_frame: bool = False
) -> Path | None:
    """Generate thumbnail image from video clip using FFmpeg.

    Extracts a single frame from video file and saves as JPEG thumbnail.
    Uses different extraction strategies based on clip type:
    - Cloud clips: First frame (fast, consistent)
    - Local clips: Middle frame (better representation)

    Args:
        video_path: Path to source video file (must exist)
        filename: Original video filename for thumbnail naming
        middle_frame: If True, extract middle frame; if False, first frame

    Returns:
        Path to generated thumbnail file, or None if generation failed

    Process:
        1. Check if thumbnail already exists (skip if found)
        2. For middle frame: Use ffprobe to get duration, calculate midpoint
        3. For first frame: Extract frame at 1 second mark
        4. Use FFmpeg to extract frame as JPEG
        5. Save with same base name as video but .jpg extension

    FFmpeg Commands:
        - First frame: ffmpeg -i video.mp4 -ss 00:00:01 -vframes 1 -f image2 thumb.jpg
        - Middle frame: ffmpeg -i video.mp4 -ss {duration/2} -vframes 1 -f image2 thumb.jpg

    Error Handling:
        - Missing FFmpeg: Returns None, logs error
        - Corrupted video: Returns None, logs error
        - Timeout: Returns None after configured timeout
        - File system errors: Returns None, logs error

    Performance:
        - Respects configured timeouts (FFmpeg: 30s, FFprobe: 10s)
        - Skips generation if thumbnail exists
        - Runs in background thread to avoid blocking
    """
    from blinkapp import CLIPS_CACHE_DIR, logger

    thumbnail_filename = filename.replace(".mp4", ".jpg")
    assert CLIPS_CACHE_DIR is not None
    thumbnail_path = Path(cast(str, CLIPS_CACHE_DIR)) / thumbnail_filename

    if thumbnail_path.exists():
        return thumbnail_path

    import subprocess

    try:
        # Use ffmpeg to extract frame (middle frame for local clips, first frame for cloud)
        if middle_frame:
            # Get video duration and extract middle frame
            duration_cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(video_path),
            ]
            duration_result = subprocess.run(
                duration_cmd,
                capture_output=True,
                text=True,
                timeout=Config.FFPROBE_TIMEOUT,
                check=True,
            )
            duration = float(duration_result.stdout.strip()) / 2  # Middle timestamp
            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-ss",
                str(duration),
                "-vframes",
                "1",
                "-f",
                "image2",
                str(thumbnail_path),
            ]
        else:
            # Extract first frame
            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-ss",
                "00:00:01",
                "-vframes",
                "1",
                "-f",
                "image2",
                str(thumbnail_path),
            ]

        subprocess.run(
            cmd, capture_output=True, check=True, timeout=Config.FFMPEG_TIMEOUT
        )
        return thumbnail_path
    except subprocess.TimeoutExpired:
        logger.error(f"Thumbnail generation timed out for {video_path}")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(
            f"FFmpeg error generating thumbnail: {e.stderr.decode() if e.stderr else str(e)}"
        )
        return None
    except Exception as e:
        logger.error(f"Error generating thumbnail: {e}")
        return None


def notify_thumbnail_ready(clip_id: ClipId) -> None:
    """Notify that thumbnail is ready for a clip.

    Args:
        clip_id: The clip ID
    """
    from blinkapp import notify_thumbnail_ready as _notify_thumbnail_ready

    _notify_thumbnail_ready(clip_id)


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
