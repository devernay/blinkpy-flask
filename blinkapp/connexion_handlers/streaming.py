"""Connexion-compatible streaming handlers."""

from typing import TYPE_CHECKING

from ..models.ids import CameraId
from ..models.types import JsonDict

if TYPE_CHECKING:
    from flask import Response


def start_live_stream(camera_id: str) -> JsonDict | tuple[JsonDict, int]:
    """Start live stream for camera.

    Args:
        camera_id: ID of the camera to start streaming.

    Returns:
        Stream start response or error tuple.
    """
    from ..services.camera_service import find_camera_by_id
    from ..services.stream_service import init_camera_stream

    try:
        camera_id_obj = CameraId(camera_id)

        # Find the camera object
        camera = find_camera_by_id(camera_id_obj)
        if not camera:
            return {"success": False, "error": "Camera not found"}, 404

        # Initialize the stream
        stream_obj, hls_url = init_camera_stream(camera, camera_id_obj)
        if hls_url:
            from ..services.stream_service import get_live_view_save_state

            return {
                "success": True,
                "stream_url": hls_url,
                "playlist_url": hls_url,
                "save_active": get_live_view_save_state(camera_id_obj),
            }
        return {"success": False, "error": "Failed to start stream"}, 500

    except ValueError:
        return {"success": False, "error": "Invalid camera ID"}, 400


def stop_live_stream(camera_id: str) -> JsonDict | tuple[JsonDict, int]:
    """Stop live stream for camera.

    Args:
        camera_id: ID of the camera to stop streaming.

    Returns:
        Stream stop response or error tuple.
    """
    from ..services.stream_service import stop_camera_stream

    try:
        camera_id_obj = CameraId(camera_id)
        success = stop_camera_stream(camera_id_obj)
        return {
            "success": success,
            "message": f"Stream {'stopped' if success else 'stop failed'} for camera {camera_id}",
        }
    except ValueError:
        return {"success": False, "error": "Invalid camera ID"}, 400


def set_live_view_save(camera_id: str, saved: bool) -> JsonDict | tuple[JsonDict, int]:
    """Set whether the active live-view recording is kept when the session ends.

    Args:
        camera_id: ID of the camera with the active live-view session.
        saved: True to keep the recording on stop, False to discard it.

    Returns:
        Success response (with the applied state) or error tuple.
    """
    from ..services.stream_service import set_live_view_save_state

    try:
        camera_id_obj = CameraId(camera_id)
        updated = set_live_view_save_state(camera_id_obj, saved)
        if not updated:
            return {"success": False, "error": "No active live view for camera"}, 404
        return {"success": True, "save_active": saved}
    except ValueError:
        return {"success": False, "error": "Invalid camera ID"}, 400


def get_hls_stream_segments(
    camera_id: str, filename: str
) -> "Response | tuple[JsonDict, int]":
    """Get HLS stream segments.

    Args:
        camera_id: ID of the camera streaming.
        filename: Name of the HLS segment file.

    Returns:
        HLS segment file response or error tuple.
    """
    from ..services.stream_service import get_hls_file

    try:
        camera_id_obj = CameraId(camera_id)
        result = get_hls_file(camera_id_obj, filename)

        # Type narrowing with assert
        if result[0] is not None and result[1] is not None:
            from flask import Response

            return Response(result[0], mimetype=result[1])
        return {"success": False, "error": "HLS file not found"}, 404
    except ValueError:
        return {"success": False, "error": "Invalid camera ID"}, 400
