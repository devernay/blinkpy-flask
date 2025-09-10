"""Device data formatting utilities for UI display."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blinkpy.camera import BlinkCamera
from blinkapp.models.types import DeviceDict


def create_device_data(
    camera: "BlinkCamera", current_ts: int = 0, cached_ts: int = 0
) -> DeviceDict:
    """Create device data for UI display.

    Args:
        camera: BlinkCamera instance
        current_ts: Current timestamp
        cached_ts: Cached timestamp

    Returns:
        Device data dictionary for UI
    """
    if not camera:
        return {}

    # Calculate display timestamp
    display_ts = cached_ts if cached_ts > current_ts else current_ts

    return {
        "id": camera.camera_id,
        "name": camera.name,
        "thumbnail": camera.thumbnail,
        "status": camera.arm,  # Use arm property for status (motion detection enabled/disabled)
        "battery": camera.battery,
        "temperature": camera.temperature,
        "wifi_strength": camera.wifi_strength,
        "motion_enabled": camera.motion_enabled,
        "display_ts": display_ts,
    }
