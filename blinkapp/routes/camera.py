"""Camera management routes for Blink Camera Flask application."""

from __future__ import annotations

from typing import TYPE_CHECKING

from blinkapp.models.ids import CameraId
from blinkapp.models.types import JsonDict
from blinkapp.utils.decorators import ensure_blink_available
from blinkapp.utils.route_decorators import api_route_with_validation
from blinkapp.utils.validation_helpers import validate_camera_id

if TYPE_CHECKING:
    from flask import Flask


def setup_camera_routes(app: Flask) -> None:
    """Register camera routes with the Flask app.

    Args:
        app: Flask application instance to register routes with.
    """

    @app.route("/api/cameras")
    @ensure_blink_available
    @api_route_with_validation("list cameras")
    def list_cameras_route() -> JsonDict:
        """List cameras route - retrieves all available cameras from Blink systems.

        Returns:
            JsonDict: List of camera data with details and status information.
        """
        from ..connexion_handlers.camera import list_cameras

        return list_cameras()

    @app.route("/api/cameras/<camera_id_str>")
    @ensure_blink_available
    @api_route_with_validation(
        "get camera details", validate_params={"camera_id_str": validate_camera_id}
    )
    def get_camera_details_route(
        camera_id_str: str,
    ) -> JsonDict | tuple[JsonDict, int]:
        """Get camera details route - retrieves detailed information for a specific camera.

        Args:
            camera_id_str: String representation of the camera ID to get details for.

        Returns:
            JsonDict | tuple[JsonDict, int]: Camera details data or error response with status code.
        """
        from ..connexion_handlers.camera import get_camera_details

        camera_id = CameraId(camera_id_str)
        return get_camera_details(str(camera_id))

    @app.route("/api/cameras/<camera_id_str>/record", methods=["POST"])
    @ensure_blink_available
    @api_route_with_validation(
        "start camera recording", validate_params={"camera_id_str": validate_camera_id}
    )
    def start_camera_recording_route(
        camera_id: CameraId,
    ) -> JsonDict | tuple[JsonDict, int]:
        """Start camera recording route - initiates video recording on the specified camera.

        Args:
            camera_id: CameraId object representing the camera to start recording on.

        Returns:
            JsonDict | tuple[JsonDict, int]: Success response or error response with status code.
        """
        from ..connexion_handlers.camera import start_camera_recording

        return start_camera_recording(str(camera_id))
