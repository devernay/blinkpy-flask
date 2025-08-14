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
from pathlib import Path
from typing import TYPE_CHECKING, cast

from flask import Flask, Response, jsonify, request

from blinkapp.models.ids import CameraId
from blinkapp.models.types import FlaskResponse, JsonDict

if TYPE_CHECKING:
    from blinkpy.camera import BlinkCamera
    from blinkpy.livestream import BlinkLiveStream
from blinkpy.camera import BlinkCamera

from blinkapp.config import Config
from blinkapp.models.responses import create_api_response
from blinkapp.services.camera_service import (
    find_camera_by_id,
    require_camera,
)
from blinkapp.utils.decorators import (
    api_route_with_validation,
    ensure_blink_available,
    error_context,
)
from blinkapp.utils.errors import CameraError, ValidationError
from blinkapp.utils.validators import (
    extract_thumbnail_timestamp,
)

logger = logging.getLogger(__name__)

# Explicitly define what this module exports
__all__ = [
    "update_camera_thumbnail",
    "setup_camera_routes",
]


# find_camera_by_id and require_camera moved to blinkapp.services.camera_service


def update_camera_thumbnail(
    camera: "BlinkCamera", cache_key: CameraId, current_ts: int, cached_ts: int
) -> None:
    """Update camera thumbnail in background if needed.

    Compares timestamps and triggers a background thumbnail update if the
    camera has a newer thumbnail available. This prevents blocking the
    API response while ensuring thumbnails stay current.

    The function uses a background thread pool to download and cache the
    new thumbnail without affecting response times. It includes race
    condition protection and automatic cleanup of old thumbnail files.

    Args:
        camera: Camera object from blinkpy library
        cache_key: Validated camera ID for cache operations
        current_ts: Current thumbnail timestamp from camera API
        cached_ts: Previously cached thumbnail timestamp

    Side Effects:
        - Submits background task to thread pool executor
        - Updates thumbnail cache when complete
        - Removes old thumbnail files from disk

    Example:
        >>> update_camera_thumbnail(camera, CameraId("123"), 1609459200, 1609459100)
        # Background update starts, function returns immediately
    """
    # Import locally to avoid circular imports during module initialization
    from blinkapp import (
        THUMBNAIL_CACHE_DIR,
    )
    from blinkapp.services.blink_service import ensure_blink_connection_initialized
    from blinkapp.services.cache_service import (
        ensure_cache_paths_initialized,
        ensure_thumbnail_cache_initialized,
    )
    from blinkapp.services.connection_service import ensure_executor_initialized

    # Ensure all required components are initialized
    ensure_cache_paths_initialized()
    blink_connection = ensure_blink_connection_initialized()
    executor = ensure_executor_initialized()
    thumbnail_cache = ensure_thumbnail_cache_initialized()

    # THUMBNAIL_CACHE_DIR is guaranteed to be not None after ensure_cache_paths_initialized()
    assert THUMBNAIL_CACHE_DIR is not None

    # Skip update if cached version is already current or newer
    if current_ts <= cached_ts:
        return

    logger.debug(
        f"Updating thumbnail cache for {camera.name} (ts: {current_ts} > {cached_ts})"
    )

    def update_thumbnail() -> None:
        """Background task to download and cache new thumbnail.

        This function runs in a background thread to avoid blocking
        the main request. It handles race conditions, file cleanup,
        and error recovery automatically.
        """
        # Double-check timestamp to prevent race condition with concurrent requests
        # Another request might have updated the cache while we were queued
        current_entry = thumbnail_cache.get(cache_key)
        current_cached_ts = (
            int(current_entry.get("timestamp", 0)) if current_entry else 0
        )
        if current_ts <= current_cached_ts:
            logger.debug(f"Thumbnail already updated for {camera.name}, skipping")
            return

        # Clean up old cached file to prevent disk space accumulation
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


async def _init_camera_stream(camera: "BlinkCamera") -> "BlinkLiveStream | None":
    """Initialize camera livestream."""
    stream = await camera.init_livestream()
    if stream is not None:
        await stream.start()
        # Start feeding the stream in the background
        asyncio.create_task(stream.feed())
    return stream


