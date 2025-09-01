"""Settings management routes for the Blink Flask application."""

import json
from pathlib import Path

from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue
from flask.wrappers import Request

from blinkapp.config import Config
from blinkapp.models.responses import create_api_response
from blinkapp.utils.decorators import ensure_blink_available
from blinkapp.utils.route_decorators import method_dispatch_route

# Explicitly define what this module exports
__all__ = [
    "setup_settings_routes",
]


def setup_settings_routes(app: Flask) -> None:
    """Set up settings management routes."""

    @app.route("/api/settings", methods=["GET", "PUT"])
    @ensure_blink_available
    @method_dispatch_route("settings")
    def settings_route() -> ResponseReturnValue:
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
                    "temperatureUnits": "C",
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
            # Flask's request.get_json() method exists but pyright doesn't recognize it on the Request type
            # This is a known issue with Flask type stubs - the method is dynamically added
            data: dict[str, object] | None = request.get_json()  # pyright: ignore[reportAttributeAccessIssue]
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
    setup_settings_routes(app)
