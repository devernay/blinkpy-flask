"""Thumbnail routes for Blink Camera Flask application.

This module handles thumbnail-related operations including:
- Camera thumbnail management and caching
- Clip thumbnail generation and serving
"""

from __future__ import annotations

__all__ = [
    "update_camera_thumbnail",
    "setup_camera_thumbnail_routes",
    "require_camera",
    "logger",
]

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from flask import Response, jsonify, request

from blinkapp.config import Config
from blinkapp.models.ids import CameraId
from blinkapp.models.types import JsonDict
from blinkapp.utils.decorators import ensure_blink_available, error_context
from blinkapp.utils.errors import CameraError, ValidationError
from blinkapp.utils.parsers import extract_thumbnail_timestamp
from blinkapp.utils.route_decorators import api_route_with_validation

if TYPE_CHECKING:
    from blinkpy.camera import BlinkCamera
    from flask import Flask

    from blinkapp.models.types import FlaskResponse, JsonDict

from blinkapp.services.camera_service import require_camera

logger = logging.getLogger(__name__)


def update_camera_thumbnail(
    camera: BlinkCamera, cache_key: CameraId, current_ts: int, cached_ts: int
) -> None:
    """Update camera thumbnail in background if needed.

    Compares timestamps and triggers a background thumbnail update if the
    camera has a newer thumbnail available. This prevents blocking the
    API response while ensuring thumbnails stay current.

    Args:
        camera: Camera object from blinkpy library
        cache_key: Validated camera ID for cache operations
        current_ts: Current thumbnail timestamp from camera API
        cached_ts: Previously cached thumbnail timestamp
    """
    # Import locally to avoid circular imports during module initialization
    from blinkapp import THUMBNAIL_CACHE_DIR
    from blinkapp.services.blink_service import ensure_blink_connection_initialized
    from blinkapp.services.cache_service import (
        ensure_cache_paths_initialized,
        ensure_camera_thumbnail_cache_initialized,
    )
    from blinkapp.services.connection_service import ensure_executor_initialized

    # Ensure all required components are initialized
    ensure_cache_paths_initialized()
    blink_connection = ensure_blink_connection_initialized()
    executor = ensure_executor_initialized()
    camera_thumbnail_cache = ensure_camera_thumbnail_cache_initialized()

    # THUMBNAIL_CACHE_DIR is guaranteed to be not None after ensure_cache_paths_initialized()
    assert THUMBNAIL_CACHE_DIR is not None

    # Skip update if cached version is already current or newer
    if current_ts <= cached_ts:
        return

    logger.debug(
        f"Updating thumbnail cache for {camera.name} (ts: {current_ts} > {cached_ts})"
    )

    def update_thumbnail() -> None:
        """Background task to download and cache new thumbnail."""
        # Double-check timestamp to prevent race condition with concurrent requests
        current_entry = camera_thumbnail_cache.get(cache_key)
        current_cached_ts = (
            int(current_entry.get("timestamp", 0)) if current_entry else 0
        )
        if current_ts <= current_cached_ts:
            logger.debug(f"Thumbnail already updated for {camera.name}, skipping")
            return

        # Clean up old cached file to prevent disk space accumulation
        old_entry = camera_thumbnail_cache.get(cache_key)
        if old_entry is not None:
            old_filename = old_entry.get("filename")
            if old_filename is not None:
                assert THUMBNAIL_CACHE_DIR is not None
                old_filepath = Path(THUMBNAIL_CACHE_DIR) / old_filename
                try:
                    if old_filepath.exists():
                        old_filepath.unlink()
                        logger.debug(f"Removed old thumbnail file: {old_filename}")
                except OSError as e:
                    logger.debug(f"Could not remove old thumbnail: {e}")

        thumbnail_response = blink_connection.execute(camera.get_thumbnail())
        if (
            thumbnail_response is not None
            and thumbnail_response.status == Config.HTTP_STATUS_OK
        ):
            image_data = blink_connection.execute(thumbnail_response.read())

            # Save to file with new timestamp
            filename = f"{cache_key}_{current_ts}.jpg"
            assert THUMBNAIL_CACHE_DIR is not None
            filepath = Path(THUMBNAIL_CACHE_DIR) / filename
            try:
                filepath.write_bytes(image_data)
                # Update cache info atomically
                from blinkapp.models.cache import CameraThumbnailCacheEntry

                camera_thumbnail_cache[cache_key] = CameraThumbnailCacheEntry(
                    timestamp=current_ts,
                    filename=filename,
                )
                logger.debug(
                    f"Cached thumbnail for {camera.name} with timestamp {current_ts}"
                )
            except OSError as e:
                logger.error(f"Failed to save thumbnail for {camera.name}: {e}")
        else:
            logger.warning(f"Failed to fetch thumbnail for {camera.name}")

    executor.submit(update_thumbnail)


