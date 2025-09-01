"""Configuration routes for Blink Camera Flask application.

This module handles application configuration endpoints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from blinkapp.models.types import JsonDict
from blinkapp.utils.route_decorators import api_route

if TYPE_CHECKING:
    from flask import Flask

    from blinkapp.models.types import JsonDict

__all__ = ["setup_config_routes"]


def setup_config_routes(app: Flask) -> None:
    """Register configuration routes with the Flask app."""

    @app.route("/api/config")
    @api_route("get config")
    def get_config_route() -> JsonDict:
        """Get application configuration.

        Returns:
            JSON response with configuration data
        """
        from blinkapp.config import Config

        return {
            "version": "1.0.0",
            "features": {
                "live_streaming": True,
                "clip_management": True,
                "thumbnail_caching": True,
                "settings_persistence": True,
            },
            "limits": {
                "max_clip_cache_size": Config.CLIPS_CACHE_SIZE,
                "thumbnail_cache_max_age": 300,  # 5 minutes
                "api_timeout": 30,
            },
            "supported_formats": {
                "video": ["mp4"],
                "image": ["jpg", "jpeg"],
                "streaming": ["hls", "m3u8"],
            },
        }
