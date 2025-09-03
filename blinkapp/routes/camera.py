"""Camera management routes for Blink Camera Flask application."""

from __future__ import annotations

from typing import TYPE_CHECKING

from blinkapp.models.ids import CameraId
from blinkapp.models.types import JsonDict
from blinkapp.utils.decorators import ensure_blink_available
from blinkapp.utils.route_decorators import api_route_with_validation

if TYPE_CHECKING:
    from flask import Flask


def setup_camera_routes(app: Flask) -> None:
    """Register camera routes with the Flask app."""

    @app.route("/api/cameras")
    @ensure_blink_available
    @api_route_with_validation("list cameras")
    def list_cameras_route() -> JsonDict:
        """List cameras route - thin wrapper around connexion handler."""
        from ..connexion_handlers.camera import list_cameras

        return list_cameras()

    @app.route("/api/cameras/<camera_id_str>")
    @ensure_blink_available
    @api_route_with_validation(
        "get camera details", validate_params={"camera_id_str": CameraId}
    )
    def get_camera_details_route(
        camera_id: CameraId,
    ) -> JsonDict | tuple[JsonDict, int]:
        """Get camera details route - thin wrapper around connexion handler."""
        from ..connexion_handlers.camera import get_camera_details

        return get_camera_details(str(camera_id))

    @app.route("/api/cameras/<camera_id_str>/record", methods=["POST"])
    @ensure_blink_available
    @api_route_with_validation(
        "start camera recording", validate_params={"camera_id_str": CameraId}
    )
    def start_camera_recording_route(
        camera_id: CameraId,
    ) -> JsonDict | tuple[JsonDict, int]:
        """Start recording route - thin wrapper around connexion handler."""
        from ..connexion_handlers.camera import start_camera_recording

        return start_camera_recording(str(camera_id))
