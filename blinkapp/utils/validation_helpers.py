"""Validation helper functions for route parameters."""

from __future__ import annotations

from blinkapp.models.ids import CameraId, ClipId, NetworkId

__all__ = [
    "validate_camera_id",
    "validate_clip_id", 
    "validate_network_id",
]


def validate_camera_id(value: str) -> bool:
    """Validate if string can be converted to CameraId."""
    try:
        CameraId(value)
        return True
    except ValueError:
        return False


def validate_clip_id(value: str) -> bool:
    """Validate if string can be converted to ClipId."""
    try:
        ClipId(value)
        return True
    except ValueError:
        return False


def validate_network_id(value: str) -> bool:
    """Validate if string can be converted to NetworkId."""
    try:
        NetworkId(value)
        return True
    except ValueError:
        return False
