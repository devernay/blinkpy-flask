"""Settings management routes for the Blink Flask application."""

import json
from pathlib import Path
from typing import cast

from flask import jsonify, request
from flask.typing import ResponseReturnValue

from blinkapp.models.responses import create_api_response
from config import Config
from route_decorators import method_dispatch_route

# Explicitly define what this module exports
__all__ = [
    "setup_settings_routes",
]


def setup_settings_routes(app):
    """Set up settings management routes."""

    @app.route("/api/settings", methods=["GET", "PUT"])
    @method_dispatch_route("settings")
    def settings() -> ResponseReturnValue:
        """Get or save application settings.

        GET: Returns current user settings (temperature units, clip retention, etc.)
        PUT: Updates settings with provided JSON data

        Settings are persisted to cache/settings.json and survive logout/restart.
        """
        from blinkapp import SETTINGS_FILE

        if request.method == "GET":
            # Load existing settings from file
            assert SETTINGS_FILE is not None
            settings_file = Path(cast(str, SETTINGS_FILE))

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
            data = request.get_json()
            if not isinstance(data, dict):
                response, status_code = create_api_response(
                    success=False,
                    error=Config.ErrorMessages.INVALID_JSON_DATA,
                    status_code=400,
                )
                return jsonify(response), status_code

            # Load existing settings to merge with new data
            assert SETTINGS_FILE is not None
            settings_file = Path(cast(str, SETTINGS_FILE))

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
