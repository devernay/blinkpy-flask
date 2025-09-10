"""Device data formatting utilities for UI display."""

from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from blinkpy.camera import BlinkCamera
from blinkapp.models.types import DeviceDict


def create_device_data(camera: "BlinkCamera", current_ts: int = 0, cached_ts: int = 0) -> DeviceDict:
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
        "id": camera.id,  # type: ignore[attr-defined]  # type: ignore[attr-defined]
        "name": camera.name,  # type: ignore[attr-defined]
        "thumbnail": camera.thumbnail,  # type: ignore[attr-defined]
        "status": camera.status,  # type: ignore[attr-defined]  # type: ignore[attr-defined]
        "battery": camera.battery,  # type: ignore[attr-defined]
        "temperature": camera.temperature,  # type: ignore[attr-defined]
        "wifi_strength": camera.wifi_strength,  # type: ignore[attr-defined]
        "motion_enabled": camera.motion_enabled,  # type: ignore[attr-defined]
        "display_ts": display_ts,
    }
