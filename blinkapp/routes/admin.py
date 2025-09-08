"""Admin routes for Blink Camera Flask application."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models.types import JsonDict
from ..utils.decorators import ensure_blink_available
from ..utils.route_decorators import simple_success_response

if TYPE_CHECKING:
    from flask import Flask


def setup_admin_routes(app: Flask) -> None:
    """Set up admin routes with the Flask app."""

    @app.route("/api/cache", methods=["DELETE"])
    @ensure_blink_available
    @simple_success_response("clear all caches")
    def clear_all_caches_route() -> JsonDict:
        """Clear all caches route - thin wrapper around connexion handler."""
        from ..connexion_handlers.admin import clear_all_caches

        return clear_all_caches()

    @app.route("/api/cache/thumbnails", methods=["DELETE"])
    @ensure_blink_available
    @simple_success_response("clear thumbnail cache")
    def clear_thumbnail_cache_route() -> JsonDict:
        """Clear thumbnail cache route - thin wrapper around connexion handler."""
        from ..connexion_handlers.admin import clear_thumbnail_cache

        return clear_thumbnail_cache()

    @app.route("/api/cache/clips", methods=["DELETE"])
    @ensure_blink_available
    @simple_success_response("clear clips cache")
    def clear_clips_cache_route() -> JsonDict:
        """Clear clips cache route - thin wrapper around connexion handler."""
        from ..connexion_handlers.admin import clear_clips_cache

        return clear_clips_cache()
