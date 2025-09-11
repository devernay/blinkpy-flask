"""Clip download service for Blink Camera Flask application.

This module handles downloading clips from both cloud and local storage,
including common download functionality and content retrieval.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import flask

from blinkapp.config import Config
from blinkapp.models.responses import create_api_response
from blinkapp.models.types import JsonDict

__all__ = [
    "download_cloud_clip",
    "download_local_clip",
    "download_clip_common",
    "_download_cloud_clip_core",
    "_download_cloud_clip_core_sync",
]

if TYPE_CHECKING:
    from blinkpy.blinkpy import Blink
    from flask import Response

    from blinkapp.models.ids import ClipId

logger = logging.getLogger(__name__)


def _download_cloud_clip_core_sync(
    clip_id: ClipId,
    blink_instance: Blink | None,
    clips_cache_dir: Path,
) -> tuple[Path | None, str | None]:
    """Synchronous wrapper for _download_cloud_clip_core for testing."""
    if blink_instance is None:
        return (
            None,
            f"Error downloading cloud clip {clip_id}: Blink instance not available",
        )

    import asyncio

    return asyncio.run(
        _download_cloud_clip_core(clip_id, blink_instance, clips_cache_dir)
    )


async def _download_cloud_clip_core(
    clip_id: ClipId,
    blink_instance: Blink,
    clips_cache_dir: Path,
) -> tuple[Path | None, str | None]:
    """Core cloud clip download logic - extracted for testability."""
    try:
        # Get all video metadata to find our specific clip
        videos_metadata = await blink_instance.get_videos_metadata(stop=50)

        # Find the clip by ID in the metadata
        clip_metadata = None
        for item in videos_metadata:
            if str(item.get("id")) == str(clip_id):
                clip_metadata = item
                break

        if not clip_metadata:
            return None, "Clip not found"

        # Get the media URL from the clip metadata
        media_url = clip_metadata.get("media")
        if not media_url:
            return None, f"Clip {clip_id} is not available for download"

        # Download clip content using blink's HTTP method
        response = await blink_instance.do_http_get(media_url)
        clip_content = await response.read()

        # Save to cache
        clip_filename = f"{clip_id}.mp4"
        clip_path = clips_cache_dir / clip_filename

        with open(clip_path, "wb") as f:
            f.write(clip_content)

        logger.info(f"Downloaded cloud clip {clip_id} to {clip_path}")
        return clip_path, None  # Return None for success, not empty string

    except Exception as e:
        error_msg = f"Error downloading cloud clip {clip_id}: {e}"
        logger.error(error_msg)
        return None, error_msg


def download_cloud_clip(clip_id: ClipId) -> Response | tuple[JsonDict, int]:
    """Download a cloud clip and return it as a file response.

    Args:
        clip_id: ClipId object representing the cloud clip to download.

    Returns:
        Response | tuple[JsonDict, int]: File response with video data or error response with status code.
    """
    try:
        from blinkapp.services.blink_service import get_blink_instance

        blink_instance = get_blink_instance()
        if not blink_instance or not blink_instance.available:
            return create_api_response(
                success=False,
                error=Config.ErrorMessages.BLINK_NOT_AVAILABLE,
                status_code=503,
            )

        from blinkapp import CLIPS_CACHE_DIR

        clips_cache_dir = Path(CLIPS_CACHE_DIR)
        clips_cache_dir.mkdir(parents=True, exist_ok=True)

        # Check if already cached
        clip_filename = f"{clip_id}.mp4"
        clip_path = clips_cache_dir / clip_filename

        if not clip_path.exists():
            clip_path, error = _download_cloud_clip_core_sync(
                clip_id, blink_instance, clips_cache_dir
            )
            if error or clip_path is None:
                # Determine appropriate status code based on error message
                status_code = 500  # Default to server error
                if error and (
                    "not found" in error.lower()
                    or "clip not found" in error.lower()
                    or "could not get download url" in error.lower()
                ):
                    status_code = 404
                elif error and (
                    "invalid url" in error.lower()
                    or "no scheme supplied" in error.lower()
                ):
                    status_code = 404  # Treat URL errors as not found

                response_dict, _ = create_api_response(
                    success=False,
                    error=error or "Failed to download cloud clip",
                    status_code=status_code,
                )
                return response_dict, status_code

        return download_clip_common(clip_path, clip_id)

    except Exception as e:
        logger.error(f"Error in download_cloud_clip: {e}")
        response_dict, status_code = create_api_response(
            success=False,
            error=f"Failed to download cloud clip: {e}",
            status_code=500,
        )
        return response_dict, status_code


def download_local_clip(
    clip_id: ClipId, sync_name: str | None = None, item_id: str | None = None
) -> Response | tuple[JsonDict, int]:
    """Download a local clip using blinkpy LocalStorageMediaItem API.

    Args:
        clip_id: ClipId object representing the local clip to download.
        sync_name: Optional sync module name for the clip.
        item_id: Optional item ID for the clip.

    Returns:
        Response | tuple[JsonDict, int]: File response with video data or error response with status code.
    """
    try:
        from blinkapp.services.blink_service import get_blink_instance

        blink_instance = get_blink_instance()
        if not blink_instance or not blink_instance.available:
            return create_api_response(
                success=False,
                error=Config.ErrorMessages.BLINK_NOT_AVAILABLE,
                status_code=503,
            )

        # Parse local clip ID to get sync module and item ID
        if sync_name is None or item_id is None:
            sync_name, item_id_str = clip_id.get_local_parts()
        else:
            item_id_str = item_id

        # Get sync module
        sync_dict = blink_instance.sync
        if sync_name not in sync_dict:
            return create_api_response(
                success=False,
                error=f"Sync module '{sync_name}' not found",
                status_code=404,
            )

        sync_module = sync_dict[sync_name]
        if not sync_module.local_storage:
            return create_api_response(
                success=False,
                error="Local storage not available",
                status_code=503,
            )

        # Find the LocalStorageMediaItem in the manifest
        manifest = sync_module._local_storage["manifest"]
        local_item = None
        for item in manifest:
            if str(item.id) == str(item_id_str):
                local_item = item
                break

        if local_item is None:
            return create_api_response(
                success=False,
                error=f"Local clip item '{item_id_str}' not found",
                status_code=404,
            )

        # Check if clip is already cached
        from blinkapp import CLIPS_CACHE_DIR

        clips_cache_dir = Path(CLIPS_CACHE_DIR).resolve()  # Use absolute path
        clips_cache_dir.mkdir(
            parents=True, exist_ok=True
        )  # Ensure cache directory exists
        cache_filename = f"local_{sync_name}_{item_id_str}_{local_item.name}_{local_item.created_at.strftime('%Y%m%d_%H%M%S')}.mp4"
        cached_filepath = clips_cache_dir / cache_filename

        if cached_filepath.exists():
            # Return cached file
            return flask.send_file(
                cached_filepath,
                as_attachment=True,
                download_name=f"clip_{clip_id}.mp4",
                mimetype="video/mp4",
            )

        # Download the clip using LocalStorageMediaItem API
        from blinkapp.services.blink_service import ensure_blink_connection_initialized

        ensure_blink_connection_initialized()

        async def download_local_clip_async() -> tuple[Path | None, str]:
            """Download local clip asynchronously and return file path or error.

            Returns:
                tuple[Path | None, str]: Tuple of (file_path, error_message).
            """
            """Download local clip asynchronously."""
            try:
                # Prepare the clip for download (uploads to Blink cloud temporarily)
                prepare_result = await local_item.prepare_download(blink_instance)
                if not prepare_result:
                    return None, "Failed to prepare local clip for download"

                # Download the clip to cache
                download_success = await local_item.download_video(
                    blink_instance, str(cached_filepath)
                )
                if not download_success:
                    return None, "Failed to download local clip"

                return cached_filepath, ""
            except Exception as e:
                return None, f"Error downloading local clip: {e}"

        # Execute the async download
        filepath, error = ensure_blink_connection_initialized().execute(
            download_local_clip_async()
        )

        if error:
            logger.error(f"Error downloading local clip {clip_id}: {error}")
            return create_api_response(
                success=False,
                error=error,
                status_code=500,
            )

        if filepath and filepath.exists():
            return flask.send_file(
                filepath,
                as_attachment=True,
                download_name=f"clip_{clip_id}.mp4",
                mimetype="video/mp4",
            )
        else:
            return create_api_response(
                success=False,
                error="Downloaded file not found",
                status_code=500,
            )

    except Exception as e:
        logger.error(f"Error in download_local_clip: {e}")
        return create_api_response(
            success=False,
            error=f"Failed to download local clip: {e}",
            status_code=500,
        )


def download_clip_common(
    clip_path: Path, clip_id: ClipId
) -> Response | tuple[JsonDict, int]:
    """Common clip download functionality for both cloud and local clips.

    Args:
        clip_path: Path object pointing to the clip file to serve.
        clip_id: ClipId object for generating the download filename.

    Returns:
        Response | tuple[JsonDict, int]: File response or error response with status code.
    """
    try:
        if not clip_path.exists():
            return create_api_response(
                success=False,
                error=f"Clip file not found: {clip_path}",
                status_code=404,
            )

        # Return the file
        return flask.send_file(
            clip_path,
            as_attachment=True,
            download_name=f"clip_{clip_id}.mp4",
            mimetype="video/mp4",
        )

    except Exception as e:
        logger.error(f"Error serving clip file {clip_path}: {e}")
        return create_api_response(
            success=False,
            error=f"Failed to serve clip file: {e}",
            status_code=500,
        )
