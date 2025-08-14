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
    "download_and_cache_cloud_thumbnail",
    "download_clip_common",
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
            cloud_thumbnail_url = video.get(
                "thumbnail"
            )  # Store original cloud thumbnail URL

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
                    clips_cache_instance[clip_id] = {
                        "cloud_thumbnail_url": cloud_thumbnail_url,
                        "media_url": video.get("media"),
                        "created_at": created_at.isoformat(),
                    }

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
    from blinkapp.services.blink_service import blink, blink_connection

    clips_by_day: dict[str, dict[str, object]] = {}

    assert blink is not None
    for sync_name, sync_module in blink.sync.items():
        try:
            # Refresh sync module to update local storage manifest
            # This ensures we have the latest clip information
            if blink_connection:
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
    )
    from blinkapp.services.blink_service import blink, blink_connection
    from blinkapp.services.connection_service import (
        ensure_executor_initialized,
        ensure_http_session_initialized,
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
    if blink_connection:
        videos_metadata = blink_connection.execute(
            blink.get_videos_metadata(stop=Config.MAX_VIDEOS_METADATA)
        )
    else:
        videos_metadata = []
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
                response = ensure_http_session_initialized().get(
                    media_url, timeout=Config.HTTP_TIMEOUT
                )
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

    return download_clip_common(clip_id, filepath, filename, middle_frame=False)


def download_local_clip(
    clip_id: ClipId, sync_name: str, item_id: int
) -> ResponseReturnValue:
    """Download local storage clip using blinkpy methods."""
    from blinkapp import (
        CLIPS_CACHE_DIR,
        logger,
    )
    from blinkapp.services.blink_service import blink, blink_connection

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
            if blink_connection:
                blink_connection.execute(item.prepare_download(blink))
                success = blink_connection.execute(
                    item.download_video(blink, str(filepath))
                )
            else:
                success = False
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

    return download_clip_common(clip_id, filepath, filename, middle_frame=True)


def process_cloud_clip_background(clip_id: ClipId) -> None:
    """Process cloud clip in background (download and generate thumbnail).

    Downloads clip from Blink cloud storage and generates thumbnail for web interface.
    Runs in background thread to avoid blocking API responses.

    Args:
        clip_id: Unique identifier for the cloud clip
    """
    from blinkapp import (
        CLIPS_CACHE_DIR,
        logger,
    )
    from blinkapp.services.blink_service import blink, blink_connection
    from blinkapp.services.connection_service import (
        ensure_executor_initialized,
        ensure_http_session_initialized,
    )
    from blinkapp.services.thumbnail_service import generate_clip_thumbnail

    # Ensure clips cache is initialized
    clips_cache_instance = ensure_clips_cache_initialized()

    def process() -> None:
        assert blink is not None
        try:
            # Check if already cached
            cached_clip = clips_cache_instance.get(clip_id)
            if cached_clip is not None and cached_clip["filepath"].exists():
                return

            # Get clip metadata
            videos_metadata = blink_connection.execute(
                blink.get_videos_metadata(stop=Config.MAX_VIDEOS_METADATA)
            )
            clip_info = next(
                (v for v in videos_metadata if str(v.get("id")) == str(clip_id)), None
            )
            if not clip_info:
                return

            # Generate filename and download
            created_at = datetime.fromisoformat(
                clip_info["created_at"].replace("Z", "+00:00")
            )
            camera_name = clip_info.get("device_name", "unknown")
            iso_date = created_at.strftime("%Y-%m-%dT%H-%M-%S")
            filename = f"{clip_id}_{camera_name}_{iso_date}.mp4"
            assert CLIPS_CACHE_DIR is not None
            filepath = Path(cast(str, CLIPS_CACHE_DIR)) / filename

            if not filepath.exists():
                media_url = clip_info.get("media")
                if not media_url:
                    return
                try:
                    response = ensure_http_session_initialized().get(
                        media_url, timeout=Config.HTTP_TIMEOUT
                    )
                    if response.status_code == Config.HTTP_STATUS_OK:
                        filepath.write_bytes(response.content)
                    else:
                        logger.error(
                            f"HTTP {response.status_code} downloading clip for processing"
                        )
                        return
                except (requests.RequestException, OSError) as e:
                    logger.error(f"Error downloading clip for processing: {e}")
                    return

            # Cache the clip and generate thumbnail
            clips_cache_instance[clip_id] = {"filepath": filepath, "thumbnail": None}
            thumbnail_path = generate_clip_thumbnail(
                filepath, filename, middle_frame=False
            )
            if thumbnail_path is not None:
                cached_clip = clips_cache_instance.get(clip_id)
                if cached_clip is not None:
                    updated_clip = cached_clip.copy()
                    updated_clip["thumbnail"] = thumbnail_path
                    clips_cache_instance[clip_id] = updated_clip
        except Exception as e:
            logger.error(f"Error processing cloud clip {clip_id}: {e}")

    ensure_executor_initialized().submit(process)


def download_and_cache_cloud_thumbnail(
    clip_id: ClipId, thumbnail_url: str
) -> Path | None:
    """Download and cache cloud thumbnail image.

    Args:
        clip_id: The clip ID
        thumbnail_url: URL of the thumbnail to download

    Returns:
        Path to cached thumbnail file, or None if download failed
    """
    from blinkapp import logger
    from blinkapp.services.cache_service import ensure_clips_cache_initialized
    from blinkapp.services.connection_service import ensure_http_session_initialized
    from config import Config

    try:
        # Get cache directory
        cache_dir = Path(Config.DEFAULT_CACHE_DIR)
        thumbnail_filename = f"{clip_id}_thumb.jpg"
        thumbnail_path = cache_dir / "thumbnails" / thumbnail_filename
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)

        # Download thumbnail
        session = ensure_http_session_initialized()
        response = session.get(thumbnail_url, timeout=10)
        response.raise_for_status()

        # Save thumbnail
        with open(thumbnail_path, "wb") as f:
            f.write(response.content)

        # Update cache with thumbnail path
        clips_cache_instance = ensure_clips_cache_initialized()
        cached_clip = clips_cache_instance.get(clip_id)
        if cached_clip is not None:
            cached_clip["thumbnail"] = thumbnail_path
            clips_cache_instance[clip_id] = cached_clip

        logger.info(f"Downloaded and cached cloud thumbnail for clip {clip_id}")
        return thumbnail_path

    except Exception as e:
        logger.error(f"Failed to download cloud thumbnail for clip {clip_id}: {e}")
        return None


