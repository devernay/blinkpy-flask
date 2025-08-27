"""Device service for Blink Camera Flask application."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blinkpy.camera import BlinkCamera

    from blinkapp.models.ids import CameraId

logger = logging.getLogger(__name__)

__all__ = ["create_device_data", "format_device_temperature", "format_battery_level"]


def format_device_temperature(temperature) -> str:
    """Format device temperature - pure function."""
    if temperature is None:
        return "N/A"
    try:
        temp_val = float(temperature)
        return f"{temp_val}°F"
    except (ValueError, TypeError):
        return "N/A"


def format_battery_level(voltage) -> str:
    """Format battery level - pure function."""
    if voltage is None:
        return "N/A"
    try:
        volt_val = float(voltage)
        if volt_val > 120:
            return "Good"
        elif volt_val > 110:
            return "Fair"
        else:
            return "Low"
    except (ValueError, TypeError):
        return "N/A"


def create_device_data(
    camera: BlinkCamera, cache_key: CameraId, current_ts: int = 0, cached_ts: int = 0
) -> dict[str, object]:
    """Create device data dictionary for camera."""
    from datetime import UTC, datetime

    from blinkapp import logger
    from blinkapp.services.time_service import seconds_since_now_from_datetime
    from blinkapp.utils.formatters import format_time_duration

    display_ts = max(cached_ts, current_ts)
    last_updated = "Never"

    if display_ts > 0:
        try:
            dt = datetime.fromtimestamp(display_ts, tz=UTC)
            seconds = seconds_since_now_from_datetime(dt)
            last_updated = f"{format_time_duration(seconds)} ago"
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to format timestamp {display_ts}: {e}")
            last_updated = "Unknown"

    return {
        "type": "camera",
        "name": camera.name,
        "id": camera.camera_id,
        "thumbnail": f"/api/camera/{camera.camera_id}/thumbnail",
        "last_updated": last_updated,
        "motion_enabled": camera.motion_enabled,
        "battery": camera.battery,
        "temperature": camera.temperature,
        "wifi_strength": camera.wifi_strength,
    }
