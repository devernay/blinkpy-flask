"""Clip management routes for the Blink Flask application."""

from flask import jsonify, request
from flask.typing import ResponseReturnValue

from app_types import JsonDict
from blinkapp.models.ids import ClipId
from blinkapp.utils.decorators import ensure_blink_available, error_context
from blinkapp.utils.errors import ValidationError
from config import Config
from route_decorators import (
    api_route,
    api_route_with_validation,
    file_response_route,
    simple_success_response,
)

# Explicitly define what this module exports
__all__ = [
    "setup_clips_routes",
]


def setup_clips_routes(app):
    """Set up clip management routes."""

    @app.route("/api/clips")
    @ensure_blink_available
    @api_route("get clips")
    def get_clips() -> JsonDict:
        """Get clips from cloud or local storage.

        Retrieves video clips from either Blink's cloud storage or local
        USB storage connected to sync modules. Results are cached and
        organized by date for efficient browsing.

        Query Parameters:
            storage: 'cloud' or 'local' (default: 'cloud')

        Returns:
            JSON response with list of clips organized by date
        """
        from blinkapp import (
            blink,
            blink_connection,
        )
        from blinkapp.services.clip_service import (
            process_cloud_clips,
            process_local_clips,
        )

        assert blink is not None
        storage_type = request.args.get("storage", "cloud")
        if storage_type not in ["cloud", "local"]:
            raise ValidationError(Config.ErrorMessages.INVALID_STORAGE_TYPE, 400)

        with error_context(f"get {storage_type} clips"):
            if storage_type == "cloud":
                # Get cloud clips via blink operation
                videos_metadata = blink_connection.execute(
                    blink.get_videos_metadata(stop=Config.CLIPS_PER_STORAGE_TYPE)
                )
                clips = process_cloud_clips(videos_metadata)
            else:
                clips = process_local_clips()

        return {"clips": clips}

    @app.route("/api/clip/<clip_id_str>/process", methods=["POST"])
    @ensure_blink_available
    @simple_success_response("Clip processing initiated")
    def process_clip(clip_id_str: str) -> JsonDict:
        """Process clip on server (download and generate thumbnail) without sending to client.

        Initiates background processing of clip for thumbnail generation.
        Used by "Update All" functionality to process clips sequentially.

        Args:
            clip_id_str: String representation of clip ID (cloud ID or local sync~item format)

        Returns:
            JSON response indicating processing has started
        """
        from blinkapp.services.clip_service import (
            process_cloud_clip_background,
            process_local_clip_background,
        )
        from blinkapp.utils.validators import parse_clip_id

        clip_id, error_response = parse_clip_id(clip_id_str)
        if error_response is not None:
            response, status_code = error_response
            return response  # Return just the dict, not the tuple

        assert clip_id is not None
        if clip_id.is_local():
            sync_name, item_id = clip_id.get_local_parts()
            process_local_clip_background(clip_id, sync_name, item_id)
        else:
            process_cloud_clip_background(clip_id)

        return {}  # Decorator will handle the success response

    @app.route("/api/clip/<clip_id_str>/download")
    @ensure_blink_available
    @api_route("download clip")
    def download_clip(clip_id_str: str) -> ResponseReturnValue:
        """Download a specific clip.

        Args:
            clip_id_str: String representation of clip ID

        Returns:
            Flask Response with clip file or error message
        """
        from blinkapp import (
            logger,
        )
        from blinkapp.services.clip_service import (
            download_cloud_clip,
            download_local_clip,
        )
        from blinkapp.utils.validators import parse_clip_id

        clip_id, error_response = parse_clip_id(clip_id_str)
        if error_response is not None:
            # Re-raise as exception to be handled by decorator
            raise ValueError(error_response[0]["error"])

        assert clip_id is not None
        logger.debug(
            f"Attempting to download clip with ID: {clip_id} (is_local: {clip_id.is_local()})"
        )
        if clip_id.is_local():
            sync_name, item_id = clip_id.get_local_parts()
            logger.debug(f"Local clip - sync_name: {sync_name}, item_id: {item_id}")
            return download_local_clip(clip_id, sync_name, item_id)
        else:
            logger.debug(f"Cloud clip - ID: {clip_id}")
            return download_cloud_clip(clip_id)

    @app.route("/api/clip/<clip_id_str>/thumbnail")
    @file_response_route("get clip thumbnail", validate_params={"clip_id_str": ClipId})
    def get_clip_thumbnail(clip_id: ClipId) -> ResponseReturnValue:
        """Serve clip thumbnail."""
        from blinkapp import send_file
        from blinkapp.services.cache_service import ensure_clips_cache_initialized

        clips_cache_instance = ensure_clips_cache_initialized()
        cached_clip = clips_cache_instance.get(clip_id)

        if cached_clip is not None:
            thumbnail_path = cached_clip.get("thumbnail")
            if thumbnail_path is not None and thumbnail_path.exists():
                return send_file(
                    str(thumbnail_path),
                    mimetype="image/jpeg",
                )

        # If no cached thumbnail, return 404
        return jsonify({"error": "Thumbnail not found"}), 404

    @app.route("/api/clip/<clip_id_str>/thumbnail/check")
    @api_route_with_validation(
        "check clip thumbnail", validate_params={"clip_id_str": ClipId}
    )
    def check_clip_thumbnail(clip_id: ClipId) -> JsonDict:
        """Check if thumbnail is available for clip.

        Args:
            clip_id: The clip ID to check

        Returns:
            JSON response indicating if thumbnail is available
        """
        from blinkapp.services.cache_service import ensure_clips_cache_initialized

        clips_cache_instance = ensure_clips_cache_initialized()
        cached_clip = clips_cache_instance.get(clip_id)
        if cached_clip is not None:
            thumbnail_path = cached_clip.get("thumbnail")
            if thumbnail_path is not None and thumbnail_path.exists():
                return {"available": True, "url": f"/api/clip/{clip_id}/thumbnail"}

        return {"available": False}
