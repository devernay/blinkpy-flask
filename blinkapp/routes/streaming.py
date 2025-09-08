"""Streaming routes for Blink Camera Flask application."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from flask import Response

from ..models.ids import CameraId
from ..models.types import JsonDict
from ..utils.decorators import ensure_blink_available
from ..utils.route_decorators import api_route_with_validation
from ..utils.validation_helpers import validate_camera_id

if TYPE_CHECKING:
    from flask import Flask

logger = logging.getLogger(__name__)


def setup_streaming_routes(app: Flask) -> None:
    """Register streaming routes with the Flask app."""

    @app.route("/api/cameras/<camera_id_str>/streams", methods=["POST"])
    @ensure_blink_available
    @api_route_with_validation(
        "start live stream", validate_params={"camera_id_str": validate_camera_id}
    )
    def start_live_stream_route(camera_id: CameraId) -> JsonDict | tuple[JsonDict, int]:
        """Start stream route - thin wrapper around connexion handler."""
        from ..connexion_handlers.streaming import start_live_stream

        return start_live_stream(str(camera_id))

    @app.route("/api/cameras/<camera_id_str>/streams", methods=["DELETE"])
    @ensure_blink_available
    @api_route_with_validation(
        "stop live stream", validate_params={"camera_id_str": validate_camera_id}
    )
    def stop_live_stream_route(camera_id: CameraId) -> JsonDict | tuple[JsonDict, int]:
        """Stop stream route - thin wrapper around connexion handler."""
        from ..connexion_handlers.streaming import stop_live_stream

        return stop_live_stream(str(camera_id))

    @app.route("/api/cameras/<camera_id_str>/streams/<path:filename>")
    @ensure_blink_available
    @api_route_with_validation(
        "get HLS segments", validate_params={"camera_id_str": validate_camera_id}
    )
    def get_hls_stream_segments_route(
        camera_id: CameraId, filename: str
    ) -> Response | tuple[JsonDict, int]:
        """Get HLS segments route - thin wrapper around connexion handler."""
        from ..connexion_handlers.streaming import get_hls_stream_segments

        return get_hls_stream_segments(str(camera_id), filename)
