"""Connexion-compatible clips management handlers."""

from typing import TYPE_CHECKING

from ..config import Config
from ..models.ids import ClipId
from ..models.types import ClipsResponse, JsonDict

if TYPE_CHECKING:
    from flask import Response


def get_clips(storage: str | None = None) -> ClipsResponse | tuple[JsonDict, int]:
    """Get clips from cloud or local storage.

    Args:
        storage: Storage type filter ('cloud' or 'local'). None returns all clips.

    Returns:
        ClipsResponse with organized clip data or error tuple.
    """
    from ..services.blink_service import (
        ensure_blink_connection_initialized,
        ensure_blink_initialized,
    )
    from ..services.clip_service import process_cloud_clips, process_local_clips
    from ..utils.decorators import error_context

    if storage is None:
        storage = "cloud"

    if storage not in ["cloud", "local"]:
        return {
            "success": False,
            "error": "Invalid storage type. Must be 'cloud' or 'local'",
        }, 400

    blink = ensure_blink_initialized()
    blink_connection = ensure_blink_connection_initialized()

    with error_context(f"get {storage} clips"):
        if storage == "cloud":
            if blink_connection:
                videos_metadata = blink_connection.execute(
                    blink.get_videos_metadata(stop=Config.CLIPS_PER_STORAGE_TYPE)
                )
            else:
                videos_metadata = []
            return {"clips": process_cloud_clips(videos_metadata)}
        else:
            return {"clips": process_local_clips()}


def delete_clip(clip_id: str) -> JsonDict | tuple[JsonDict, int]:
    """Delete clip.

    Args:
        clip_id: ID of the clip to delete.

    Returns:
        Success response or error tuple.
    """
    import asyncio

    from ..services.clip_service import delete_clip as delete_clip_service

    try:
        clip_id_obj = ClipId(clip_id)
        return asyncio.run(delete_clip_service(clip_id_obj))
    except ValueError:
        return {"success": False, "error": "Invalid clip ID"}, 400


def download_clip(clip_id: str) -> "Response | tuple[JsonDict, int]":
    """Download clip file.

    Args:
        clip_id: ID of the clip to download.

    Returns:
        File response for download or error tuple.
    """
    from ..services.clip_service import download_clip

    try:
        clip_id_obj = ClipId(clip_id)
        return download_clip(clip_id_obj)
    except ValueError:
        return {"success": False, "error": "Invalid clip ID"}, 400


def get_clip_thumbnail(
    clip_id: str, check: bool = False
) -> "Response | JsonDict | tuple[JsonDict, int]":
    """Get clip thumbnail.

    Args:
        clip_id: ID of the clip to get thumbnail for.
        check: If True, return availability info instead of file.

    Returns:
        Thumbnail file response, availability info, or error tuple.
    """
    from flask import send_file

    from ..models.ids import ClipId
    from ..services.cache_service import ensure_clips_cache_initialized

    try:
        clip_id_obj = ClipId(clip_id)
        clips_cache = ensure_clips_cache_initialized()

        # If check=true, always return 200 with availability info
        if check:
            if clip_id_obj in clips_cache:
                clip_entry = clips_cache[clip_id_obj]
                thumbnail_path = clip_entry.get("thumbnail")
                if (
                    clip_entry is not None
                    and thumbnail_path is not None
                    and thumbnail_path.exists()
                ):
                    return {"success": True, "exists": True, "available": True}
                else:
                    return {"success": True, "exists": False, "available": False}
            else:
                return {"success": True, "exists": False, "available": False}

        # For non-check requests, return the actual file or 404
        if clip_id_obj not in clips_cache:
            return {"success": False, "error": "Clip not found"}, 404

        clip_entry = clips_cache[clip_id_obj]

        # Return the thumbnail file if it exists
        thumbnail_path = clip_entry.get("thumbnail")
        if (
            clip_entry is not None
            and thumbnail_path is not None
            and thumbnail_path.exists()
        ):
            return send_file(thumbnail_path, mimetype="image/jpeg")
        else:
            return {"success": False, "error": "Thumbnail not found"}, 404

    except ValueError:
        return {"success": False, "error": "Invalid clip ID"}, 400


def generate_clip_thumbnail(clip_id: str) -> JsonDict | tuple[JsonDict, int]:
    """Generate clip thumbnail.

    Args:
        clip_id: ID of the clip to generate thumbnail for.

    Returns:
        Success response or error tuple.
    """
    from ..services.clip_processing import process_local_clip_background

    try:
        clip_id_obj = ClipId(clip_id)
        # Launch background thumbnail generation for the clip
        process_local_clip_background(clip_id_obj)
        return {"success": True, "message": f"Thumbnail generation started for clip {clip_id}"}, 200
    except ValueError:
        return {"success": False, "error": "Invalid clip ID"}, 400
