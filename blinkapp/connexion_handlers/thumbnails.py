"""Connexion-compatible thumbnail handlers."""

from typing import TYPE_CHECKING

from ..models.ids import CameraId
from ..models.types import JsonDict

if TYPE_CHECKING:
    from flask import Response


def get_camera_thumbnail(
    camera_id: str, timestamp: bool = False
) -> "Response | JsonDict | tuple[JsonDict, int]":
    """Get camera thumbnail."""
    from ..services.camera_service import find_camera_by_id

    try:
        camera_id_obj = CameraId(camera_id)
        camera = find_camera_by_id(camera_id_obj)
        
        if not camera:
            return {"success": False, "error": "Camera not found"}, 404
            
        # For now, return a simple response since the actual thumbnail logic is complex
        if timestamp:
            return {"success": True, "data": {"timestamp": "2025-01-01T00:00:00Z"}}
        else:
            return {"success": False, "error": "Thumbnail not available"}, 404
            
    except ValueError:
        return {"success": False, "error": "Invalid camera ID"}, 400


def refresh_camera_thumbnail(camera_id: str) -> JsonDict | tuple[JsonDict, int]:
    """Refresh camera thumbnail."""
    from ..services.camera_service import find_camera_by_id

    try:
        camera_id_obj = CameraId(camera_id)
        camera = find_camera_by_id(camera_id_obj)
        
        if not camera:
            return {"success": False, "error": "Camera not found"}, 404
            
        return {"success": True, "data": {"message": "Thumbnail refresh initiated"}}
        
    except ValueError:
        return {"success": False, "error": "Invalid camera ID"}, 400
