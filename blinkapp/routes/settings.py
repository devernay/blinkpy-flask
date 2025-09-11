"""Settings routes for Blink Camera Flask application."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from flask import request

from ..models.types import JsonDict
from ..utils.decorators import ensure_blink_available
from ..utils.route_decorators import api_route

if TYPE_CHECKING:
    from flask import Flask


def setup_settings_routes(app: Flask) -> None:
    """Register settings routes with the Flask app.

    Args:
        app: Flask application instance to register routes with.
    """

    @app.route("/api/config")
    @ensure_blink_available
    @api_route("get app config")
    def get_app_config_route() -> JsonDict:
        """Get config route - retrieves application configuration settings.

        Returns:
            JsonDict: Application configuration data.
        """
        from ..connexion_handlers.settings import get_app_config

        return get_app_config()

    @app.route("/api/settings")
    @ensure_blink_available
    @api_route("get user settings")
    def get_user_settings_route() -> JsonDict:
        """Get settings route - retrieves user preference settings.

        Returns:
            JsonDict: User settings data including preferences and configurations.
        """
        from ..connexion_handlers.settings import get_user_settings

        return get_user_settings()

    @app.route("/api/settings", methods=["PUT"])
    @ensure_blink_available
    @api_route("update user settings")
    def update_user_settings_route() -> JsonDict | tuple[JsonDict, int]:
        """Update settings route - saves user preference settings.

        Returns:
            JsonDict | tuple[JsonDict, int]: Success response or error response with status code.
        """
        from ..connexion_handlers.settings import update_user_settings

        # Get JSON body with proper type narrowing
        # NOTE: pyright doesn't recognize Flask's request.get_json() method properly
        # This is a known Flask typing limitation, method exists and works at runtime
        body_raw: Any = request.get_json()  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]
        if body_raw is None:
            body_raw = {}
        # Type narrowing: ensure we have a dict
        if not isinstance(body_raw, dict):
            body_raw = {}
        body: JsonDict = body_raw
        return update_user_settings(body)
