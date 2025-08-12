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
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from blinkapp.app_types import ResponseReturnValue
    from blinkapp.models.ids import ClipId

import requests
from flask import jsonify, send_file

from blinkapp.models.ids import ClipId
from blinkapp.models.responses import create_api_response
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


def process_local_clips() -> list[dict[str, object]]:
    """Process local storage clips into day-grouped format.

    Retrieves clips from USB storage connected to Blink sync modules.
    Local clips require the sync module to have local storage enabled
    and the manifest to be ready. Each clip gets a composite ID that
    includes the sync module name for proper identification.

    Returns:
        List of day groups with clips sorted by date, or empty list if
        no local storage is available or manifest isn't ready
    """
    from blinkapp import blink, blink_connection

    clips_by_day: dict[str, dict[str, object]] = {}

    assert blink is not None
    for sync_name, sync_module in blink.sync.items():
        try:
            # Refresh sync module to update local storage manifest
            # This ensures we have the latest clip information
            blink_connection.execute(sync_module.refresh())

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

    return format_clips_by_day(clips_by_day)


def download_cloud_clip(clip_id: ClipId) -> ResponseReturnValue:
    """Download cloud storage clip."""
    from blinkapp import (
        CLIPS_CACHE_DIR,
        _download_clip_common,
        blink,
        blink_connection,
        ensure_executor_initialized,
        http_session,
    )

    assert blink is not None
    # Check if already cached
    clips_cache_instance = ensure_clips_cache_initialized()
    cached_clip = clips_cache_instance.get(clip_id)
    if cached_clip is not None:
        try:
            # Quick existence check - if it fails, we'll re-download
            if cached_clip["filepath"].exists():
                response = send_file(str(cached_clip["filepath"]), as_attachment=True)
                return response, 200
        except (OSError, AttributeError):
            # File doesn't exist or path is invalid, continue to download
            pass

    # Get clip metadata
    videos_metadata = blink_connection.execute(
        blink.get_videos_metadata(stop=Config.MAX_VIDEOS_METADATA)
    )
    clip_info = next(
        (v for v in videos_metadata if str(v.get("id")) == str(clip_id)), None
    )
    if clip_info is None:
        api_response, status_code = create_api_response(
            success=False, error=Config.ErrorMessages.CLIP_NOT_FOUND, status_code=404
        )
        return jsonify(api_response), status_code

    # Generate filename
    created_at = datetime.fromisoformat(clip_info["created_at"].replace("Z", "+00:00"))
    camera_name = clip_info.get("device_name", "unknown")
    iso_date = created_at.strftime("%Y-%m-%dT%H-%M-%S")
    filename = f"{clip_id}_{camera_name}_{iso_date}.mp4"
    assert CLIPS_CACHE_DIR is not None
    filepath = Path(cast(str, CLIPS_CACHE_DIR)) / filename

    # Download if not cached
    if not filepath.exists():
        media_url = clip_info.get("media")
        if media_url is None:
            api_response, status_code = create_api_response(
                success=False,
                error=Config.ErrorMessages.CLIP_NO_MEDIA_URL,
                status_code=404,
            )
            return jsonify(api_response), status_code

        # Download in executor to avoid blocking
        def download_file() -> bool:
            try:
                response = http_session.get(media_url, timeout=Config.HTTP_TIMEOUT)
                if response.status_code == Config.HTTP_STATUS_OK:
                    filepath.write_bytes(response.content)
                    return True
                else:
                    logger.error(
                        f"HTTP {response.status_code} downloading clip {clip_id}"
                    )
                    return False
            except (requests.RequestException, OSError) as e:
                logger.error(f"Error downloading clip {clip_id}: {e}")
                return False

        # Execute download synchronously since we need the file immediately
        future = ensure_executor_initialized().submit(download_file)
        try:
            success = future.result(timeout=Config.DOWNLOAD_TIMEOUT)
            if not success:
                api_response, status_code = create_api_response(
                    success=False,
                    error=Config.ErrorMessages.CLIP_DOWNLOAD_FAILED,
                    status_code=500,
                )
                return jsonify(api_response), status_code
        except Exception as e:
            logger.error(f"Download timeout or error for clip {clip_id}: {e}")
            api_response, status_code = create_api_response(
                success=False,
                error=Config.ErrorMessages.CLIP_DOWNLOAD_TIMEOUT,
                status_code=500,
            )
            return jsonify(api_response), status_code

    return _download_clip_common(clip_id, filepath, filename, middle_frame=False)


def download_local_clip(
    clip_id: ClipId, sync_name: str, item_id: int
) -> ResponseReturnValue:
    """Download local storage clip using blinkpy methods."""
    from blinkapp import (
        CLIPS_CACHE_DIR,
        _download_clip_common,
        blink,
        blink_connection,
        logger,
    )

    assert blink is not None
    # Check if already cached
    clips_cache_instance = ensure_clips_cache_initialized()
    cached_clip = clips_cache_instance.get(clip_id)
    if cached_clip is not None:
        try:
            # Quick existence check - if it fails, we'll re-download
            if cached_clip["filepath"].exists():
                response = send_file(str(cached_clip["filepath"]), as_attachment=True)
                return response, 200
        except (OSError, AttributeError):
            # File doesn't exist or path is invalid, continue to download
            pass

    # Find sync module and clip item
    sync_module = blink.sync.get(sync_name)
    if sync_module is None:
        api_response, status_code = create_api_response(
            success=False,
            error=Config.ErrorMessages.SYNC_MODULE_NOT_FOUND,
            status_code=404,
        )
        return jsonify(api_response), status_code

    if not sync_module.local_storage or not sync_module.local_storage_manifest_ready:
        api_response, status_code = create_api_response(
            success=False,
            error=Config.ErrorMessages.LOCAL_STORAGE_NOT_AVAILABLE,
            status_code=404,
        )
        return jsonify(api_response), status_code

    manifest = sync_module._local_storage["manifest"]
    item = next((i for i in manifest if i.id == item_id), None)
    if item is None:
        api_response, status_code = create_api_response(
            success=False,
            error=Config.ErrorMessages.LOCAL_CLIP_NOT_FOUND,
            status_code=404,
        )
        return jsonify(api_response), status_code

    # Generate filename
    iso_date = item.created_at.strftime("%Y-%m-%dT%H-%M-%S")
    filename = f"{clip_id}_{item.name}_{iso_date}.mp4"
    assert CLIPS_CACHE_DIR is not None
    filepath = Path(cast(str, CLIPS_CACHE_DIR)) / filename

    # Download if not cached
    if not filepath.exists():
        try:
            blink_connection.execute(item.prepare_download(blink))
            success = blink_connection.execute(
                item.download_video(blink, str(filepath))
            )
            if success is not True:
                api_response, status_code = create_api_response(
                    success=False,
                    error=Config.ErrorMessages.CLIP_DOWNLOAD_FAILED,
                    status_code=500,
                )
                return jsonify(api_response), status_code
        except Exception as e:
            logger.error(f"Error downloading local clip: {e}")
            api_response, status_code = create_api_response(
                success=False,
                error=Config.ErrorMessages.CLIP_DOWNLOAD_FAILED,
                status_code=500,
            )
            return jsonify(api_response), status_code

    return _download_clip_common(clip_id, filepath, filename, middle_frame=True)


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
