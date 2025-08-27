"""
Administrative routes for the Blink Camera Flask application.

This module handles administrative functionality including:
- Cache management and clearing
- System maintenance operations
- Placeholder/development routes
"""

from flask import Flask, Response, jsonify

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
        # Submit cache clearing task to background executor
        from blinkapp.services.connection_service import ensure_executor_initialized

        def clear_all_caches() -> dict[str, object]:
            """Clear all caches except credentials (background operation)."""
            from blinkapp.services.cache_service import (
                clips_cache,
                thumbnail_cache,
            )

            results: dict[str, object] = {}

            # Clear in-memory caches
            if clips_cache is not None:
                clips_cache.clear()
            if thumbnail_cache is not None:
                thumbnail_cache.clear()
            results["memory_caches_cleared"] = True

            # Clear file caches in background
            try:
                # Import and call the clear_file_cache function from __init__
                import os
                from pathlib import Path

                from blinkapp.config import Config

                def clear_file_cache(cache_dir: str, cache_name: str) -> None:
                    """Clear files in a cache directory."""
                    if os.path.exists(cache_dir):
                        for file_path in Path(cache_dir).glob("*"):
                            if file_path.is_file():
                                file_path.unlink()

                # Clear thumbnail and clips caches
                clear_file_cache(
                    str(Path(Config.DEFAULT_CACHE_DIR) / Config.THUMBNAILS_SUBDIR),
                    "thumbnails",
                )
                clear_file_cache(
                    str(Path(Config.DEFAULT_CACHE_DIR) / Config.CLIPS_SUBDIR), "clips"
                )
                results["file_caches_cleared"] = True
            except Exception as e:
                results["file_cache_error"] = str(e)

            return results

        ensure_executor_initialized().submit(clear_all_caches)
        return {}  # Decorator will handle the actual response

    @app.route("/api/cache/thumbnails", methods=["DELETE"])
    @simple_success_response("Thumbnail cache cleared")
    def clear_thumbnail_cache() -> JsonDict:
        """Clear thumbnail cache only.

        Returns:
            JSON response with success status
        """
        from pathlib import Path

        from blinkapp.services.connection_service import ensure_executor_initialized

        def clear_thumbnails() -> None:
            import shutil

            from blinkapp import THUMBNAIL_CACHE_DIR

            cache_path = Path(THUMBNAIL_CACHE_DIR)
            if cache_path.exists():
                shutil.rmtree(cache_path)
                cache_path.mkdir(parents=True, exist_ok=True)

        ensure_executor_initialized().submit(clear_thumbnails)
        return {}

    @app.route("/api/cache/clips", methods=["DELETE"])
    @simple_success_response("Clips cache cleared")
    def clear_clips_cache() -> JsonDict:
        """Clear clips cache only.

        Returns:
            JSON response with success status
        """
        from pathlib import Path

        from blinkapp.services.connection_service import ensure_executor_initialized

        def clear_clips() -> None:
            import shutil

            from blinkapp import CLIPS_CACHE_DIR

            cache_path = Path(CLIPS_CACHE_DIR)
            if cache_path.exists():
                shutil.rmtree(cache_path)
                cache_path.mkdir(parents=True, exist_ok=True)

        ensure_executor_initialized().submit(clear_clips)
        return {}

    @app.route("/placeholder")
    @api_route("placeholder")
    def placeholder() -> tuple[Response, int]:
        """Show placeholder message.

        Returns:
            JSON response with placeholder message
        """
        from blinkapp import create_api_response
        from blinkapp.config import Config

        response, status_code = create_api_response(
            success=False,
            error=Config.ErrorMessages.FEATURE_NOT_AVAILABLE,
            status_code=Config.HTTP_STATUS_NOT_IMPLEMENTED,
        )
        return jsonify(response), status_code
