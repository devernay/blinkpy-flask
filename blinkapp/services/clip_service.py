"""Clip service for Blink Camera Flask application.

This module handles high-level clip processing and organization.
Download and background processing functionality has been moved to
dedicated modules for better separation of concerns.
"""

from __future__ import annotations

__all__ = [
    "process_cloud_clips",
    "process_local_clips",
]

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from blinkapp.utils.formatters import format_clips_by_day

if TYPE_CHECKING:
    from blinkapp.models.ids import ClipId

from blinkapp.config import Config
from blinkapp.models.cache import ClipCacheEntry
from blinkapp.models.ids import ClipId
from blinkapp.services.cache_service import ensure_clips_cache_initialized

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
            cloud_thumbnail_url_raw = video.get("thumbnail")
            cloud_thumbnail_url = (
                str(cloud_thumbnail_url_raw)
                if cloud_thumbnail_url_raw is not None
                else None
            )

            # Always use our thumbnail endpoint for cloud clips
            # This will handle redirect to Blink CDN or serve cached thumbnails
            thumbnail_url = f"/api/clip/{clip_id}/thumbnail"

            # Store cloud thumbnail URL in cache for the endpoint to use
            clips_cache_instance = ensure_clips_cache_initialized()
            cached_clip = clips_cache_instance.get(clip_id)
            if cached_clip is not None:
                # Update existing cache entry with cloud thumbnail URL
                cached_clip["cloud_thumbnail_url"] = cloud_thumbnail_url
                clips_cache_instance[clip_id] = cached_clip
            else:
                # Create new cache entry with cloud thumbnail URL
                if cloud_thumbnail_url:
                    media_url_obj = video.get("media")
                    assert media_url_obj is None or isinstance(media_url_obj, str), (
                        f"Expected media to be str, got {type(media_url_obj)}"
                    )
                    media_url = str(media_url_obj) if media_url_obj is not None else ""

                    cache_entry: ClipCacheEntry = {
                        "cloud_thumbnail_url": str(cloud_thumbnail_url),
                        "media_url": media_url,
                        "created_at": created_at.isoformat(),
                    }
                    clips_cache_instance[clip_id] = cache_entry

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

    # Convert clips_by_day dict to list format and format properly
    clips_list = []
    for day_data in clips_by_day.values():
        if isinstance(day_data, dict) and "clips" in day_data:
            clips = day_data["clips"]
            if isinstance(clips, list):
                clips_list.extend(clips)

    return format_clips_by_day(clips_list)


def process_local_clips(
    blink_instance=None, blink_connection_instance=None
) -> list[dict[str, object]]:
    """Process local storage clips into day-grouped format.

    Retrieves clips from USB storage connected to Blink sync modules.
    Local clips require the sync module to have local storage enabled
    and the manifest to be ready. Each clip gets a composite ID that
    includes the sync module name for proper identification.

    Args:
        blink_instance: Optional blink instance for testing
        blink_connection_instance: Optional blink connection for testing

    Returns:
        List of day groups with clips sorted by date, or empty list if
        no local storage is available or manifest isn't ready
    """
    # Use injected dependencies or defaults
    if blink_instance is None or blink_connection_instance is None:
        from blinkapp.services.blink_service import blink, blink_connection

        if blink_instance is None:
            blink_instance = blink
        if blink_connection_instance is None:
            blink_connection_instance = blink_connection

    clips_by_day: dict[str, dict[str, object]] = {}

    assert blink_instance is not None
    for sync_name, sync_module in blink_instance.sync.items():
        try:
            # Refresh sync module to update local storage manifest
            # This ensures we have the latest clip information
            if blink_connection_instance:
                try:
                    refresh_result = sync_module.refresh()
                    blink_connection_instance.execute(refresh_result)
                except Exception as refresh_error:
                    logger.warning(
                        f"Failed to refresh sync module {sync_name}: {refresh_error}"
                    )
                    # Continue processing even if refresh fails

            # Get clips from local storage manifest if ready
            if sync_module.local_storage and sync_module.local_storage_manifest_ready:
                manifest = sync_module._local_storage["manifest"]
                for item in manifest:
                    try:
                        created_at = item.created_at
                        day_key = created_at.strftime("%Y-%m-%d")

                        # Create day group if it doesn't exist
                        if day_key not in clips_by_day:
                            clips_by_day[day_key] = {
                                "date": created_at.strftime("%B %d, %Y"),
                                "clips": [],
                            }

                        # Create composite clip ID for local clips (sync_name:item_id)
                        clip_id = ClipId.from_local(sync_name, item.id)
                        logger.debug(
                            f"Created local clip ID: {clip_id} from sync: "
                            f"{sync_name}, item: {item.id}"
                        )

                        # Check for existing thumbnail only
                        # (no auto-generation for local)
                        thumbnail_url = None
                        clips_cache_instance = ensure_clips_cache_initialized()
                        cached_clip = clips_cache_instance.get(clip_id)
                        if cached_clip is not None:
                            cached_thumbnail = cached_clip.get("thumbnail")
                            if cached_thumbnail and cached_thumbnail.exists():
                                thumbnail_url = f"/api/clip/{clip_id}/thumbnail"

                        # Build standardized clip object for UI
                        clip_data = {
                            "id": str(clip_id),
                            "camera_name": item.name,
                            "system_name": sync_name,
                            "time": created_at.astimezone().strftime("%I:%M %p"),
                            "event_type": "Motion",
                            "thumbnail": thumbnail_url,
                            "media_url": item.url(
                                sync_module._local_storage["last_manifest_id"]
                            ),
                        }
                        clips_list = clips_by_day[day_key]["clips"]
                        if isinstance(clips_list, list):
                            clips_list.append(clip_data)
                    except Exception as e:
                        logger.warning(f"Skipping invalid local clip metadata: {e}")
                        continue
        except Exception as e:
            logger.warning(f"Could not get local storage manifest for {sync_name}: {e}")
            continue

    # Convert clips_by_day dict to list format and format properly
    clips_list = []
    for day_data in clips_by_day.values():
        if isinstance(day_data, dict) and "clips" in day_data:
            clips = day_data["clips"]
            if isinstance(clips, list):
                clips_list.extend(clips)

    return format_clips_by_day(clips_list)
