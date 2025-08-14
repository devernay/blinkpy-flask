"""Camera service for Blink Camera Flask application.

This module handles camera-related business logic including
camera lookup and validation.
"""

from __future__ import annotations

__all__ = [
    "find_camera_by_id",
    "require_camera",
]

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blinkpy.camera import BlinkCamera

    from blinkapp.models.ids import CameraId

logger = logging.getLogger(__name__)


def find_camera_by_id(
    camera_id: CameraId,
) -> BlinkCamera | None:
    """Find camera by ID across all sync modules.

    Searches through all available Blink sync modules and their cameras
    to find a camera matching the provided ID. This is necessary because
    cameras are organized under sync modules in the Blink API structure.

    Args:
        camera_id: Validated camera ID to search for

    Returns:
        BlinkCamera object if found, None if not found or Blink unavailable

    Example:
        >>> camera = find_camera_by_id(CameraId("12345"))
        >>> if camera:
        ...     print(f"Found camera: {camera.name}")
    """
    # Import locally to avoid circular imports during module initialization
    from blinkapp.services.blink_service import ensure_blink_initialized

    # Check if Blink system is available and initialized
    try:
        blink = ensure_blink_initialized()
    except RuntimeError:
        return None

    if not blink.available:
        return None

    # Search through all sync modules and their cameras
    for sync_name, sync in blink.sync.items():
        for cam_name, cam in sync.cameras.items():
            if str(cam.camera_id) == str(camera_id):
                return cam
    return None


def require_camera(
    camera_id: CameraId,
) -> tuple[BlinkCamera, None] | tuple[None, tuple[dict[str, object], int]]:
    """Find camera by ID, return error response if not found.

    This is a convenience function for API endpoints that need to find
    a camera and return a standardized error response if it doesn't exist.
    It combines camera lookup with error handling in a single call.

    Args:
        camera_id: Validated camera ID to find

    Returns:
        Tuple of (camera, error_response). Exactly one will be None:
        - If found: (BlinkCamera, None)
        - If not found: (None, error_response_tuple)

    Example:
        >>> camera, error = require_camera(CameraId("12345"))
        >>> if error:
        ...     return error  # Return error response to client
        >>> # Use camera for operations
    """
    from blinkapp.config import Config
    from blinkapp.models.responses import create_api_response

    camera = find_camera_by_id(camera_id)
    if camera is None:
        error_response = create_api_response(
            success=False, error=Config.ErrorMessages.CAMERA_NOT_FOUND, status_code=404
        )
        return None, error_response
    return camera, None
