"""Connexion-compatible thumbnail handlers."""

from typing import TYPE_CHECKING

from ..models.ids import CameraId
from ..models.types import JsonDict

if TYPE_CHECKING:
    from flask import Response


def get_camera_thumbnail(
    camera_id: str, timestamp: bool = False
) -> "Response | JsonDict | tuple[JsonDict, int]":
    """Get camera thumbnail.

    Args:
        camera_id: ID of the camera to get thumbnail for.
        timestamp: Whether to return timestamp information.

    Returns:
        Thumbnail file response or error tuple.
    """
    from ..services.thumbnail_service import get_camera_thumbnail

    try:
        camera_id_obj = CameraId(camera_id)
        return get_camera_thumbnail(camera_id_obj, timestamp)
    except ValueError:
        return {"success": False, "error": "Invalid camera ID"}, 400


def refresh_camera_thumbnail(camera_id: str) -> JsonDict | tuple[JsonDict, int]:
    """Refresh camera thumbnail.

    Args:
        camera_id: ID of the camera to refresh thumbnail for.

    Returns:
        Refresh response or error tuple.
    """
    from ..services.thumbnail_service import refresh_camera_thumbnail

    try:
        camera_id_obj = CameraId(camera_id)
        return refresh_camera_thumbnail(camera_id_obj)
    except ValueError:
        return {"success": False, "error": "Invalid camera ID"}, 400
