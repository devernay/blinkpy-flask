"""Clip processing service for Blink Camera Flask application.

This module handles background processing of clips including thumbnail generation,
cloud clip processing, and local clip processing.
"""

from __future__ import annotations

__all__ = [
    "download_and_cache_cloud_thumbnail",
    "logger",
    "process_cloud_clip_background",
    "process_cloud_clip_thumbnail_only",
    "process_local_clip_background",
]

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from blinkapp.models.ids import ClipId

from blinkapp.config import Config
from blinkapp.models.cache import ClipCacheEntry
from blinkapp.services.cache_service import (
    ensure_clips_cache_initialized,
    get_clips_cache_dir,
    get_thumbnail_path,
)

logger = logging.getLogger(__name__)


def process_cloud_clip_background(clip_id: ClipId) -> None:
    """Process a cloud clip in the background.

    Checks if thumbnail is cached first. If not, downloads the clip and generates thumbnail.
    This runs in a background thread to avoid blocking the main request.

    Args:
        clip_id: ClipId object representing the cloud clip to process.
    """
    try:
        # Check if thumbnail is already cached
        from ..services.cache_service import get_thumbnail_path

        thumbnail_path = get_thumbnail_path(clip_id)

        if thumbnail_path.exists():
            logger.debug(f"Thumbnail already cached for clip {clip_id}")
            return

        from blinkapp.services.blink_service import ensure_blink_initialized

        try:
            blink_instance = ensure_blink_initialized()
        except RuntimeError:
            logger.warning(f"Blink not available for processing clip {clip_id}")
            return

        if not blink_instance.available:
            logger.warning(f"Blink not available for processing clip {clip_id}")
            return

        clips_cache_dir = get_clips_cache_dir()
        clips_cache_dir.mkdir(parents=True, exist_ok=True)

        # Download clip if not cached
        clip_filename = f"{clip_id}.mp4"
        clip_path = clips_cache_dir / clip_filename

        if not clip_path.exists():
            try:
                # Get clip URL from cache (set during clip listing)
                clips_cache = ensure_clips_cache_initialized()
                cached_clip = clips_cache.get(clip_id)

                if not cached_clip or not cached_clip.get("media_url"):
                    logger.error(f"No media URL found for cloud clip {clip_id}")
                    return

                clip_url = cached_clip.get("media_url")
                assert clip_url is not None  # We already checked above

                # Download clip content
                response = requests.get(clip_url, timeout=Config.HTTP_TIMEOUT)
                response.raise_for_status()

                # Save to cache
                with open(clip_path, "wb") as f:
                    f.write(response.content)

                logger.info(f"Downloaded cloud clip {clip_id} to {clip_path}")

            except Exception as e:
                logger.error(f"Error downloading cloud clip {clip_id}: {e}")
                return

        # Handle thumbnail using existing function
        process_cloud_clip_thumbnail_only(clip_id)

        # Update cache entry
        try:
            clips_cache = ensure_clips_cache_initialized()
            thumbnail_path = get_thumbnail_path(clip_id)
            clips_cache[clip_id] = ClipCacheEntry(
                filepath=clip_path,
                thumbnail=thumbnail_path if thumbnail_path.exists() else None,
            )
        except Exception as e:
            logger.error(f"Error updating cache for clip {clip_id}: {e}")

    except Exception as e:
        logger.error(f"Error in process_cloud_clip_background for {clip_id}: {e}")


