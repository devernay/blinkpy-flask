"""Connexion-compatible camera management handlers."""

from typing import Any


def list_cameras() -> dict[str, Any]:
    """Get list of all available cameras across all systems.

    Connexion-compatible handler that returns camera information.
    """
    from ..services.blink_service import ensure_blink_connection_initialized
    from ..services.device_service import create_device_data

    blink_connection = ensure_blink_connection_initialized()
    blink = blink_connection.blink

    if blink is None or not hasattr(blink, "cameras"):
        return {"cameras": []}

    cameras = []
    for camera_id, camera in blink.cameras.items():
        camera_data = create_device_data(camera)
        cameras.append(camera_data)

    return {"cameras": cameras}
