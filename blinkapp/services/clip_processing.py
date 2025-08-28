"""Clip processing service for Blink Camera Flask application.

This module handles background processing of clips including thumbnail generation,
cloud clip processing, and local clip processing.
"""

from __future__ import annotations

__all__ = [
    "process_cloud_clip_background",
    "process_local_clip_background",
    "download_and_cache_cloud_thumbnail",
]

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from blinkapp.models.ids import ClipId

from blinkapp.config import Config
from blinkapp.models.cache import ClipCacheEntry
from blinkapp.services.cache_service import ensure_clips_cache_initialized

logger = logging.getLogger(__name__)


def _get_blink_instance():
    """Get Blink instance - extracted for testability."""
    from blinkapp.services.blink_service import blink

    return blink


def _get_clips_cache_dir():
    """Get clips cache directory - extracted for testability."""
    from blinkapp import CLIPS_CACHE_DIR

    return CLIPS_CACHE_DIR


def process_cloud_clip_background(clip_id: ClipId) -> None:
    """Process a cloud clip in the background.

    Downloads the clip and generates a thumbnail for faster access.
    This runs in a background thread to avoid blocking the main request.
    """
    try:
        blink_instance = _get_blink_instance()
        if not blink_instance or not blink_instance.available:
            logger.warning(f"Blink not available for processing clip {clip_id}")
            return

        clips_cache_dir = Path(_get_clips_cache_dir())
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

        # Download thumbnail from Blink API for cloud clips
        thumbnail_path = clips_cache_dir / f"{clip_id}.jpg"
        if not thumbnail_path.exists():
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
                            logger.info(
                                f"Downloaded thumbnail for cloud clip {clip_id}"
                            )
                        else:
                            logger.warning(
                                f"Failed to download thumbnail for cloud clip {clip_id}"
                            )
                    else:
                        logger.warning(f"Empty thumbnail URL for cloud clip {clip_id}")
                else:
                    logger.warning(f"No thumbnail URL found for cloud clip {clip_id}")
            except Exception as e:
                logger.error(
                    f"Error downloading thumbnail for cloud clip {clip_id}: {e}"
                )

        # Update cache entry
        try:
            clips_cache = ensure_clips_cache_initialized()
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

    Retrieves the clip from local storage and generates a thumbnail.
    This runs in a background thread to avoid blocking the main request.
    """
    try:
        blink_instance = _get_blink_instance()
        if not blink_instance or not blink_instance.available:
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

        clips_cache_dir = Path(_get_clips_cache_dir())
        clips_cache_dir.mkdir(parents=True, exist_ok=True)

        # Download clip if not cached
        clip_filename = f"{clip_id}.mp4"
        clip_path = clips_cache_dir / clip_filename

        if not clip_path.exists():
            try:
                # Get local clip content
                # TODO: Implement proper local clip access using blinkpy LocalStorageMediaItem API
                # The get_local_clip_content method doesn't exist in blinkpy
                # Need to use request_local_storage_clip and download_video methods instead
                logger.warning(
                    f"Local clip processing not fully implemented for {clip_id}"
                )
                logger.warning(
                    "Need to implement proper blinkpy LocalStorageMediaItem API usage"
                )
                return

            except Exception as e:
                logger.error(f"Error caching local clip {clip_id}: {e}")
                return

        # Generate thumbnail
        thumbnail_path = clips_cache_dir / f"{clip_id}.jpg"
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
    """
    try:
        clips_cache_dir = Path(_get_clips_cache_dir())
        clips_cache_dir.mkdir(parents=True, exist_ok=True)

        thumbnail_path = clips_cache_dir / f"{clip_id}.jpg"

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
