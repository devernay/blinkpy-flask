"""Connexion-compatible streaming handlers."""

from typing import TYPE_CHECKING

from ..models.ids import CameraId
from ..models.types import JsonDict

if TYPE_CHECKING:
    from flask import Response


def start_live_stream(camera_id: str) -> JsonDict | tuple[JsonDict, int]:
    """Start live stream for camera."""
    from ..services.stream_service import start_camera_stream

    try:
        camera_id_obj = CameraId(camera_id)
        return start_camera_stream(camera_id_obj)
    except ValueError:
        return {"success": False, "error": "Invalid camera ID"}, 400


def stop_live_stream(camera_id: str) -> JsonDict | tuple[JsonDict, int]:
    """Stop live stream for camera."""
    from ..services.stream_service import stop_camera_stream

    try:
        camera_id_obj = CameraId(camera_id)
        return stop_camera_stream(camera_id_obj)
    except ValueError:
        return {"success": False, "error": "Invalid camera ID"}, 400


def get_hls_stream_segments(
    camera_id: str, filename: str
) -> "Response | tuple[JsonDict, int]":
    """Get HLS stream segments."""
    from ..services.stream_service import get_hls_file

    try:
        camera_id_obj = CameraId(camera_id)
        return get_hls_file(camera_id_obj, filename)
    except ValueError:
        return {"success": False, "error": "Invalid camera ID"}, 400
