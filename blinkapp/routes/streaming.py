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
    """Register streaming routes with the Flask app.

    Args:
        app: Flask application instance to register routes with.
    """

    @app.route("/api/cameras/<camera_id_str>/streams", methods=["POST"])
    @ensure_blink_available
    @api_route_with_validation(
        "start live stream", validate_params={"camera_id_str": validate_camera_id}
    )
    def start_live_stream_route(camera_id: CameraId) -> JsonDict | tuple[JsonDict, int]:
        """Start stream route - initiates live video streaming from the specified camera.

        Args:
            camera_id: CameraId object representing the camera to start streaming from.

        Returns:
            JsonDict | tuple[JsonDict, int]: Stream URL and details or error response with status code.
        """
        from ..connexion_handlers.streaming import start_live_stream

        return start_live_stream(str(camera_id))

    @app.route("/api/cameras/<camera_id_str>/streams", methods=["DELETE"])
    @ensure_blink_available
    @api_route_with_validation(
        "stop live stream", validate_params={"camera_id_str": validate_camera_id}
    )
    def stop_live_stream_route(camera_id: CameraId) -> JsonDict | tuple[JsonDict, int]:
        """Stop stream route - terminates live video streaming from the specified camera.

        Args:
            camera_id: CameraId object representing the camera to stop streaming from.

        Returns:
            JsonDict | tuple[JsonDict, int]: Success response or error response with status code.
        """
        from ..connexion_handlers.streaming import stop_live_stream

        return stop_live_stream(str(camera_id))

    @app.route("/api/cameras/<camera_id_str>/streams/save", methods=["PUT"])
    @ensure_blink_available
    @api_route_with_validation(
        "set live view save state",
        validate_params={"camera_id_str": validate_camera_id},
    )
    def set_live_view_save_state_route(
        camera_id: CameraId,
    ) -> JsonDict | tuple[JsonDict, int]:
        """Set whether the active live-view recording will be kept on stop.

        Args:
            camera_id: CameraId object for the active live-view session.

        Returns:
            JsonDict | tuple[JsonDict, int]: Success response or error response.
        """
        from flask import request

        from ..connexion_handlers.streaming import set_live_view_save

        # NOTE: pyright doesn't recognize Flask's request.get_json() method properly
        body = request.get_json(silent=True) or {}  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]
        return set_live_view_save(str(camera_id), bool(body.get("saved", False)))

    @app.route("/api/cameras/<camera_id_str>/streams/<path:filename>")
    @ensure_blink_available
    @api_route_with_validation(
        "get HLS segments", validate_params={"camera_id_str": validate_camera_id}
    )
    def get_hls_stream_segments_route(
        camera_id: CameraId, filename: str
    ) -> Response | tuple[JsonDict, int]:
        """Get HLS segments route - serves HLS video stream segments and playlists.

        Args:
            camera_id: CameraId object representing the camera stream.
            filename: HLS segment filename or playlist file to serve.

        Returns:
            Response | tuple[JsonDict, int]: HLS file response or error response with status code.
        """
        from ..connexion_handlers.streaming import get_hls_stream_segments

        return get_hls_stream_segments(str(camera_id), filename)
