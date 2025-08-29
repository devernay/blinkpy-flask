"""Device service for Blink Camera Flask application.

This module provides utilities for processing and formatting device data from
Blink cameras, including temperature readings, battery status, and device
information aggregation.

Key functions:
- Device data creation and formatting
- Temperature conversion and display
- Safe data extraction with fallback values

Battery Handling:
Uses camera.battery which returns battery state strings (e.g., "ok", "low")
directly from the Blink API as the preferred approach.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blinkpy.camera import BlinkCamera


logger = logging.getLogger(__name__)

__all__ = ["create_device_data", "format_device_temperature"]


def format_device_temperature(temperature: float | int | None) -> str:
    """Format device temperature for display.

    Converts temperature values to a user-friendly string format.
    Currently displays in Fahrenheit as returned by the Blink API.

    Note: The Blink API returns temperatures in Fahrenheit. The blinkpy library
    provides a temperature_c property for Celsius conversion using the formula:
    celsius = (fahrenheit - 32) / 9.0 * 5.0

    TODO: Enhance to respect user temperature unit settings (temperatureUnits)
    from the settings service to display in Celsius when preferred.

    Args:
        temperature: Temperature value in Fahrenheit (numeric or None)

    Returns:
        Formatted temperature string (e.g., "72.5°F") or "N/A" if invalid
    """
    if temperature is None:
        return "N/A"
    try:
        temp_val = float(temperature)
        return f"{temp_val}°F"
    except (ValueError, TypeError):
        return "N/A"


def create_device_data(
    camera: BlinkCamera, current_ts: int = 0, cached_ts: int = 0
) -> dict[str, object]:
    """Create comprehensive device data dictionary for a Blink camera.

    Aggregates camera information including status, battery level, temperature,
    and thumbnail metadata into a standardized format for API responses.

    Args:
        camera: Blink camera instance with device attributes
        current_ts: Current timestamp for thumbnail freshness (default: 0)
        cached_ts: Cached thumbnail timestamp (default: 0)

    Returns:
        Dictionary containing:
        - Basic info: id, name, type, status
        - Hardware: battery, temperature, temperature_calibrated, wifi_strength
        - Metadata: last_updated, thumbnail_age
        - Capabilities: enabled status, motion detection

    Note:
        temperature_calibrated provides more accurate readings from dedicated sensor endpoint,
        falls back to regular temperature if calibrated value unavailable
    """
    from datetime import UTC, datetime

    from blinkapp import logger
    from blinkapp.services.time_service import seconds_since_now_from_datetime
    from blinkapp.utils.formatters import format_time_duration

    # Use the most recent timestamp for display
    display_ts = max(cached_ts, current_ts)
    last_updated = "Never"

    # Format timestamp into human-readable "X ago" format
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
        "temperature_calibrated": camera.temperature_calibrated,
        "wifi_strength": camera.wifi_strength,
    }