def setup_camera_thumbnail_routes(app: Flask) -> None:
    """Register thumbnail routes with the Flask app."""

    @app.route("/api/cameras/<camera_id_str>/thumbnail", methods=["DELETE"])
    @ensure_blink_available
    @api_route_with_validation(
        "clear camera thumbnail cache", validate_params={"camera_id_str": CameraId}
    )
    def clear_camera_camera_thumbnail_cache(camera_id: CameraId) -> JsonDict:
        """Clear camera thumbnail cache and refresh.

        Args:
            camera_id: Validated camera ID

        Returns:
            JSON response confirming cache clear
        """
        # Import locally to avoid circular imports
        from blinkapp import (
            THUMBNAIL_CACHE_DIR,
        )
        from blinkapp.services.blink_service import (
            ensure_blink_connection_initialized,
        )
        from blinkapp.services.cache_service import (
            ensure_cache_paths_initialized,
            ensure_camera_thumbnail_cache_initialized,
        )
        from blinkapp.services.connection_service import ensure_executor_initialized

        ensure_cache_paths_initialized()
        blink_connection = ensure_blink_connection_initialized()
        executor = ensure_executor_initialized()
        camera_thumbnail_cache = ensure_camera_thumbnail_cache_initialized()
        ensure_cache_paths_initialized()

        # THUMBNAIL_CACHE_DIR is guaranteed to be not None after ensure_cache_paths_initialized()
        assert THUMBNAIL_CACHE_DIR is not None

        camera, error_response = require_camera(camera_id)
        if error_response is not None:
            error_dict, status_code = error_response
            return error_dict

        assert camera is not None
        with error_context("refresh camera thumbnail", CameraError):
            # Remove camera thumbnail from cache in background
            def remove_camera_thumbnail_cache() -> None:
                """Remove cached thumbnail file and cache entry."""
                cached_info = camera_thumbnail_cache.get(camera_id)
                if cached_info is not None:
                    # Remove cached file
                    if "filename" in cached_info:
                        assert THUMBNAIL_CACHE_DIR is not None
                        cached_file = Path(THUMBNAIL_CACHE_DIR) / str(
                            cached_info["filename"]
                        )
                        try:
                            if cached_file.exists():
                                cached_file.unlink()
                        except OSError as e:
                            logger.debug(f"Could not remove cached thumbnail: {e}")
                    # Remove from cache
                    camera_thumbnail_cache.pop(camera_id, {})

            executor.submit(remove_camera_thumbnail_cache)

            # Trigger thumbnail update
            blink_connection.execute(camera.snap_picture())  # type: ignore[attr-defined]

            return {"success": True, "message": "Camera thumbnail refresh initiated"}

    @app.route("/api/cameras/<camera_id_str>/thumbnail")
    @ensure_blink_available
    @api_route_with_validation(
        "get camera thumbnail", validate_params={"camera_id_str": CameraId}
    )
    def get_camera_thumbnail(camera_id: CameraId) -> FlaskResponse:
        """Proxy camera thumbnail with authentication or get timestamp.

        Args:
            camera_id: Validated camera ID

        Returns:
            Image data or JSON with timestamp
        """

        from blinkapp.services.camera_service import find_camera_by_id

        # Check if timestamp query parameter is present
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
            from blinkapp.models.responses import create_api_response

            response, _ = create_api_response(
                success=True, data={"timestamp": timestamp, "url": thumbnail_url}
            )
            return jsonify(response)

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
            ensure_camera_thumbnail_cache_initialized,
        )

        ensure_cache_paths_initialized()
        blink_connection = ensure_blink_connection_initialized()
        camera_thumbnail_cache = ensure_camera_thumbnail_cache_initialized()

        # THUMBNAIL_CACHE_DIR is guaranteed to be not None after ensure_cache_paths_initialized()
        assert THUMBNAIL_CACHE_DIR is not None

        # Check if Blink is available first - if not, return 500
        try:
            blink = ensure_blink_initialized()
            if not blink.available:
                raise RuntimeError("Blink system not available")
        except RuntimeError:
            raise ValidationError("Blink system not available", 500) from None

        camera = find_camera_by_id(camera_id)
        if camera is None or camera.thumbnail is None:
            raise ValidationError(Config.ErrorMessages.CAMERA_THUMBNAIL_NOT_FOUND, 404)

        # Check cache first
        cached_info = camera_thumbnail_cache.get(camera_id)
        current_ts = extract_thumbnail_timestamp(camera.thumbnail)
        cached_ts = 0  # Default value

        if cached_info is not None:
            cached_ts = int(cached_info.get("timestamp", 0))
            cached_filename = cached_info.get("filename")

            # Check if cached version is current
            if current_ts <= cached_ts and cached_filename is not None:
                assert THUMBNAIL_CACHE_DIR is not None
                cached_file = Path(THUMBNAIL_CACHE_DIR) / str(cached_filename)
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
        thumbnail_response = blink_connection.execute(camera.get_thumbnail())
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