def process_local_clip_background(
    clip_id: ClipId, sync_name: str, filename: str
) -> None:
    """Process a local clip in the background.

    Checks if thumbnail is cached first. If not, downloads the clip and generates thumbnail.
    This runs in a background thread to avoid blocking the main request.

    Args:
        clip_id: ClipId object representing the local clip to process.
        sync_name: Name of the sync module containing the clip.
        filename: Original filename of the clip.
    """
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        f"Starting local clip background processing for {clip_id} (sync: {sync_name}, file: {filename})"
    )

    try:
        # Check if thumbnail is already cached

        clips_cache_dir = get_clips_cache_dir()
        thumbnail_path = get_thumbnail_path(clip_id)

        if thumbnail_path.exists():
            logger.debug(f"Thumbnail already cached for local clip {clip_id}")
            return

        from blinkapp.services.blink_service import ensure_blink_initialized

        try:
            blink_instance = ensure_blink_initialized()
        except RuntimeError:
            logger.warning(f"Blink not available for processing local clip {clip_id}")
            return

        if not blink_instance.available:
            logger.warning(f"Blink not available for processing local clip {clip_id}")
            return

        # Get sync module
        sync_dict = blink_instance.sync
        if sync_name not in sync_dict:
            logger.error(f"Sync module '{sync_name}' not found for clip {clip_id}")
            return

        sync_module = sync_dict[sync_name]
        if not sync_module.local_storage:
            logger.warning(f"Local storage not available for clip {clip_id}")
            return

        clips_cache_dir.mkdir(parents=True, exist_ok=True)

        # Download clip if not cached
        clip_filename = f"{clip_id}.mp4"
        clip_path = clips_cache_dir / clip_filename

        if not clip_path.exists():
            try:
                # For local clips, check if video is already cached, then extract thumbnail
                # Parse local clip ID to get sync name and item ID
                sync_name, item_id = clip_id.get_local_parts()

                # First check if video is already cached
                clips_cache_dir = get_clips_cache_dir().resolve()
                video_pattern = f"{sync_name}~{item_id}.mp4"
                video_files = list(clips_cache_dir.glob(video_pattern))

                if video_files and video_files[0].exists():
                    # Video already cached, use it directly
                    video_path = video_files[0]
                    logger.info(
                        f"Using cached video for local clip {clip_id}: {video_path}"
                    )
                else:
                    # Video not cached, download it first
                    from blinkapp.services.clip_download import download_local_clip

                    download_result = download_local_clip(
                        clip_id, sync_name, str(item_id)
                    )

                    # Check if download was successful and we got a file response
                    if hasattr(download_result, "status_code"):
                        # It's an error response tuple
                        logger.warning(
                            f"Failed to download local clip {clip_id} for thumbnail generation"
                        )
                        return

                    # Find the newly cached video file
                    video_files = list(clips_cache_dir.glob(video_pattern))
                    if not video_files:
                        logger.warning(
                            f"Cached video file not found after download for local clip {clip_id}"
                        )
                        return

                    video_path = video_files[0]
                    if not video_path.exists():
                        logger.warning(
                            f"Cached video file does not exist: {video_path}"
                        )
                        return

                # Generate thumbnail from the cached video
                from blinkapp.services.thumbnail_service import (
                    generate_local_clip_thumbnail,
                )

                generate_local_clip_thumbnail(clip_id, video_path, thumbnail_path)
                logger.info(
                    f"Successfully generated thumbnail for local clip {clip_id} from cached video"
                )

            except Exception as e:
                logger.error(f"Error processing local clip {clip_id}: {e}")
                return

        # Generate thumbnail
        thumbnail_path = get_thumbnail_path(clip_id)
        if not thumbnail_path.exists():
            try:
                from blinkapp.services.thumbnail_service import (
                    generate_local_clip_thumbnail,
                )

                generate_local_clip_thumbnail(clip_id, clip_path, thumbnail_path)
                logger.info(f"Generated thumbnail for local clip {clip_id}")
            except Exception as e:
                logger.error(
                    f"Error generating thumbnail for local clip {clip_id}: {e}"
                )

        # Update cache entry
        try:
            clips_cache = ensure_clips_cache_initialized()
            clips_cache[clip_id] = ClipCacheEntry(
                filepath=clip_path,
                thumbnail=thumbnail_path if thumbnail_path.exists() else None,
            )
        except Exception as e:
            logger.error(f"Error updating cache for local clip {clip_id}: {e}")

    except Exception as e:
        logger.error(f"Error in process_local_clip_background for {clip_id}: {e}")


