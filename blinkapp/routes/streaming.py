"""Streaming routes for Blink Camera Flask application.

This module handles live streaming operations including:
- Stream initialization and management
- HLS file serving
- Stream cleanup and termination
"""

from __future__ import annotations

__all__ = [
    "setup_streaming_routes",
    "_init_camera_stream",
    "logger",
]

import logging
from typing import TYPE_CHECKING

from flask import send_file

from blinkapp.config import Config
from blinkapp.models.ids import CameraId
from blinkapp.models.types import JsonDict
from blinkapp.utils.decorators import ensure_blink_available, error_context
from blinkapp.utils.errors import CameraError, ValidationError
from blinkapp.utils.route_decorators import api_route_with_validation

if TYPE_CHECKING:
    from flask import Flask

    from blinkapp.models.types import FlaskResponse, JsonDict

logger = logging.getLogger(__name__)


def setup_streaming_routes(app: Flask) -> None:
    """Register streaming routes with the Flask app."""

    @app.route("/api/cameras/<camera_id_str>/streams", methods=["POST"])
    @ensure_blink_available
    @api_route_with_validation(
        "start camera stream", validate_params={"camera_id_str": CameraId}
    )
    def start_camera_stream(camera_id: CameraId) -> JsonDict:
        """Start live stream for camera.

        Args:
            camera_id: Validated camera ID

        Returns:
            JSON response with stream URL or error
        """
        from blinkapp.services.blink_service import ensure_blink_connection_initialized
        from blinkapp.services.camera_service import find_camera_by_id

        blink_connection = ensure_blink_connection_initialized()

        camera = find_camera_by_id(camera_id)
        if camera is None:
            raise ValidationError(Config.ErrorMessages.CAMERA_NOT_FOUND, 404)

        with error_context("start camera stream", CameraError):
            stream, hls_url = _init_camera_stream(camera, camera_id)

            if hls_url is not None:
                # Store the stream object for later cleanup
                blink_connection._active_streams[str(camera_id)] = stream

                return {
                    "success": True,
                    "stream_url": hls_url,
                    "message": f"Live stream started for camera {camera_id}",
                }

            return {"success": False, "error": "Failed to initialize live stream"}

    @app.route("/api/cameras/<camera_id_str>/streams", methods=["DELETE"])
    @ensure_blink_available
    @api_route_with_validation(
        "stop camera stream", validate_params={"camera_id_str": CameraId}
    )
    def stop_camera_stream(camera_id: CameraId) -> JsonDict:
        """Stop live stream for camera.

        Args:
            camera_id: Validated camera ID

        Returns:
            JSON response confirming stream stop
        """
        from blinkapp.services.blink_service import ensure_blink_connection_initialized

        blink_connection = ensure_blink_connection_initialized()

        with error_context("stop camera stream", CameraError):
            # Stop and cleanup the TCP stream
            if blink_connection is not None:
                stream = blink_connection._active_streams.pop(str(camera_id), None)
                if stream is not None:
                    # Execute stop in the blink connection thread
                    blink_connection.execute(stream.stop())
                    logger.info(f"Stopped live stream for camera {camera_id}")
                    return {
                        "success": True,
                        "message": f"Live stream stopped for camera {camera_id}",
                    }
                else:
                    return {
                        "success": False,
                        "error": f"No active stream found for camera {camera_id}",
                    }

            return {"success": False, "error": "Failed to stop live stream"}

    @app.route("/api/cameras/<camera_id_str>/streams/<path:filename>")
    @api_route_with_validation(
        "serve stream file", validate_params={"camera_id_str": CameraId}
    )
    def get_hls_file(camera_id: CameraId, filename: str) -> FlaskResponse:
        """Serve HLS stream files.

        Args:
            camera_id: Validated camera ID
            filename: HLS file name

        Returns:
            File response or error
        """
        from pathlib import Path

        from blinkapp import HLS_OUTPUT_DIR

        if HLS_OUTPUT_DIR is None:
            raise ValidationError("HLS output directory not configured", 500)

        # Construct file path
        file_path = Path(HLS_OUTPUT_DIR) / str(camera_id) / filename

        # Security check: ensure file is within expected directory
        try:
            file_path.resolve().relative_to(Path(HLS_OUTPUT_DIR).resolve())
        except ValueError:
            raise ValidationError("Invalid file path", 400) from None

        if not file_path.exists():
            raise ValidationError("Stream file not found", 404)

        # Determine MIME type based on file extension
        if filename.endswith(".m3u8"):
            mimetype = "application/vnd.apple.mpegurl"
        elif filename.endswith(".ts"):
            mimetype = "video/mp2t"
        else:
            mimetype = "application/octet-stream"

        return send_file(
            file_path,
            mimetype=mimetype,
            as_attachment=False,
            download_name=filename,
        )


def _init_camera_stream(
    camera: object, camera_id: CameraId
) -> tuple[object | None, str | None]:
    """Initialize camera stream and return stream object and HLS URL.

    Args:
        camera: Camera object from blinkpy
        camera_id: Camera ID for stream management

    Returns:
        Tuple of (stream_object, hls_url) or (None, None) on failure
    """
    from blinkapp import HLS_OUTPUT_DIR
    from blinkapp.services.stream_service import StreamManager

    if HLS_OUTPUT_DIR is None:
        logger.error("HLS output directory not configured")
        return None, None

    try:
        # Initialize camera livestream
        from blinkapp.services.blink_service import ensure_blink_connection_initialized

        connection = ensure_blink_connection_initialized()

        # Initialize livestream on camera to get TCP stream
        camera_stream = connection.execute(camera.init_livestream)  # type: ignore[attr-defined]
        if camera_stream is None:
            logger.error(f"Failed to initialize livestream for camera {camera_id}")
            return None, None

        # Start the camera stream
        connection.execute(camera_stream.start)  # type: ignore[attr-defined]
        tcp_url = camera_stream.url  # type: ignore[attr-defined]

        # Initialize stream manager
        stream_manager = StreamManager()

        # Start HLS transcoding
        hls_url, error = stream_manager.start_stream(str(camera_id), tcp_url)
        if hls_url is not None:
            logger.info(f"Started live stream for camera {camera_id}: {hls_url}")
            return camera_stream, hls_url
        else:
            logger.error(f"Failed to start stream for camera {camera_id}: {error}")
            return None, None

    except Exception as e:
        logger.error(f"Error initializing stream for camera {camera_id}: {e}")
        return None, None