def setup_camera_routes(app: Flask) -> None:
    """Register camera routes with the Flask app.

    Args:
        app: Flask application instance
    """

    @app.route("/api/cameras/<camera_id_str>/refresh", methods=["PUT"])
    @ensure_blink_available
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
        from blinkapp import (
            THUMBNAIL_CACHE_DIR,
        )
        from blinkapp.services.blink_service import (
            ensure_blink_connection_initialized,
            ensure_blink_initialized,
        )
        from blinkapp.services.cache_service import (
            ensure_cache_paths_initialized,
            ensure_thumbnail_cache_initialized,
        )
        from blinkapp.services.connection_service import ensure_executor_initialized

        # Ensure all required components are initialized
        ensure_blink_initialized()  # We don't need the return value
        blink_connection = ensure_blink_connection_initialized()
        executor = ensure_executor_initialized()
        thumbnail_cache = ensure_thumbnail_cache_initialized()
        ensure_cache_paths_initialized()

        # THUMBNAIL_CACHE_DIR is guaranteed to be not None after ensure_cache_paths_initialized()
        assert THUMBNAIL_CACHE_DIR is not None

        camera, error_response = require_camera(camera_id)
        if error_response is not None:
            error_dict, status_code = error_response
            error_message = error_dict.get("error", "Unknown error")
            raise ValidationError(str(error_message), status_code)

        assert camera is not None
        with error_context("refresh camera thumbnail", CameraError):
            # Remove camera thumbnail from cache in background
            def remove_thumbnail_cache() -> None:
                cached_info = thumbnail_cache.get(camera_id)
                if cached_info is not None:
                    # Remove cached file
                    if "filename" in cached_info:
                        assert THUMBNAIL_CACHE_DIR is not None
                        cached_file = Path(cast(str, THUMBNAIL_CACHE_DIR)) / str(
                            cached_info["filename"]
                        )
                        try:
                            if cached_file.exists():
                                cached_file.unlink()
                        except OSError as e:
                            logger.debug(f"Could not remove cached thumbnail: {e}")
                    # Remove from cache
                    thumbnail_cache.pop(camera_id, {})

            executor.submit(remove_thumbnail_cache)

            # Trigger thumbnail update
            blink_connection.execute(camera.snap_picture())

            return {"success": True, "message": "Camera thumbnail refresh initiated"}

    @app.route("/api/cameras/<camera_id_str>/liveview")
    @ensure_blink_available
    @api_route_with_validation(
        "start camera liveview", validate_params={"camera_id_str": CameraId}
    )
    def get_camera_liveview(camera_id: CameraId) -> JsonDict:
        """Get live view stream for camera using init_livestream().

        Args:
            camera_id: Validated CameraId object

        Returns:
            JSON response with stream URLs (TCP and HLS) or error message
        """
        # Import locally to avoid circular imports
        from blinkapp.services.blink_service import ensure_blink_connection_initialized
        from blinkapp.services.stream_service import ensure_stream_manager_initialized

        # Ensure required components are initialized
        blink_connection = ensure_blink_connection_initialized()
        stream_manager = ensure_stream_manager_initialized()

        camera, error_response = require_camera(camera_id)
        if error_response is not None:
            # Re-raise as exception to be handled by decorator
            error_dict, status_code = error_response
            error_message = error_dict.get("error", "Unknown error")
            raise ValidationError(str(error_message), status_code)

        assert camera is not None

        # Use init_livestream() as specified in IMPLEMENTATION.md
        # Execute the async livestream initialization
        stream = blink_connection.execute(_init_camera_stream(camera))

        if stream is not None:
            # Get the TCP URL from the stream
            tcp_url = stream.url
            logger.info(f"Livestream TCP URL for camera {camera_id}: {tcp_url}")

            # Start HLS transcoding from the TCP stream
            error_msg = "Failed to start HLS transcoding"  # Default error message
            if stream_manager is not None:
                hls_url, error_msg = stream_manager.start_stream(
                    str(camera_id), tcp_url
                )
            else:
                hls_url = None

            if hls_url is not None:
                # Store the stream object for later cleanup
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

    @app.route("/api/cameras/<camera_id_str>/liveview", methods=["DELETE"])
    @ensure_blink_available
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
        from blinkapp.services.blink_service import ensure_blink_connection_initialized
        from blinkapp.services.stream_service import ensure_stream_manager_initialized

        # Ensure required components are initialized
        blink_connection = ensure_blink_connection_initialized()
        stream_manager = ensure_stream_manager_initialized()

        try:
            # Stop HLS transcoding
            stream_manager.stop_stream(str(camera_id))

            # Stop and cleanup the TCP stream
            if blink_connection is not None:
                stream = blink_connection._active_streams.pop(str(camera_id), None)
                if stream is not None:
                    # Execute stop in the blink connection thread
                    async def stop_stream() -> None:
                        stream.stop()

                    blink_connection.execute(stop_stream())

            return {"success": True, "message": "Live stream stopped successfully"}

        except Exception as e:
            logger.error(f"Error stopping live stream for camera {camera_id}: {e}")
            return {"success": False, "error": "Failed to stop live stream"}

    @app.route("/api/cameras/<camera_id_str>/hls/<path:filename>")
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
        from blinkapp.services.stream_service import ensure_stream_manager_initialized

        # Ensure stream manager is initialized
        stream_manager = ensure_stream_manager_initialized()

        try:
            content, content_type = stream_manager.get_hls_file(
                str(camera_id), filename
            )
            if content and content_type:
                from flask import Response

                return Response(content, mimetype=content_type)
            else:
                from flask import jsonify

                response, status_code = create_api_response(
                    success=False, error="HLS file not found", status_code=404
                )
                return jsonify(response), status_code
        except Exception as e:
            logger.error(
                f"Error serving HLS file {filename} for camera {camera_id}: {e}"
            )
            from flask import jsonify

            response, status_code = create_api_response(
                success=False, error="Failed to serve HLS file", status_code=500
            )
            return jsonify(response), status_code

    @app.route("/api/cameras/<camera_id_str>/thumbnail")
    @ensure_blink_available
    @api_route_with_validation(
        "get camera thumbnail", validate_params={"camera_id_str": CameraId}
    )
    def get_camera_thumbnail(camera_id: CameraId) -> FlaskResponse:
        """Proxy camera thumbnail with authentication or get timestamp.

        Args:
            camera_id: Validated CameraId object

        Query Parameters:
            timestamp: If 'true', return timestamp instead of image

        Returns:
            Flask Response with image data, timestamp JSON, or error message
        """
        # Check if timestamp is requested
        if request.args.get("timestamp") == "true":
            camera = find_camera_by_id(camera_id)
            if camera is None:
                raise ValidationError(Config.ErrorMessages.CAMERA_NOT_FOUND, 404)

            thumbnail_url = getattr(camera, "thumbnail", None)
            timestamp = (
                extract_thumbnail_timestamp(thumbnail_url) if thumbnail_url else None
            )
            logger.info(
                f"Camera {camera_id} thumbnail timestamp: {timestamp}, URL: {thumbnail_url}"
            )
            response, _ = create_api_response(
                success=True, data={"timestamp": timestamp}
            )
            return jsonify(response)

        # Import locally to avoid circular imports

        from blinkapp import (
            THUMBNAIL_CACHE_DIR,
        )
        from blinkapp.services.blink_service import ensure_blink_connection_initialized
        from blinkapp.services.cache_service import (
            ensure_cache_paths_initialized,
            ensure_thumbnail_cache_initialized,
        )

        # Ensure required components are initialized
        ensure_cache_paths_initialized()
        blink_connection = ensure_blink_connection_initialized()
        thumbnail_cache = ensure_thumbnail_cache_initialized()

        # THUMBNAIL_CACHE_DIR is guaranteed to be not None after ensure_cache_paths_initialized()
        assert THUMBNAIL_CACHE_DIR is not None

        # camera_id is now validated and converted by the decorator

        camera = find_camera_by_id(camera_id)
        if camera is None or camera.thumbnail is None:
            raise ValidationError(Config.ErrorMessages.CAMERA_THUMBNAIL_NOT_FOUND, 404)

        # Check cache first
        cached_info = thumbnail_cache.get(camera_id)
        current_ts = extract_thumbnail_timestamp(camera.thumbnail)
        cached_ts = 0  # Default value

        if cached_info is not None:
            cached_ts = int(cached_info.get("timestamp", 0))
            cached_filename = cached_info.get("filename")

            # Check if cached version is current
            if current_ts <= cached_ts and cached_filename is not None:
                assert THUMBNAIL_CACHE_DIR is not None
                cached_file = Path(cast(str, THUMBNAIL_CACHE_DIR)) / str(
                    cached_filename
                )
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
        update_camera_thumbnail(camera, camera_id, current_ts, cached_ts)

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
