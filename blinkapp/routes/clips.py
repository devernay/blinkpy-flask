"""Clip management routes for the Blink Flask application."""

from flask import Flask, Response, request

from blinkapp.models.ids import ClipId
from blinkapp.models.types import ClipsResponse, JsonDict
from blinkapp.utils.decorators import ensure_blink_available
from blinkapp.utils.route_decorators import api_route, api_route_with_validation
from blinkapp.utils.validation_helpers import validate_clip_id


def setup_clips_routes(app: Flask) -> None:
    """Set up clip management routes."""

    @app.route("/api/clips")
    @ensure_blink_available
    @api_route("get clips")
    def get_clips_route() -> ClipsResponse | tuple[JsonDict, int]:
        """Get clips route - thin wrapper around connexion handler."""
        from ..connexion_handlers.clips import get_clips

        storage_type = request.args.get("storage")
        return get_clips(storage_type)

    @app.route("/api/clips/<clip_id_str>", methods=["DELETE"])
    @ensure_blink_available
    @api_route_with_validation("delete clip", validate_params={"clip_id_str": validate_clip_id})
    def delete_clip_route(clip_id: ClipId) -> JsonDict | tuple[JsonDict, int]:
        """Delete clip route - thin wrapper around connexion handler."""
        from ..connexion_handlers.clips import delete_clip

        return delete_clip(str(clip_id))

    @app.route("/api/clips/<clip_id_str>/download")
    @ensure_blink_available
    @api_route_with_validation("download clip", validate_params={"clip_id_str": validate_clip_id})
    def download_clip_route(clip_id: ClipId) -> Response | tuple[JsonDict, int]:
        """Download clip route - thin wrapper around connexion handler."""
        from ..connexion_handlers.clips import download_clip

        return download_clip(str(clip_id))

    @app.route("/api/clips/<clip_id_str>/thumbnail")
    @ensure_blink_available
    @api_route_with_validation(
        "get clip thumbnail", validate_params={"clip_id_str": validate_clip_id}
    )
    def get_clip_thumbnail_route(
        clip_id: ClipId,
    ) -> Response | JsonDict | tuple[JsonDict, int]:
        """Get clip thumbnail route - thin wrapper around connexion handler."""
        from ..connexion_handlers.clips import get_clip_thumbnail

        check = request.args.get("check", "").lower() == "true"
        return get_clip_thumbnail(str(clip_id), check)

    @app.route("/api/clips/<clip_id_str>/thumbnail", methods=["POST"])
    @ensure_blink_available
    @api_route_with_validation(
        "generate clip thumbnail", validate_params={"clip_id_str": validate_clip_id}
    )
    def generate_clip_thumbnail_route(
        clip_id: ClipId,
    ) -> JsonDict | tuple[JsonDict, int]:
        """Generate clip thumbnail route - thin wrapper around connexion handler."""
        from ..connexion_handlers.clips import generate_clip_thumbnail

        return generate_clip_thumbnail(str(clip_id))
