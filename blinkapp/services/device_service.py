"""Device service for Blink Camera Flask application.

This module provides utilities for processing and formatting device data from
Blink cameras, including temperature readings, battery levels, and device
information aggregation.

Key functions:
- Device data creation and formatting
- Temperature conversion and display
- Battery level assessment from voltage readings
- Safe data extraction with fallback values
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blinkpy.camera import BlinkCamera

    from blinkapp.models.ids import CameraId

logger = logging.getLogger(__name__)

__all__ = ["create_device_data", "format_device_temperature", "format_battery_level"]


def format_device_temperature(temperature) -> str:
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


def format_battery_level(voltage) -> str:
    """Format battery level based on voltage reading.

    Converts voltage readings to user-friendly battery status indicators.
    Uses standard lithium battery voltage thresholds for Blink cameras.

    Voltage values are in 100ths of volts (e.g., 163 = 1.63V).
    Thresholds based on typical lithium battery discharge curves:
    - Good: >150 (>1.50V) - Full to good charge
    - Fair: 140-150 (1.40-1.50V) - Moderate charge
    - Low: <140 (<1.40V) - Needs replacement

    Args:
        voltage: Battery voltage reading in 100ths of volts (numeric or None)

    Returns:
        Battery status: "Good", "Fair", "Low", or "N/A"
    """
    if voltage is None:
        return "N/A"
    try:
        volt_val = float(voltage)
        # Lithium battery voltage thresholds (values in 100ths of volts)
        if volt_val > 150:  # >1.50V
            return "Good"
        elif volt_val > 140:  # 1.40-1.50V
            return "Fair"
        else:  # <1.40V
            return "Low"
    except (ValueError, TypeError):
        return "N/A"


def create_device_data(
    camera: BlinkCamera, cache_key: CameraId, current_ts: int = 0, cached_ts: int = 0
) -> dict[str, object]:
    """Create comprehensive device data dictionary for a Blink camera.

    Aggregates camera information including status, battery level, temperature,
    and thumbnail metadata into a standardized format for API responses.

    Args:
        camera: Blink camera instance with device attributes
        cache_key: Unique identifier for the camera
        current_ts: Current timestamp for thumbnail freshness (default: 0)
        cached_ts: Cached thumbnail timestamp (default: 0)

    Returns:
        Dictionary containing:
        - Basic info: id, name, type, status
        - Hardware: battery_level, temperature, signal_strength
        - Metadata: last_updated, thumbnail_age
        - Capabilities: enabled status, motion detection
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
        "wifi_strength": camera.wifi_strength,
    }
