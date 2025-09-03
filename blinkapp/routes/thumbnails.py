"""Thumbnail routes for Blink Camera Flask application."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from flask import Response, request

from ..models.ids import CameraId
from ..models.types import JsonDict
from ..utils.decorators import ensure_blink_available
from ..utils.route_decorators import api_route_with_validation

if TYPE_CHECKING:
    from flask import Flask

logger = logging.getLogger(__name__)


def update_camera_thumbnail(camera, current_ts: int, cached_ts: int) -> None:
    """Update camera thumbnail if current timestamp is newer than cached.

    Args:
        camera: BlinkCamera instance
        current_ts: Current timestamp from camera
        cached_ts: Cached timestamp
    """
    from ..services.connection_service import ensure_executor_initialized
    from ..services.thumbnail_service import _download_camera_thumbnail

    if current_ts > cached_ts:
        camera_id = CameraId(str(camera.camera_id))
        if camera is not None and camera.thumbnail:
            # Submit to executor for background processing
            executor = ensure_executor_initialized()
            executor.submit(
                _download_camera_thumbnail, camera_id, camera.thumbnail, current_ts
            )


def setup_camera_thumbnail_routes(app: Flask) -> None:
    """Register thumbnail routes with the Flask app."""

    @app.route("/api/cameras/<camera_id>/thumbnail")
    @ensure_blink_available
    @api_route_with_validation(
        "get camera thumbnail", validate_params={"camera_id": CameraId}
    )
    def get_camera_thumbnail_route(
        camera_id: CameraId,
    ) -> Response | JsonDict | tuple[JsonDict, int]:
        """Get thumbnail route - thin wrapper around connexion handler."""
        from ..connexion_handlers.thumbnails import get_camera_thumbnail

        timestamp = request.args.get("timestamp", "").lower() == "true"
        return get_camera_thumbnail(str(camera_id), timestamp)

    @app.route("/api/cameras/<camera_id>/thumbnail", methods=["DELETE"])
    @ensure_blink_available
    @api_route_with_validation(
        "refresh camera thumbnail", validate_params={"camera_id": CameraId}
    )
    def refresh_camera_thumbnail_route(
        camera_id: CameraId,
    ) -> JsonDict | tuple[JsonDict, int]:
        """Refresh thumbnail route - thin wrapper around connexion handler."""
        from ..connexion_handlers.thumbnails import refresh_camera_thumbnail

        return refresh_camera_thumbnail(str(camera_id))
