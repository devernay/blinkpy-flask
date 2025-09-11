"""Clip service for Blink Camera Flask application.

This module handles high-level clip processing and organization.
Download and background processing functionality has been moved to
dedicated modules for better separation of concerns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blinkapp.models.types import JsonDict

__all__ = [
    "process_cloud_clips",
    "process_local_clips",
    "download_clip",
]

import logging
from datetime import datetime
from typing import TYPE_CHECKING, NotRequired, TypedDict

from blinkapp.config import Config
from blinkapp.models.cache import ClipCacheEntry
from blinkapp.models.ids import ClipId
from blinkapp.models.types import ClipApiData, ClipDayGroup, JsonDict
from blinkapp.services.cache_service import ensure_clips_cache_initialized
from blinkapp.utils.formatters import format_clips_by_day

if TYPE_CHECKING:
    from blinkpy.blinkpy import Blink
    from flask import Response

    from blinkapp.services.blink_connection import BlinkConnection


class VideoMetadata(TypedDict):
    """Type definition for video metadata from blinkpy."""

    id: str | int
    created_at: str
    device_name: str
    deleted: bool
    media: str
    # Additional optional fields that may be present
    size: NotRequired[int | None]
    thumbnail: NotRequired[str | None]


logger = logging.getLogger(__name__)


def download_clip(clip_id: ClipId) -> Response | tuple[JsonDict, int]:
    """Download clip file by ID.

    This function serves as a bridge between the route handlers and the
    actual download implementation in clip_download service.

    Args:
        clip_id: ClipId object representing the clip to download.

    Returns:
        Response | tuple[JsonDict, int]: File response or error response with status code.
    """
    from ..services.cache_service import ensure_clips_cache_initialized
    from ..services.clip_download import download_clip_common

    # Check if clip exists in cache
    clips_cache = ensure_clips_cache_initialized()
    if clip_id in clips_cache:
        clip_entry = clips_cache[clip_id]
        if "filepath" not in clip_entry:
            return {"success": False, "error": "Clip file not cached"}, 404
        return download_clip_common(clip_entry["filepath"], clip_id)
    else:
        # Return 404 for missing clips
        return {"success": False, "error": "Clip not found"}, 404


def process_cloud_clips(
    videos_metadata: list[dict[str, str | int | bool | None]],
) -> list[ClipDayGroup]:
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
    clips_by_day: dict[str, dict[str, str | list[ClipApiData]]] = {}

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
            # Create new cache entry with cloud thumbnail URL
            elif cloud_thumbnail_url:
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
            clip_data: JsonDict = {
                "id": str(clip_id),
                "camera_name": video.get("device_name", "Unknown"),
                "system_name": Config.DEFAULT_SYSTEM_NAME,
                "time": created_at.astimezone().strftime("%I:%M %p"),
                "event_type": "Motion",  # Cloud clips are always motion events
                "thumbnail": thumbnail_url,
                "media_url": video.get("media"),
            }
            clips_list_raw = clips_by_day[day_key]["clips"]
            if isinstance(clips_list_raw, list):
                # Type cast: clip_data contains all required ClipApiData fields plus extras
                clips_list_raw.append(clip_data)  # pyright: ignore[reportArgumentType]
        except Exception as e:
            # Skip malformed video entries but continue processing others
            # This ensures one bad clip doesn't break the entire list
            logger.warning(f"Skipping invalid video metadata: {e}")
            continue

    # Convert clips_by_day dict to list format and format properly
    clips_list: list[ClipApiData] = []
    for day_data in clips_by_day.values():
        if isinstance(day_data, dict) and "clips" in day_data:
            clips = day_data["clips"]
            if isinstance(clips, list):
                clips_list.extend(clips)

    return format_clips_by_day(clips_list)


def process_local_clips(
    blink_instance: Blink | None = None,
    blink_connection_instance: BlinkConnection | None = None,
) -> list[ClipDayGroup]:
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
        from blinkapp.services.blink_service import (
            ensure_blink_connection_initialized,
            ensure_blink_initialized,
        )

        if blink_instance is None:
            blink_instance = ensure_blink_initialized()
        if blink_connection_instance is None:
            blink_connection_instance = ensure_blink_connection_initialized()

    clips_by_day: dict[str, dict[str, str | list[ClipApiData]]] = {}

    assert blink_instance is not None
    logger.debug(f"Processing local clips from {len(blink_instance.sync)} sync modules")

    for sync_name, sync_module in blink_instance.sync.items():
        logger.debug(
            f"Checking sync module {sync_name}: local_storage={sync_module.local_storage}"
        )
        try:
            # Update local storage manifest specifically for local clips
            # This ensures we have the latest clip information from USB storage
            if blink_connection_instance and sync_module.local_storage:
                logger.debug(f"Updating local storage manifest for {sync_name}")
                try:
                    result = blink_connection_instance.execute(
                        sync_module.update_local_storage_manifest()
                    )
                    logger.debug(f"Manifest update result for {sync_name}: {result}")
                    
                    # Then check for new videos to populate last_records (blinkpy pattern)
                    blink_connection_instance.execute(sync_module.check_new_videos())
                    logger.debug(f"Checked new videos for {sync_name}")
                except Exception as manifest_error:
                    logger.warning(
                        f"Failed to update local storage manifest for {sync_name}: {manifest_error}"
                    )
                    # Continue processing even if manifest update fails

            # Get clips from local storage manifest if ready
            if sync_module.local_storage and sync_module.local_storage_manifest_ready:
                logger.debug(
                    f"Processing manifest for {sync_name} with {len(sync_module._local_storage['manifest'])} clips"
                )
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
                            f"Created local clip ID: {clip_id} from sync: {sync_name}, item: {item.id}"
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
                        clip_data: JsonDict = {
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
                        clips_list_raw = clips_by_day[day_key]["clips"]
                        if isinstance(clips_list_raw, list):
                            # Type cast: clip_data contains all required ClipApiData fields plus extras
                            clips_list_raw.append(clip_data)  # pyright: ignore[reportArgumentType]
                    except Exception as e:
                        logger.warning(f"Skipping invalid local clip metadata: {e}")
                        continue
        except Exception as e:
            logger.warning(f"Could not get local storage manifest for {sync_name}: {e}")
            continue

    # Convert clips_by_day dict to list format and format properly
    clips_list: list[ClipApiData] = []
    for day_data in clips_by_day.values():
        if isinstance(day_data, dict) and "clips" in day_data:
            clips = day_data["clips"]
            if isinstance(clips, list):
                clips_list.extend(clips)

    return format_clips_by_day(clips_list)


async def delete_clip(clip_id: ClipId) -> tuple[JsonDict, int]:
    """Delete a clip from both Blink system and local storage.

    Args:
        clip_id: The clip ID to delete

    Returns:
        Tuple of (response_dict, status_code)
    """
    from blinkapp.models.responses import create_api_response
    from blinkapp.services.blink_service import ensure_blink_connection_initialized
    from blinkapp.services.cache_service import ensure_clips_cache_initialized

    try:
        # Use shared BlinkConnection to access Blink system
        blink_conn = ensure_blink_connection_initialized()

        # Find the video object by iterating through videos metadata
        videos_found = False
        video_deleted = False

        async def find_and_delete_video() -> bool:
            """Find and delete video from Blink system.

            Returns:
                bool: True if video was found and deleted, False otherwise.
            """
            nonlocal videos_found, video_deleted
            blink = blink_conn.blink
            if blink is None:
                return False

            # Get videos metadata to find the clip
            videos_metadata = await blink.get_videos_metadata()

            for video_data in videos_metadata:
                if str(video_data.get("id")) == str(clip_id):
                    videos_found = True
                    # Find the sync module that contains this video
                    if blink.sync is not None:
                        for sync_name, sync_module in blink.sync.items():
                            # Note: BlinkSyncModule doesn't have a 'videos' attribute
                            # This functionality may need to be implemented differently
                            # For now, just mark as found but not deleted
                            logger.warning(
                                f"Video deletion not implemented for sync module {sync_name}"
                            )
                            return False
                    break
            return videos_found

        # Execute deletion through BlinkConnection thread
        blink_conn.execute(find_and_delete_video())

        # Remove from local cache regardless of Blink deletion result
        clips_cache = ensure_clips_cache_initialized()

        if clip_id in clips_cache:
            del clips_cache[clip_id]
            logger.info(f"Removed clip {clip_id} from local cache")

        # Prepare response based on results
        if videos_found and video_deleted:
            message = f"Clip {clip_id} deleted from Blink system and local cache"
        elif videos_found and not video_deleted:
            message = f"Clip {clip_id} found but failed to delete from Blink system, removed from local cache"
        else:
            message = (
                f"Clip {clip_id} not found in Blink system, removed from local cache"
            )

        response, status_code = create_api_response(
            success=True, data={"message": message, "deleted_from_blink": video_deleted}
        )
        return response, status_code

    except Exception as e:
        logger.error(f"Failed to delete clip {clip_id}: {e}")
        response, status_code = create_api_response(
            success=False, error=f"Failed to delete clip: {str(e)}", status_code=500
        )
        return response, status_code
