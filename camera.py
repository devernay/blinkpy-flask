"""Camera operations module for Blink Flask application.

This module handles all camera-related operations including:
- Camera lookup and validation
- Thumbnail management and caching
- Live streaming functionality
- Camera route handlers

Extracted from app.py to improve code organization and maintainability.
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import cast

from flask import Flask, Response

from blinkpy.camera import BlinkCamera
from decorators import (
    error_context,
    requires_blink,
)
from errors import CameraError, ValidationError
from ids import CameraId
from route_decorators import api_route_with_validation
from utils import (
    Config,
    create_api_response,
)

# Type definitions (matching app.py)
JsonDict = dict[str, object]
ApiResponse = tuple[JsonDict, int]
FlaskResponse = Response

logger = logging.getLogger(__name__)


def extract_thumbnail_timestamp(thumbnail_url: str | None) -> int:
    """Extract timestamp from thumbnail URL.

    Args:
        thumbnail_url: URL containing ts parameter

    Returns:
        Timestamp as integer, 0 if not found
    """
    if not thumbnail_url:
        return 0
    try:
        match = re.search(r"ts=([0-9]+)", thumbnail_url)
        return int(match.group(1)) if match else 0
    except (AttributeError, ValueError, TypeError) as e:
        logger.debug(f"Failed to extract timestamp from URL '{thumbnail_url}': {e}")
        return 0


def find_camera_by_id(camera_id: CameraId) -> BlinkCamera | None:
    """Find camera by ID across all sync modules.

    Args:
        camera_id: Camera ID to search for

    Returns:
        Camera object if found, None otherwise
    """
    # Import locally to avoid circular imports
    from blinkapp import blink

    if blink is None or not blink.available:
        return None

    for sync_name, sync in blink.sync.items():
        for cam_name, cam in sync.cameras.items():
            if str(cam.camera_id) == str(camera_id):
                return cam
    return None


def require_camera(
    camera_id: CameraId,
) -> tuple[BlinkCamera | None, tuple[ApiResponse, int] | None]:
    """Find camera by ID, return error response if not found.

    Args:
        camera_id: Camera ID to find

    Returns:
        Tuple of (camera, error_response). One will be None.
    """
    camera = find_camera_by_id(camera_id)
    if camera is None:
        error_response = create_api_response(
            success=False, error=Config.ErrorMessages.CAMERA_NOT_FOUND, status_code=404
        )
        return None, error_response
    return camera, None


def update_camera_thumbnail(
    camera: BlinkCamera, cache_key: CameraId, current_ts: int, cached_ts: int
) -> None:
    """Update camera thumbnail in background if needed.

    Args:
        camera: Camera object from blinkpy
        cache_key: Validated camera ID
        current_ts: Current thumbnail timestamp
        cached_ts: Cached thumbnail timestamp
    """
    # Import locally to avoid circular imports
    from blinkapp import (
        THUMBNAIL_CACHE_DIR,
        blink_connection,
        executor,
        thumbnail_cache,
    )

    if current_ts <= cached_ts:
        return

    logger.debug(
        f"Updating thumbnail cache for {camera.name} (ts: {current_ts} > {cached_ts})"
    )

    def update_thumbnail() -> None:
        # Double-check timestamp to prevent race condition
        current_entry = thumbnail_cache.get(cache_key)
        current_cached_ts = current_entry.get("timestamp", 0) if current_entry else 0
        if current_ts <= current_cached_ts:
            logger.debug(f"Thumbnail already updated for {camera.name}, skipping")
            return

        # Remove old cached file if exists
        old_entry = thumbnail_cache.get(cache_key)
        if old_entry is not None:
            old_filename = old_entry.get("filename")
            if old_filename is not None:
                assert THUMBNAIL_CACHE_DIR is not None
                old_filepath = Path(cast(str, THUMBNAIL_CACHE_DIR)) / old_filename
                try:
                    if old_filepath.exists():
                        old_filepath.unlink()
                        logger.debug(f"Removed old thumbnail file: {old_filename}")
                except OSError as e:
                    logger.debug(f"Could not remove old thumbnail: {e}")

        thumbnail_response = blink_connection.execute(camera.thumbnail)
        if (
            thumbnail_response is not None
            and thumbnail_response.status == Config.HTTP_STATUS_OK
        ):
            image_data = blink_connection.execute(thumbnail_response.read())

            # Save to file with new timestamp
            filename = f"{cache_key}_{current_ts}.jpg"
            assert THUMBNAIL_CACHE_DIR is not None
            filepath = Path(cast(str, THUMBNAIL_CACHE_DIR)) / filename
            try:
                filepath.write_bytes(image_data)
                # Update cache info atomically
                thumbnail_cache[cache_key] = {
                    "timestamp": current_ts,
                    "filename": filename,
                }
                logger.debug(
                    f"Cached thumbnail for {camera.name} with timestamp {current_ts}"
                )
            except OSError as e:
                logger.error(f"Failed to save thumbnail for {camera.name}: {e}")
        else:
            logger.warning(f"Failed to fetch thumbnail for {camera.name}")

    # Import locally to avoid circular imports
    executor.submit(update_thumbnail)


def setup_camera_routes(app: Flask) -> None:
    """Register camera routes with the Flask app.

    Args:
        app: Flask application instance
    """

    @app.route("/api/camera/<camera_id_str>/refresh", methods=["POST"])
    @requires_blink
    @api_route_with_validation(
        "refresh camera thumbnail", validate_params={"camera_id_str": CameraId}
    )
    def refresh_camera(camera_id: CameraId) -> JsonDict:
        """Refresh camera thumbnail.

        Args:
            camera_id: Validated CameraId object (converted from camera_id_str by decorator)

        Returns:
            JSON response with success status or error message
        """
        # Import locally to avoid circular imports
        from blinkapp import THUMBNAIL_CACHE_DIR, blink, executor, thumbnail_cache

        assert blink is not None

        camera, error_response = require_camera(camera_id)
        if error_response is not None:
            raise ValidationError(error_response[0]["error"], error_response[1])

        assert camera is not None
        with error_context("refresh camera thumbnail", CameraError):
            # Remove camera thumbnail from cache in background
            def remove_thumbnail_cache() -> None:
                cache_key = str(camera_id)
                cached_info = thumbnail_cache.get(cache_key)
                if cached_info is not None:
                    # Remove cached file
                    if "filename" in cached_info:
                        assert THUMBNAIL_CACHE_DIR is not None
                        cached_file = (
                            Path(cast(str, THUMBNAIL_CACHE_DIR))
                            / cached_info["filename"]
                        )
                        try:
                            if cached_file.exists():
                                cached_file.unlink()
                        except OSError as e:
                            logger.debug(f"Could not remove cached thumbnail: {e}")
                    # Remove from cache
                    thumbnail_cache.pop(cache_key, None)

            executor.submit(remove_thumbnail_cache)

            # Trigger thumbnail update
            camera.snap_picture()

            return {"success": True, "message": "Camera thumbnail refresh initiated"}

    @app.route("/api/camera/<camera_id_str>/liveview")
    @requires_blink
    @api_route_with_validation(
        "start camera liveview", validate_params={"camera_id_str": CameraId}
    )
    def get_camera_liveview(camera_id: CameraId) -> JsonDict:
        """Get live view stream for camera using init_livestream() as specified in IMPLEMENTATION.md.

        Args:
            camera_id: Validated CameraId object (converted from camera_id_str by decorator)

        Returns:
            JSON response with stream URLs (TCP and HLS) or error message

        Raises:
            ValueError: If camera_id_str is invalid
        """
        # Import locally to avoid circular imports
        from blinkapp import blink_connection, stream_manager

        # camera_id is now validated and converted by the decorator

        camera, error_response = require_camera(camera_id)
        if error_response is not None:
            # Re-raise as exception to be handled by decorator
            raise ValidationError(error_response[0]["error"], error_response[1])

        assert camera is not None

        # Use init_livestream() as specified in IMPLEMENTATION.md
        async def init_stream() -> object:
            stream = await camera.init_livestream()
            if (
                stream is not None
                and hasattr(stream, "start")
                and hasattr(stream, "feed")
            ):
                await stream.start()
                # Start feeding the stream in the background
                asyncio.create_task(stream.feed())
            return stream

        # Execute the async livestream initialization
        stream = blink_connection.execute(init_stream())

        if stream is not None:
            # Get the TCP URL from the stream
            tcp_url = stream.url
            logger.info(f"Livestream TCP URL for camera {camera_id}: {tcp_url}")

            # Start HLS transcoding from the TCP stream
            if stream_manager is not None:
                hls_url, error_msg = stream_manager.start_stream(
                    str(camera_id), tcp_url
                )
            else:
                hls_url = None

            if hls_url is not None:
                # Store the stream object for later cleanup
                if not hasattr(blink_connection, "_active_streams"):
                    blink_connection._active_streams = {}
                blink_connection._active_streams[str(camera_id)] = stream

                return {
                    "success": True,
                    "tcp_url": tcp_url,
                    "hls_url": hls_url,
                    "message": "Live stream started successfully",
                }
            else:
                return {
                    "success": False,
                    "error": error_msg or "Failed to start HLS transcoding",
                }
        else:
            return {"success": False, "error": "Failed to initialize live stream"}

    @app.route("/api/camera/<camera_id_str>/liveview/stop", methods=["POST"])
    @requires_blink
    @api_route_with_validation(
        "stop camera liveview", validate_params={"camera_id_str": CameraId}
    )
    def stop_camera_liveview(camera_id: CameraId) -> JsonDict:
        """Stop live view stream for camera.

        Args:
            camera_id: Validated CameraId object (converted from camera_id_str by decorator)

        Returns:
            JSON response with success status or error message
        """
        # Import locally to avoid circular imports
        from blinkapp import blink_connection, stream_manager

        try:
            # Stop HLS transcoding
            if stream_manager is not None:
                stream_manager.stop_stream(str(camera_id))

            # Stop and cleanup the TCP stream
            if hasattr(blink_connection, "_active_streams"):
                stream = blink_connection._active_streams.pop(str(camera_id), None)
                if stream is not None and hasattr(stream, "stop"):
                    # Execute async stop in the blink connection thread
                    async def stop_stream() -> None:
                        await stream.stop()

                    blink_connection.execute(stop_stream())

            return {"success": True, "message": "Live stream stopped successfully"}

        except Exception as e:
            logger.error(f"Error stopping live stream for camera {camera_id}: {e}")
            return {"success": False, "error": "Failed to stop live stream"}

    @app.route("/api/hls/<camera_id_str>/<path:filename>")
    @api_route_with_validation(
        "serve HLS file", validate_params={"camera_id_str": CameraId}
    )
    def serve_hls_file(camera_id: CameraId, filename: str) -> FlaskResponse:
        """Serve HLS files for live streaming.

        Args:
            camera_id: Validated CameraId object (converted from camera_id_str by decorator)
            filename: HLS file to serve

        Returns:
            Flask Response with HLS file content or error
        """
        # Import locally to avoid circular imports
        from blinkapp import stream_manager

        if stream_manager is None:
            return create_api_response(
                success=False, error="Stream manager not available", status_code=503
            )

        try:
            return stream_manager.serve_hls_file(str(camera_id), filename)
        except Exception as e:
            logger.error(
                f"Error serving HLS file {filename} for camera {camera_id}: {e}"
            )
            return create_api_response(
                success=False, error="Failed to serve HLS file", status_code=500
            )

    @app.route("/api/camera/<camera_id_str>/thumbnail/timestamp")
    @requires_blink
    @api_route_with_validation(
        "get camera thumbnail timestamp", validate_params={"camera_id_str": CameraId}
    )
    def get_camera_thumbnail_timestamp(camera_id: CameraId) -> JsonDict:
        """Get camera thumbnail timestamp for polling.

        Args:
            camera_id: Validated CameraId object (converted from camera_id_str by decorator)

        Returns:
            JSON response with timestamp or error message

        Raises:
            ValueError: If camera_id_str is invalid
        """
        # camera_id is now validated and converted by the decorator

        camera = find_camera_by_id(camera_id)
        if camera is None:
            raise ValidationError(Config.ErrorMessages.CAMERA_NOT_FOUND, 404)

        timestamp = extract_thumbnail_timestamp(camera.thumbnail)
        logger.info(
            f"Camera {camera_id} thumbnail timestamp: {timestamp}, URL: {camera.thumbnail}"
        )
        return {"timestamp": timestamp}

    @app.route("/api/camera/<camera_id_str>/thumbnail")
    @requires_blink
    @api_route_with_validation(
        "get camera thumbnail", validate_params={"camera_id_str": CameraId}
    )
    def get_camera_thumbnail(camera_id: CameraId) -> FlaskResponse:
        """Proxy camera thumbnail with authentication.

        Args:
            camera_id: Validated CameraId object (converted from camera_id_str by decorator)

        Returns:
            Flask Response with image data or error message

        Returns:
            JPEG image file or JSON error response

        Raises:
            ValueError: If camera_id_str is invalid
        """
        # Import locally to avoid circular imports
        from flask import Response

        from blinkapp import THUMBNAIL_CACHE_DIR, blink_connection, thumbnail_cache

        # camera_id is now validated and converted by the decorator

        camera = find_camera_by_id(camera_id)
        if camera is None or camera.thumbnail is None:
            raise ValidationError(Config.ErrorMessages.CAMERA_THUMBNAIL_NOT_FOUND, 404)

        # Check cache first
        cache_key = str(camera_id)
        cached_info = thumbnail_cache.get(cache_key)
        current_ts = extract_thumbnail_timestamp(camera.thumbnail)

        if cached_info is not None:
            cached_ts = cached_info.get("timestamp", 0)
            cached_filename = cached_info.get("filename")

            # Check if cached version is current
            if current_ts <= cached_ts and cached_filename is not None:
                assert THUMBNAIL_CACHE_DIR is not None
                cached_file = Path(cast(str, THUMBNAIL_CACHE_DIR)) / cached_filename
                if cached_file.exists():
                    try:
                        image_data = cached_file.read_bytes()
                        return Response(
                            image_data,
                            mimetype="image/jpeg",
                            headers={"Cache-Control": "public, max-age=300"},
                        )
                    except OSError as e:
                        logger.debug(f"Could not read cached thumbnail: {e}")

            # Update cache in background if needed
            update_camera_thumbnail(camera, cache_key, current_ts, cached_ts)

        # Fetch from Blink API
        thumbnail_response = blink_connection.execute(camera.thumbnail)
        if (
            thumbnail_response is not None
            and thumbnail_response.status == Config.HTTP_STATUS_OK
        ):
            image_data = blink_connection.execute(thumbnail_response.read())
            return Response(
                image_data,
                mimetype="image/jpeg",
                headers={"Cache-Control": "public, max-age=300"},
            )
        else:
            raise ValidationError(Config.ErrorMessages.CAMERA_THUMBNAIL_NOT_FOUND, 404)
