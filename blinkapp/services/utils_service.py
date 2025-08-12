"""Utils service for Blink Camera Flask application.

This module handles utility functions and common operations
that are used across multiple parts of the application.
"""

from __future__ import annotations

__all__ = [
    "create_device_data",
    "dump_blink_system_info",
    "handle_dump_system",
]

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blinkapp.models.ids import CameraId
    from blinkpy.camera import BlinkCamera

logger = logging.getLogger(__name__)


def create_device_data(
    camera: BlinkCamera, cache_key: CameraId, current_ts: int, cached_ts: int
) -> dict[str, object]:
    """Create device data dictionary for camera.

    Builds a standardized device object for API responses, including
    camera status, thumbnail information, and human-readable timestamps.
    This function handles the complex logic of determining the most
    recent thumbnail timestamp and formatting it for display.

    Args:
        camera: Camera object from blinkpy library with device properties
        cache_key: Validated camera ID for API endpoints
        current_ts: Current thumbnail timestamp from Blink API
        cached_ts: Cached thumbnail timestamp from local storage

    Returns:
        Device data dictionary for API response with standardized fields:
        - type: Always "camera"
        - name: Camera display name
        - id: Camera ID for API calls
        - thumbnail: Thumbnail endpoint URL
        - last_updated: Human-readable time since last update
        - motion_enabled: Boolean motion detection status
        - battery: Battery level (if available)
        - temperature: Temperature reading (if available)
        - wifi_strength: WiFi signal strength (if available)

    Example:
        >>> device = create_device_data(
        ...     camera, CameraId("12345"), 1609459200, 1609459100
        ... )
        >>> device["last_updated"]
        "5m ago"
    """
    from datetime import datetime

    from blinkapp import format_time_ago, logger

    # Use the most recent timestamp between current and cached
    # This ensures we show the latest available thumbnail information
    display_ts = max(cached_ts, current_ts)
    last_updated = "Never"

    if display_ts > 0:
        try:
            # Calculate human-readable time difference
            thumbnail_time = datetime.fromtimestamp(display_ts)
            now = datetime.now()
            diff = now - thumbnail_time
            days = diff.days

            # Format time difference in most appropriate unit
            if days == 0:
                hours = diff.seconds // 3600
                if hours == 0:
                    minutes = diff.seconds // 60
                    last_updated = f"{minutes}m ago"
                else:
                    last_updated = f"{hours}h ago"
            else:
                last_updated = f"{days}d ago"
        except (ValueError, TypeError, AttributeError) as e:
            # Fallback to camera's last record time if timestamp calculation fails
            logger.debug(
                f"Failed to calculate time difference for camera {camera.name}: {e}"
            )
            last_updated = (
                format_time_ago(camera.last_record) if camera.last_record else "Never"
            )

    # Return standardized device object for consistent API responses
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


def dump_blink_system_info() -> None:
    """Dump Blink system information for debugging."""
    from blinkapp import dump_blink_system_info as _dump_blink_system_info

    _dump_blink_system_info()


def handle_dump_system() -> None:
    """Handle system dump request."""
    from blinkapp import handle_dump_system as _handle_dump_system

    _handle_dump_system()
