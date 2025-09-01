"""Clip management routes for the Blink Flask application."""

from flask import Flask, jsonify, request
from flask.typing import (
    ResponseReturnValue,  # pyright: ignore[reportUnknownVariableType]
)

from blinkapp.connexion_handlers.clips import get_clips
from blinkapp.models.ids import ClipId
from blinkapp.models.responses import create_api_response
from blinkapp.models.types import ClipsResponse, JsonDict
from blinkapp.utils.decorators import (
    ensure_blink_available,
)
from blinkapp.utils.route_decorators import (
    api_route,
    api_route_with_validation,
    file_response_route,
    simple_success_response,
)

# Explicitly define what this module exports
__all__ = [
    "setup_clips_routes",
]


def setup_clips_routes(app: Flask) -> None:
    """Set up clip management routes."""

    @app.route("/api/clips")
    @ensure_blink_available
    @api_route("get clips")
    def get_clips_route() -> ClipsResponse | tuple[JsonDict, int]:
        """Get clips from cloud or local storage.

        Retrieves video clips from either Blink's cloud storage or local
        USB storage connected to sync modules. Results are cached and
        organized by date for efficient browsing.

        Query Parameters:
            storage: 'cloud' or 'local' (default: 'cloud')

        Returns:
            JSON response with list of clips organized by date
        """
        storage_type = request.args.get("storage")
        result = get_clips(storage_type)
        if isinstance(result, tuple):
            return result[0], result[1]  # Return dict and status code
        return result

    @app.route("/api/clips/<clip_id_str>/thumbnail", methods=["POST"])
    @ensure_blink_available
    @simple_success_response("Clip thumbnail generation initiated")
    def create_clip_thumbnail_route(clip_id_str: str) -> JsonDict:
        """Generate thumbnail for clip (download and process) without sending to client.

        Initiates background processing of clip for thumbnail generation.
        Used by "Update All" functionality to process clips sequentially.

        Args:
            clip_id_str: String representation of clip ID (cloud ID or local sync~item format)

        Returns:
            JSON response indicating processing has started
        """
        from blinkapp.services.clip_processing import (
            process_cloud_clip_thumbnail_only,
            process_local_clip_background,
        )
        from blinkapp.services.connection_service import ensure_executor_initialized
        from blinkapp.utils.parsers import parse_clip_id

        try:
            clip_id_parsed = parse_clip_id(clip_id_str)
        except ValueError as e:
            return {"success": False, "error": str(e)}

        # Convert to ClipId object
        from blinkapp.models.ids import ClipId

        clip_id = ClipId(clip_id_parsed)

        # Submit background processing
        executor = ensure_executor_initialized()

        if clip_id.is_local():
            sync_name, item_id = clip_id.get_local_parts()
            executor.submit(
                process_local_clip_background, clip_id, sync_name, str(item_id)
            )
        else:
            executor.submit(process_cloud_clip_thumbnail_only, clip_id)

        return {}  # Decorator will handle the success response

    @app.route("/api/clips/<clip_id_str>/download")
    @ensure_blink_available
    @api_route_with_validation("download clip", validate_params={"clip_id_str": ClipId})
    def download_clip_route(clip_id: ClipId) -> ResponseReturnValue:  # pyright: ignore[reportUnknownParameterType]
        """Download a specific clip.

        Args:
            clip_id: Validated clip ID

        Returns:
            Flask Response with clip file or error message
        """
        from blinkapp import logger
        from blinkapp.services.clip_download import (
            download_cloud_clip,
            download_local_clip,
        )
        from blinkapp.services.clip_processing import (
            process_cloud_clip_background,
            process_local_clip_background,
        )

        logger.debug(
            f"Attempting to download clip with ID: {clip_id} (is_local: {clip_id.is_local()})"
        )

        # Trigger background processing for thumbnail generation
        if clip_id.is_local():
            sync_name, item_id = clip_id.get_local_parts()
            logger.debug(f"Local clip - sync_name: {sync_name}, item_id: {item_id}")

            # Trigger background thumbnail generation
            process_local_clip_background(clip_id, sync_name, str(item_id))

            return download_local_clip(clip_id, sync_name, str(item_id))
        else:
            logger.debug(f"Cloud clip - ID: {clip_id}")

            # Trigger background processing for cloud clips too
            process_cloud_clip_background(clip_id)

            return download_cloud_clip(clip_id)

    @app.route("/api/clips/<clip_id_str>/thumbnail")
    @file_response_route("get clip thumbnail", validate_params={"clip_id_str": ClipId})
    def get_clip_thumbnail_route(clip_id: ClipId) -> ResponseReturnValue:  # pyright: ignore[reportUnknownParameterType]
        """Serve clip thumbnail or check availability.

        Query Parameters:
            check: If 'true', return availability status instead of image
        """
        from flask import redirect, send_file

        from blinkapp.services.cache_service import ensure_clips_cache_initialized

        clips_cache_instance = ensure_clips_cache_initialized()
        cached_clip = clips_cache_instance.get(clip_id)

        # Check if availability check is requested
        if request.args.get("check") == "true":
            if cached_clip is not None:
                # Check for local cached thumbnail first
                thumbnail_path = cached_clip.get("thumbnail")
                if thumbnail_path is not None and thumbnail_path.exists():
                    response, _ = create_api_response(
                        success=True, data={"available": True, "type": "local"}
                    )
                    return jsonify(response)

                # For cloud clips, check if we have cloud thumbnail URL
                if not clip_id.is_local():
                    cloud_thumbnail_url = cached_clip.get("cloud_thumbnail_url")
                    if cloud_thumbnail_url is not None:
                        response, _ = create_api_response(
                            success=True, data={"available": True, "type": "cloud"}
                        )
                        return jsonify(response)

            response, _ = create_api_response(success=True, data={"available": False})
            return jsonify(response)
        cached_clip = clips_cache_instance.get(clip_id)

        if cached_clip is not None:
            # Check for local cached thumbnail first
            thumbnail_path = cached_clip.get("thumbnail")
            if thumbnail_path is not None and thumbnail_path.exists():
                return send_file(
                    str(thumbnail_path),
                    mimetype="image/jpeg",
                )

            # For cloud clips, try to download and cache thumbnail
            if not clip_id.is_local():
                cloud_thumbnail_url = cached_clip.get("cloud_thumbnail_url")
                if cloud_thumbnail_url is not None:
                    # Try to download and cache the thumbnail
                    from blinkapp.services.clip_processing import (
                        download_and_cache_cloud_thumbnail,
                    )

                    thumbnail_path = download_and_cache_cloud_thumbnail(
                        clip_id, cloud_thumbnail_url
                    )
                    if thumbnail_path and thumbnail_path.exists():
                        return send_file(
                            str(thumbnail_path),
                            mimetype="image/jpeg",
                        )
                    # If download failed, redirect to original URL
                    return redirect(cloud_thumbnail_url)

        # If no cached thumbnail, return 404
        return jsonify({"error": "Thumbnail not found"}), 404

    @app.route("/api/clips/<clip_id_str>", methods=["DELETE"])
    @api_route_with_validation("delete clip", validate_params={"clip_id_str": ClipId})
    def delete_clip_route(clip_id: ClipId) -> JsonDict:
        """Delete a clip.

        Args:
            clip_id: The clip ID to delete

        Returns:
            JSON response indicating success or failure
        """
        from blinkapp.services.cache_service import ensure_clips_cache_initialized

        clips_cache_instance = ensure_clips_cache_initialized()
        cached_clip = clips_cache_instance.get(clip_id)

        if cached_clip is not None:
            # Remove cached files
            filepath = cached_clip.get("filepath")
            if filepath and filepath.exists():
                filepath.unlink()

            thumbnail_path = cached_clip.get("thumbnail")
            if thumbnail_path and thumbnail_path.exists():
                thumbnail_path.unlink()

            # Remove from cache
            del clips_cache_instance[clip_id]

            return {"deleted": True}

        return {"deleted": False, "error": "Clip not found"}