def process_local_clip_background(
    clip_id: ClipId, sync_name: str, item_id: int
) -> None:
    """Process local clip in background (download and generate thumbnail).

    Downloads clip from USB storage and generates thumbnail for web interface.
    Runs in background thread to avoid blocking API responses.

    Args:
        clip_id: Unique identifier for the clip
        sync_name: Name of the sync module containing the clip
        item_id: Local storage item ID
    """
    from blinkapp import (
        CLIPS_CACHE_DIR,
        logger,
    )
    from blinkapp.services.blink_service import blink, blink_connection
    from blinkapp.services.connection_service import ensure_executor_initialized
    from blinkapp.services.thumbnail_service import generate_clip_thumbnail

    # Ensure clips cache is initialized
    clips_cache_instance = ensure_clips_cache_initialized()

    def process() -> None:
        try:
            # Check if already cached
            cached_clip = clips_cache_instance.get(clip_id)
            if cached_clip is not None and cached_clip["filepath"].exists():
                return

            assert blink is not None
            # Find sync module and clip item
            sync_module = blink.sync.get(sync_name)
            if (
                sync_module is None
                or not sync_module.local_storage
                or not sync_module.local_storage_manifest_ready
            ):
                return

            manifest = sync_module._local_storage["manifest"]
            item = next((i for i in manifest if i.id == item_id), None)
            if not item:
                return

            # Generate filename and download
            iso_date = item.created_at.strftime("%Y-%m-%dT%H-%M-%S")
            filename = f"{clip_id}_{item.name}_{iso_date}.mp4"
            assert CLIPS_CACHE_DIR is not None
            filepath = Path(cast(str, CLIPS_CACHE_DIR)) / filename

            if not filepath.exists():
                blink_connection.execute(item.prepare_download(blink))
                success = blink_connection.execute(
                    item.download_video(blink, str(filepath))
                )
                if success is not True:
                    return

            # Cache the clip and generate thumbnail
            clips_cache_instance[clip_id] = {"filepath": filepath, "thumbnail": None}
            thumbnail_path = generate_clip_thumbnail(
                filepath, filename, middle_frame=True
            )
            if thumbnail_path is not None:
                cached_clip = clips_cache_instance.get(clip_id)
                if cached_clip is not None:
                    updated_clip = cached_clip.copy()
                    updated_clip["thumbnail"] = thumbnail_path
                    clips_cache_instance[clip_id] = updated_clip
        except Exception as e:
            logger.error(f"Error processing local clip {clip_id}: {e}")

    ensure_executor_initialized().submit(process)


def download_clip_common(
    clip_id: ClipId, filepath: Path, filename: str, middle_frame: bool = False
) -> tuple[ResponseReturnValue, int]:
    """Common clip download logic after file is downloaded.

    Args:
        clip_id: Unique identifier for the clip
        filepath: Path to the downloaded clip file
        filename: Original filename for the clip
        middle_frame: Whether to extract middle frame as thumbnail

    Returns:
        Flask response with clip file or error message
    """
    from flask import send_file

    # Ensure clips cache is initialized
    clips_cache_instance = ensure_clips_cache_initialized()

    # Cache the clip first (without thumbnail)
    clips_cache_instance[clip_id] = {
        "filepath": filepath,
        "thumbnail": None,
    }

    # Generate thumbnail in background
    def generate_thumbnail_bg() -> None:
        from blinkapp.services.thumbnail_service import generate_clip_thumbnail

        thumbnail_path = generate_clip_thumbnail(
            filepath, filename, middle_frame=middle_frame
        )
        if thumbnail_path is not None:
            # Update cache with thumbnail atomically
            cached_clip = clips_cache_instance.get(clip_id)
            if cached_clip is not None:
                # Create new dict to avoid race conditions
                updated_clip = cached_clip.copy()
                updated_clip["thumbnail"] = thumbnail_path
                clips_cache_instance[clip_id] = updated_clip
            # Notify clients that thumbnail is ready
            from blinkapp.services.thumbnail_service import notify_thumbnail_ready

            notify_thumbnail_ready(clip_id)

    from blinkapp.services.connection_service import ensure_executor_initialized

    ensure_executor_initialized().submit(generate_thumbnail_bg)
    response = send_file(
        str(filepath), as_attachment=True, attachment_filename=filename
    )
    return response, 200
