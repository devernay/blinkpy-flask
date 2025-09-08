"""Validation helper functions for route parameters."""

from __future__ import annotations

from blinkapp.models.ids import CameraId, ClipId, NetworkId

__all__ = [
    "validate_camera_id",
    "validate_clip_id", 
    "validate_network_id",
]


def validate_camera_id(value: str) -> CameraId:
    """Validate and convert string to CameraId."""
    return CameraId(value)


def validate_clip_id(value: str) -> ClipId:
    """Validate and convert string to ClipId."""
    return ClipId(value)


def validate_network_id(value: str) -> NetworkId:
    """Validate and convert string to NetworkId."""
    return NetworkId(value)
