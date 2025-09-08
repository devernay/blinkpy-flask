"""Camera service for Blink Camera Flask application.

This module handles camera-related business logic including
camera lookup and validation.
"""

from __future__ import annotations

__all__ = [
    "find_camera_by_id",
    "require_camera",
    "get_camera_details",
    "record_camera",
]

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blinkpy.camera import BlinkCamera

    from blinkapp.models.ids import CameraId
    from blinkapp.models.types import JsonDict

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
    for _, sync in blink.sync.items():
        for _, cam in sync.cameras.items():
            if str(cam.camera_id) == str(camera_id):
                return cam
    return None


def get_camera_details(camera_id: CameraId) -> JsonDict | tuple[JsonDict, int]:
    """Get detailed information about a specific camera.

    Args:
        camera_id: Validated camera ID to get details for

    Returns:
        Camera details dictionary or error response tuple
    """
    from blinkapp.models.responses import create_api_response

    camera, error = require_camera(camera_id)
    if error:
        return error

    # Camera is guaranteed to be non-None here due to require_camera logic
    assert camera is not None

    return create_api_response(
        success=True,
        data={
            "id": str(camera.camera_id),
            "name": camera.name,
            "battery": camera.battery,
            "temperature": camera.temperature,
            "wifi_strength": camera.wifi_strength,
        },
    )


def require_camera(
    camera_id: CameraId,
) -> tuple[BlinkCamera, None] | tuple[None, tuple[JsonDict, int]]:
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


async def record_camera(camera_id: "CameraId") -> tuple[dict[str, str], int]:
    """Start recording on a camera.
    
    Args:
        camera_id: The camera ID to start recording
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    from blinkapp.models.responses import create_api_response
    from blinkapp.services.blink_service import ensure_blink_connection_initialized
    
    try:
        # Use shared BlinkConnection instance
        blink_conn = ensure_blink_connection_initialized()
        
        # Find camera through shared connection
        camera = await blink_conn.run_in_thread(find_camera_by_id, camera_id)
        if camera is None:
            response, status_code = create_api_response(
                success=False, 
                error="Camera not found", 
                status_code=404
            )
            return response, status_code
        
        # Start recording through shared connection thread
        await blink_conn.run_in_thread(camera.record)
        
        response, status_code = create_api_response(
            success=True, 
            data={"message": f"Recording started for camera {camera_id}"}
        )
        return response, status_code
    except Exception as e:
        logger.error(f"Failed to start recording for camera {camera_id}: {e}")
        response, status_code = create_api_response(
            success=False, 
            error=f"Failed to start recording: {str(e)}", 
            status_code=500
        )
        return response, status_code
