"""
Administrative routes for the Blink Camera Flask application.

This module handles administrative functionality including:
- Cache management and clearing
- System maintenance operations
- Placeholder endpoints for future features
"""

from flask import Flask, jsonify

from blinkapp.config import Config
from blinkapp.models.responses import create_api_response
from blinkapp.models.types import JsonDict
from blinkapp.utils.route_decorators import api_route, simple_success_response

# Explicitly define what this module exports
__all__ = ["register_admin_routes"]


def register_admin_routes(app: Flask) -> None:
    """Register administrative routes with the Flask app."""

    @app.route("/api/cache", methods=["DELETE"])
    @simple_success_response("Cache clearing initiated")
    def clear_cache() -> JsonDict:
        """Clear all caches except credentials.

        Returns:
            JSON response with success status
        """
        from blinkapp.services.cache_service import clear_all_caches
        from blinkapp.services.connection_service import ensure_executor_initialized

        ensure_executor_initialized().submit(clear_all_caches)
        return {}  # Decorator will handle the actual response

    @app.route("/api/cache/thumbnails", methods=["DELETE"])
    @simple_success_response("Thumbnail cache cleared")
    def clear_thumbnail_cache() -> JsonDict:
        """Clear thumbnail cache only.

        Returns:
            JSON response with success status
        """
        from blinkapp.services.cache_service import clear_thumbnail_cache_files
        from blinkapp.services.connection_service import ensure_executor_initialized

        ensure_executor_initialized().submit(clear_thumbnail_cache_files)
        return {}

    @app.route("/api/cache/clips", methods=["DELETE"])
    @simple_success_response("Clips cache cleared")
    def clear_clips_cache() -> JsonDict:
        """Clear clips cache only.

        Returns:
            JSON response with success status
        """
        from blinkapp.services.cache_service import clear_clips_cache_files
        from blinkapp.services.connection_service import ensure_executor_initialized

        ensure_executor_initialized().submit(clear_clips_cache_files)
        return {}

    @app.route("/placeholder")
    @api_route("placeholder feature")
    def placeholder() -> tuple[object, int]:
        """Placeholder endpoint for future features.

        Returns:
            JSON response indicating feature is not yet implemented
        """
        response, status_code = create_api_response(
            success=False,
            error=Config.ErrorMessages.FEATURE_NOT_AVAILABLE,
            status_code=Config.HTTP_STATUS_NOT_IMPLEMENTED,
        )
        return jsonify(response), status_code
