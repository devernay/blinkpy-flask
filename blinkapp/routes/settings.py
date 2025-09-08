"""Settings routes for Blink Camera Flask application."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import request

from ..models.types import JsonDict
from ..utils.decorators import ensure_blink_available
from ..utils.route_decorators import api_route

if TYPE_CHECKING:
    from flask import Flask


def setup_settings_routes(app: Flask) -> None:
    """Register settings routes with the Flask app."""

    @app.route("/api/config")
    @ensure_blink_available
    @api_route("get app config")
    def get_app_config_route() -> JsonDict:
        """Get config route - thin wrapper around connexion handler."""
        from ..connexion_handlers.settings import get_app_config

        return get_app_config()

    @app.route("/api/settings")
    @ensure_blink_available
    @api_route("get user settings")
    def get_user_settings_route() -> JsonDict:
        """Get settings route - thin wrapper around connexion handler."""
        from ..connexion_handlers.settings import get_user_settings

        return get_user_settings()

    @app.route("/api/settings", methods=["PUT"])
    @ensure_blink_available
    @api_route("update user settings")
    def update_user_settings_route() -> JsonDict | tuple[JsonDict, int]:
        """Update settings route - thin wrapper around connexion handler."""
        from ..connexion_handlers.settings import update_user_settings

        # Flask 3.x get_json() - use getattr to bypass pyright LocalProxy limitation
        body = getattr(request, 'get_json')() or {}
        return update_user_settings(body)