def download_and_cache_cloud_thumbnail(
    clip_id: ClipId,
    thumbnail_url: str,
) -> Path | None:
    """Download and cache a cloud clip thumbnail.

    Downloads the thumbnail from the provided URL and saves it to the cache.
    Returns the path to the cached thumbnail or None if download failed.

    Returns:
        Path | None: Path to cached thumbnail file if successful, None otherwise.

    Args:
        clip_id: Clip identifier (must be a cloud clip)
        thumbnail_url: URL to download thumbnail from

    Raises:
        ValueError: If clip_id is not a cloud clip
    """
    # Verify this is a cloud clip - raise exception if not
    if clip_id.is_local():
        raise ValueError(
            f"download_and_cache_cloud_thumbnail called on local clip {clip_id}. Use generate_local_clip_thumbnail instead."
        )

    # Validate thumbnail URL
    if not thumbnail_url:
        logger.error(f"No thumbnail URL provided for clip {clip_id}")
        return None

    try:
        clips_cache_dir = get_clips_cache_dir()
        clips_cache_dir.mkdir(parents=True, exist_ok=True)

        thumbnail_path = get_thumbnail_path(clip_id)

        # Download thumbnail if not cached
        if not thumbnail_path.exists():
            try:
                response = requests.get(thumbnail_url, timeout=Config.HTTP_TIMEOUT)
                response.raise_for_status()

                with open(thumbnail_path, "wb") as f:
                    f.write(response.content)

                logger.debug(f"Downloaded thumbnail for clip {clip_id}")

            except Exception as e:
                logger.error(f"Error downloading thumbnail for clip {clip_id}: {e}")
                return None

        return thumbnail_path

    except Exception as e:
        logger.error(f"Error in download_and_cache_cloud_thumbnail for {clip_id}: {e}")
        return None


def process_cloud_clip_thumbnail_only(clip_id: ClipId) -> None:
    """Process a cloud clip thumbnail only in the background.

    Checks if thumbnail is cached first. If not, downloads thumbnail from Blink server.
    This runs in a background thread to avoid blocking the main request.

    Args:
        clip_id: ClipId object representing the cloud clip to process thumbnail for.
    """
    try:
        # Check if thumbnail is already cached

        clips_cache_dir = get_clips_cache_dir()
        thumbnail_path = get_thumbnail_path(clip_id)

        if thumbnail_path.exists():
            logger.debug(f"Thumbnail already cached for clip {clip_id}")
            return

        clips_cache_dir.mkdir(parents=True, exist_ok=True)

        # Download thumbnail from Blink API for cloud clips
        try:
            # Get thumbnail URL from cache (set during clip listing)
            clips_cache = ensure_clips_cache_initialized()
            cached_clip = clips_cache.get(clip_id)

            if cached_clip and cached_clip.get("cloud_thumbnail_url"):
                thumbnail_url = cached_clip.get("cloud_thumbnail_url")
                if thumbnail_url:  # Additional check for type safety
                    downloaded_thumbnail = download_and_cache_cloud_thumbnail(
                        clip_id, thumbnail_url
                    )
                    if downloaded_thumbnail:
                        logger.info(f"Downloaded thumbnail for cloud clip {clip_id}")
                    else:
                        logger.warning(
                            f"Failed to download thumbnail for cloud clip {clip_id}"
                        )
                else:
                    logger.warning(f"Empty thumbnail URL for cloud clip {clip_id}")
            else:
                logger.debug(
                    f"No thumbnail URL found for cloud clip {clip_id} - skipping thumbnail download"
                )
        except Exception as e:
            logger.error(f"Error downloading thumbnail for cloud clip {clip_id}: {e}")

    except Exception as e:
        logger.error(f"Error processing cloud clip {clip_id}: {e}")
