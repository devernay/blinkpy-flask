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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def create_device_data(
    camera, cache_key=None, current_ts=None, cached_ts=None
) -> dict[str, Any]:
    """Create device data dictionary for a camera.

    Args:
        camera: Camera object
        cache_key: Optional cache key
        current_ts: Optional current timestamp
        cached_ts: Optional cached timestamp

    Returns:
        Dictionary with device data
    """
    from blinkapp import create_device_data as _create_device_data

    if cache_key is not None and current_ts is not None and cached_ts is not None:
        return _create_device_data(camera, cache_key, current_ts, cached_ts)
    else:
        return _create_device_data(camera)


def dump_blink_system_info() -> None:
    """Dump Blink system information for debugging."""
    from blinkapp import dump_blink_system_info as _dump_blink_system_info

    _dump_blink_system_info()


def handle_dump_system() -> None:
    """Handle system dump request."""
    from blinkapp import handle_dump_system as _handle_dump_system

    _handle_dump_system()
