"""Validation helper functions for route parameters."""

from __future__ import annotations

from blinkapp.models.ids import CameraId, ClipId, NetworkId

__all__ = [
    "validate_camera_id",
    "validate_clip_id",
    "validate_network_id",
]


def validate_camera_id(value: str) -> CameraId:
    """ValidationFunction: Convert string to validated CameraId object.
    
    ValidationFunctions take string URL parameters and return validated objects.
    They should raise ValueError/TypeError if validation fails.
    
    Args:
        value: String camera ID from URL parameter
        
    Returns:
        CameraId: Validated camera ID object
        
    Raises:
        ValueError: If camera ID format is invalid
    """
    return CameraId(value)


def validate_clip_id(value: str) -> ClipId:
    """ValidationFunction: Convert string to validated ClipId object.
    
    ValidationFunctions take string URL parameters and return validated objects.
    They should raise ValueError/TypeError if validation fails.
    
    Args:
        value: String clip ID from URL parameter
        
    Returns:
        ClipId: Validated clip ID object
        
    Raises:
        ValueError: If clip ID format is invalid
    """
    return ClipId(value)


def validate_network_id(value: str) -> NetworkId:
    """ValidationFunction: Convert string to validated NetworkId object.
    
    ValidationFunctions take string URL parameters and return validated objects.
    They should raise ValueError/TypeError if validation fails.
    
    Args:
        value: String network ID from URL parameter
        
    Returns:
        NetworkId: Validated network ID object
        
    Raises:
        ValueError: If network ID format is invalid
    """
    return NetworkId(value)
