"""Clip service for Blink Camera Flask application.

This module handles all clip-related business logic including
cloud and local clip processing, downloading, and thumbnail generation.
"""

from __future__ import annotations

__all__ = [
    "process_cloud_clips",
    "process_local_clips",
    "download_cloud_clip",
    "download_local_clip",
    "process_cloud_clip_background",
]

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from blinkapp.models.ids import ClipId

from blinkapp.models.ids import ClipId
from blinkapp.services.cache_service import ensure_clips_cache_initialized
from blinkapp.utils.validators import format_clips_by_day
from config import Config

logger = logging.getLogger(__name__)


def process_cloud_clips(
    videos_metadata: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Process cloud storage clips into day-grouped format.

    Takes raw video metadata from the Blink API and organizes it into
    day-based groups for easier browsing in the web interface. This function
    handles thumbnail caching, timestamp parsing, and creates a standardized
    format for both cloud and local clips.

    The function prioritizes local thumbnails over Blink's CDN thumbnails
    when available, as local thumbnails are faster to load and don't count
    against API rate limits.

    Args:
        videos_metadata: Raw video metadata from Blink API, each containing:
            - id: Unique clip identifier
            - created_at: ISO timestamp string
            - device_name: Camera name
            - thumbnail: CDN thumbnail URL
            - media: Video file URL

    Returns:
        List of day groups with clips sorted by date, each containing:
        - date: Human-readable date string
        - clips: List of clip objects with standardized fields

    Example:
        >>> metadata = [{"id": "123", "created_at": "2023-01-01T12:00:00Z", ...}]
        >>> result = process_cloud_clips(metadata)
        >>> result[0]["date"]
        "January 01, 2023"
    """
    clips_by_day: dict[str, dict[str, object]] = {}

    for video in videos_metadata:
        try:
            # Parse ISO timestamp from Blink API (handles Z timezone suffix)
            created_at = datetime.fromisoformat(
                str(video["created_at"]).replace("Z", "+00:00")
            )
            day_key = created_at.strftime("%Y-%m-%d")

            # Create day group if it doesn't exist
            if day_key not in clips_by_day:
                clips_by_day[day_key] = {
                    "date": created_at.strftime("%B %d, %Y"),
                    "clips": [],
                }

            clip_id = ClipId(str(video.get("id")))
            thumbnail_url = video.get("thumbnail")

            # Check if we have a cached thumbnail for cloud clips
            # This avoids using Blink's CDN thumbnail if we have a local one
            # which is faster and doesn't count against API limits
            clips_cache_instance = ensure_clips_cache_initialized()
            cached_clip = clips_cache_instance.get(clip_id)
            if cached_clip is not None:
                cached_thumbnail = cached_clip.get("thumbnail")
                if cached_thumbnail and cached_thumbnail.exists():
                    # Use our local thumbnail endpoint instead of Blink's CDN
                    thumbnail_url = f"/api/clip/{clip_id}/thumbnail"

            # Build standardized clip object for UI consumption
            clip_data = {
                "id": str(clip_id),
                "camera_name": video.get("device_name", "Unknown"),
                "system_name": Config.DEFAULT_SYSTEM_NAME,
                "time": created_at.astimezone().strftime("%I:%M %p"),
                "event_type": "Motion",  # Cloud clips are always motion events
                "thumbnail": thumbnail_url,
                "media_url": video.get("media"),
            }
            clips_list = clips_by_day[day_key]["clips"]
            if isinstance(clips_list, list):
                clips_list.append(clip_data)
        except Exception as e:
            # Skip malformed video entries but continue processing others
            # This ensures one bad clip doesn't break the entire list
            logger.warning(f"Skipping invalid video metadata: {e}")
            continue

    return format_clips_by_day(clips_by_day)


def process_local_clips() -> list[dict[str, Any]]:
    """Process local clips from USB storage.

    Returns:
        List of processed local clips
    """
    from blinkapp import process_local_clips as _process_local_clips

    return _process_local_clips()


def download_cloud_clip(clip_id: ClipId):
    """Download a cloud clip.

    Args:
        clip_id: The clip ID to download

    Returns:
        Flask response with clip file or error
    """
    from blinkapp import download_cloud_clip as _download_cloud_clip

    return _download_cloud_clip(clip_id)


def download_local_clip(clip_id: ClipId):
    """Download a local clip.

    Args:
        clip_id: The clip ID to download

    Returns:
        Flask response with clip file or error
    """
    from blinkapp import download_local_clip as _download_local_clip

    return _download_local_clip(clip_id)


def process_cloud_clip_background(clip_id: ClipId) -> None:
    """Process cloud clip in background.

    Args:
        clip_id: The clip ID to process
    """
    from blinkapp import process_cloud_clip_background as _process_cloud_clip_background

    _process_cloud_clip_background(clip_id)


def process_local_clip_background(clip_id: ClipId) -> None:
    """Process local clip in background.

    Args:
        clip_id: The clip ID to process
    """
    from blinkapp import process_local_clip_background as _process_local_clip_background

    _process_local_clip_background(clip_id)
