"""Connexion-compatible clips management handlers."""

from typing import TYPE_CHECKING

from ..config import Config
from ..models.ids import ClipId
from ..models.types import ClipsResponse, JsonDict

if TYPE_CHECKING:
    from flask import Response


def get_clips(storage: str | None = None) -> ClipsResponse | tuple[JsonDict, int]:
    """Get clips from cloud or local storage."""
    from ..services.blink_service import blink, blink_connection
    from ..services.clip_service import process_cloud_clips, process_local_clips
    from ..utils.decorators import error_context

    if storage is None:
        storage = "cloud"

    if storage not in ["cloud", "local"]:
        return {
            "success": False,
            "error": "Invalid storage type. Must be 'cloud' or 'local'",
        }, 400

    assert blink is not None

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
    """Delete clip."""
    from ..services.clip_service import delete_clip

    try:
        clip_id_obj = ClipId(clip_id)
        return delete_clip(clip_id_obj)
    except ValueError:
        return {"success": False, "error": "Invalid clip ID"}, 400


def download_clip(clip_id: str) -> "Response | tuple[JsonDict, int]":
    """Download clip file."""
    from ..services.clip_service import download_clip

    try:
        clip_id_obj = ClipId(clip_id)
        return download_clip(clip_id_obj)
    except ValueError:
        return {"success": False, "error": "Invalid clip ID"}, 400


def get_clip_thumbnail(
    clip_id: str, check: bool = False
) -> "Response | JsonDict | tuple[JsonDict, int]":
    """Get clip thumbnail."""
    from ..services.clip_service import get_clip_thumbnail

    try:
        clip_id_obj = ClipId(clip_id)
        return get_clip_thumbnail(clip_id_obj, check)
    except ValueError:
        return {"success": False, "error": "Invalid clip ID"}, 400


def generate_clip_thumbnail(clip_id: str) -> JsonDict | tuple[JsonDict, int]:
    """Generate clip thumbnail."""
    from ..services.clip_service import generate_clip_thumbnail

    try:
        clip_id_obj = ClipId(clip_id)
        return generate_clip_thumbnail(clip_id_obj)
    except ValueError:
        return {"success": False, "error": "Invalid clip ID"}, 400
