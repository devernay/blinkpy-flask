"""Connexion-compatible camera management handlers."""

from ..models.ids import CameraId
from ..models.types import DeviceDict, JsonDict


def list_cameras() -> dict[str, list[DeviceDict]]:
    """Get list of all available cameras across all systems.

    Returns:
        Cameras list dictionary
    """
    from ..services.blink_service import ensure_blink_connection_initialized
    from ..services.device_service import create_device_data

    blink_connection = ensure_blink_connection_initialized()
    blink = blink_connection.blink

    if blink is None or blink.cameras is None:
        return {"cameras": []}

    cameras = []
    for camera_id, camera in blink.cameras.items():
        camera_data = create_device_data(camera)
        cameras.append(camera_data)

    return {"cameras": cameras}


def get_camera_details(camera_id: str) -> JsonDict | tuple[JsonDict, int]:
    """Get camera details.

    Args:
        camera_id: Camera ID string

    Returns:
        Camera details dictionary
    """
    from ..services.camera_service import get_camera_details

    try:
        camera_id_obj = CameraId(camera_id)
        return get_camera_details(camera_id_obj)
    except ValueError:
        return {"success": False, "error": "Invalid camera ID"}, 400


def start_camera_recording(camera_id: str) -> JsonDict | tuple[JsonDict, int]:
    """Start recording on camera.

    Args:
        camera_id: Camera ID string

    Returns:
        Recording start result
    """
    import asyncio

    from ..services.camera_service import record_camera

    try:
        camera_id_obj = CameraId(camera_id)
        return asyncio.run(record_camera(camera_id_obj))
    except ValueError:
        return {"success": False, "error": "Invalid camera ID"}, 400
