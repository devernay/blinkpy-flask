"""Settings management routes for the Blink Flask application."""

import json
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request
from flask.typing import (
    ResponseReturnValue,  # pyright: ignore[reportUnknownVariableType]
)
from flask.wrappers import Request

from blinkapp.config import Config
from blinkapp.models.responses import create_api_response
from blinkapp.models.types import JsonDict
from blinkapp.utils.decorators import api_route, method_dispatch_route

# Explicitly define what this module exports
__all__ = [
    "setup_settings_routes",
]


def setup_settings_routes(app: Flask) -> None:
    """Set up settings management routes."""

    @app.route("/api/settings", methods=["GET", "PUT"])
    @method_dispatch_route("settings")
    def settings() -> ResponseReturnValue:  # pyright: ignore[reportUnknownParameterType]
        """Get or save application settings.

        GET: Returns current user settings (temperature units, clip retention, etc.)
        PUT: Updates settings with provided JSON data

        Settings are persisted to cache/settings.json and survive logout/restart.
        """
        from blinkapp import SETTINGS_FILE

        if request.method == "GET":
            # Load existing settings from file
            assert SETTINGS_FILE is not None
            settings_file = Path(SETTINGS_FILE)

            if settings_file.exists():
                # Read saved settings from JSON file
                with open(settings_file) as f:
                    settings_data = json.load(f)
            else:
                # Return default settings if no file exists
                settings_data = {
                    "temperatureUnits": "celsius",
                    "cloudClipRetention": "30",
                    "localClipRetention": "never",
                    "clipThumbnailSize": "medium",
                }

            response, status_code = create_api_response(
                success=True, data=settings_data
            )
            return jsonify(response), status_code

        else:  # PUT - Save new settings
            # Validate incoming JSON data
            assert isinstance(request, Request)
            data: dict[str, Any] | None = request.get_json()  # pyright: ignore[reportAttributeAccessIssue]
            if data is None or not isinstance(data, dict):
                response, status_code = create_api_response(
                    success=False,
                    error=Config.ErrorMessages.INVALID_JSON_DATA,
                    status_code=400,
                )
                return jsonify(response), status_code

            # Validate input length and content
            for key, value in data.items():
                if isinstance(value, str):
                    # Check for overly long input (max 1000 chars)
                    if len(value) > 1000:
                        response, status_code = create_api_response(
                            success=False,
                            error=f"Input too long for field '{key}' (max 1000 characters)",
                            status_code=400,
                        )
                        return jsonify(response), status_code

                    # Check for potentially malicious content
                    malicious_patterns = [
                        "<script",
                        "javascript:",
                        "onerror=",
                        "DROP TABLE",
                        "SELECT *",
                    ]
                    if any(
                        pattern.lower() in value.lower()
                        for pattern in malicious_patterns
                    ):
                        response, status_code = create_api_response(
                            success=False,
                            error=f"Invalid content in field '{key}'",
                            status_code=400,
                        )
                        return jsonify(response), status_code

            # Load existing settings to merge with new data
            assert SETTINGS_FILE is not None
            settings_file = Path(SETTINGS_FILE)

            if settings_file.exists():
                # Load current settings from file
                with open(settings_file) as f:
                    settings_data = json.load(f)
            else:
                # Start with empty settings if no file exists
                settings_data = {}

            # Merge new settings with existing ones
            settings_data.update(data)

            # Persist updated settings to file
            with open(settings_file, "w") as f:
                json.dump(settings_data, f, indent=2)

            response, status_code = create_api_response(
                success=True, data={"message": "Settings saved"}
            )
            return jsonify(response), status_code


def register_settings_routes(app: Flask) -> None:
    """Register settings routes with the Flask app."""

    @app.route("/api/config")
    @api_route("get config")
    def get_config() -> JsonDict:
        """Get client-side configuration constants."""
        from blinkapp.config import Config

        config_data: dict[str, Any] = {
            "hls_stream_check_interval": Config.HLS_STREAM_CHECK_INTERVAL,
            "hls_stream_check_delay": Config.HLS_STREAM_CHECK_DELAY,
            "hls_stream_max_attempts": Config.HLS_STREAM_MAX_ATTEMPTS,
            "thumbnail_update_poll_interval": Config.THUMBNAIL_UPDATE_POLL_INTERVAL,
            "thumbnail_success_display_time": Config.THUMBNAIL_SUCCESS_DISPLAY_TIME,
            "thumbnail_processing_display_time": Config.THUMBNAIL_PROCESSING_DISPLAY_TIME,
            "clip_thumbnail_check_interval": Config.CLIP_THUMBNAIL_CHECK_INTERVAL,
            "clip_thumbnail_poll_max_attempts": Config.CLIP_THUMBNAIL_POLL_MAX_ATTEMPTS,
            "thumbnail_error_display_time": Config.THUMBNAIL_ERROR_DISPLAY_TIME,
            "milliseconds_to_seconds": Config.MILLISECONDS_TO_SECONDS,
            "error_messages": {
                "live_stream_failed": "Unable to start live video. Please check your camera connection and try again.",
                "live_stream_connection_failed": "Unable to start live video. Please check your internet connection and try again.",
                "live_view_failed": "Unable to start live view. Please check that your camera is online and try again.",
                "connection_error": "Unable to connect. Please check your internet connection and try again.",
                "arm_state_failed": "Unable to change system status. Please check your connection and try again.",
                "clip_download_failed": "Unable to download video. Please try again later.",
                "clip_play_failed": "Unable to play video. Please check your connection and try again.",
                "cache_clear_success": "Cache cleared successfully! Your storage space has been freed up.",
                "cache_clear_failed": "Unable to clear cache. Please check your connection and try again.",
                "logout_failed": "Unable to log out. Please try again.",
                "clips_updated": "All your local video clips are already up to date!",
                "feature_coming_soon": "This feature is coming soon! We're working hard to bring it to you.",
            },
        }
        return config_data
