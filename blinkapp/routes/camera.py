"""Camera operations module for Blink Flask application.

This module handles core camera-related operations including:
- Camera lookup and validation
- Camera details and listing
- Camera recording functionality

Thumbnail and streaming functionality moved to dedicated modules.
"""

import logging
from typing import TYPE_CHECKING

from blinkapp.config import Config
from blinkapp.models.ids import CameraId
from blinkapp.models.types import JsonDict
from blinkapp.utils.decorators import ensure_blink_available, error_context
from blinkapp.utils.errors import CameraError, ValidationError
from blinkapp.utils.route_decorators import api_route_with_validation

if TYPE_CHECKING:
    from flask import Flask

    from blinkapp.models.types import JsonDict

logger = logging.getLogger(__name__)

__all__ = ["setup_camera_routes"]


def setup_camera_routes(app: "Flask") -> None:
    """Register camera routes with the Flask app."""

    @app.route("/api/cameras")
    @ensure_blink_available
    @api_route_with_validation("list cameras")
    def list_cameras() -> JsonDict:
        """List all available cameras.

        Returns:
            JSON response with camera list
        """
        from blinkapp.services.blink_service import ensure_blink_connection_initialized
        from blinkapp.services.device_service import create_device_data

        blink_connection = ensure_blink_connection_initialized()

        with error_context("list cameras", CameraError):
            blink = blink_connection.blink
            if blink is None or not hasattr(blink, "cameras"):
                return {"cameras": []}

            cameras = []
            for camera_id, camera in blink.cameras.items():
                camera_data = create_device_data(camera, camera_id)
                cameras.append(camera_data)

            return {"cameras": cameras}

    @app.route("/api/cameras/<camera_id_str>")
    @ensure_blink_available
    @api_route_with_validation(
        "get camera details", validate_params={"camera_id_str": CameraId}
    )
    def get_camera_details(camera_id: CameraId) -> JsonDict:
        """Get detailed information about a specific camera.

        Args:
            camera_id: Validated camera ID

        Returns:
            JSON response with camera details
        """
        from blinkapp.services.camera_service import find_camera_by_id
        from blinkapp.services.device_service import create_device_data

        camera = find_camera_by_id(camera_id)
        if camera is None:
            raise ValidationError(Config.ErrorMessages.CAMERA_NOT_FOUND, 404)

        with error_context("get camera details", CameraError):
            camera_data = create_device_data(camera, camera_id)
            return {"camera": camera_data}

    @app.route("/api/cameras/<camera_id_str>/record", methods=["POST"])
    @ensure_blink_available
    @api_route_with_validation(
        "start camera recording", validate_params={"camera_id_str": CameraId}
    )
    def start_camera_recording(camera_id: CameraId) -> JsonDict:
        """Start recording on a camera.

        Args:
            camera_id: Validated camera ID

        Returns:
            JSON response confirming recording start
        """
        from blinkapp.services.blink_service import ensure_blink_connection_initialized
        from blinkapp.services.camera_service import find_camera_by_id

        blink_connection = ensure_blink_connection_initialized()

        camera = find_camera_by_id(camera_id)
        if camera is None:
            raise ValidationError(Config.ErrorMessages.CAMERA_NOT_FOUND, 404)

        with error_context("start camera recording", CameraError):
            # Start recording
            result = blink_connection.execute(camera.record())
            if result:
                return {
                    "success": True,
                    "message": f"Recording started for camera {camera_id}",
                }
            else:
                raise CameraError("Failed to initiate camera recording", 500)
