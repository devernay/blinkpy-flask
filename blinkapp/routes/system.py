"""System management routes for the Blink Flask application."""

from typing import TYPE_CHECKING

from flask import Flask
import flask

if TYPE_CHECKING:
    pass

from blinkapp.models.ids import NetworkId
from blinkapp.models.types import JsonDict
from blinkapp.utils.decorators import ensure_blink_available
from blinkapp.utils.route_decorators import (
    api_route,
    api_route_with_validation,
    simple_success_response,
)
from blinkapp.utils.validation_helpers import validate_network_id


def setup_system_routes(app: Flask) -> None:
    """Set up system management routes.

    Args:
        app: Flask application instance to register routes with.
    """

    @app.route("/api/systems")
    @ensure_blink_available
    @api_route("get systems")
    def get_systems_route() -> JsonDict:
        """Get systems route - thin wrapper around connexion handler."""
        from ..connexion_handlers.system import get_systems

        return get_systems()

    @app.route("/api/systems/<network_id>")
    @ensure_blink_available
    @api_route_with_validation(
        "get system details", validate_params={"network_id": validate_network_id}
    )
    def get_system_details_route(
        network_id: NetworkId,
    ) -> JsonDict | tuple[JsonDict, int]:
        """Get system details route - thin wrapper around connexion handler."""
        from ..connexion_handlers.system import get_system_details

        return get_system_details(str(network_id))

    @app.route("/api/systems/<network_id>", methods=["PUT"])
    @ensure_blink_available
    @api_route_with_validation(
        "update system", validate_params={"network_id": validate_network_id}
    )
    def update_system_settings_route(
        network_id: NetworkId,
    ) -> JsonDict | tuple[JsonDict, int]:
        """Update system route - thin wrapper around connexion handler."""
        from ..connexion_handlers.system import update_system_settings

        body = flask.request.get_json() or {}
        return update_system_settings(str(network_id), body)

    @app.route("/api/systems/<network_id>/devices")
    @ensure_blink_available
    @api_route_with_validation(
        "get system devices", validate_params={"network_id": validate_network_id}
    )
    def get_system_devices_route(
        network_id: NetworkId,
    ) -> JsonDict | tuple[JsonDict, int]:
        """Get system devices route - thin wrapper around connexion handler."""
        from ..connexion_handlers.system import get_system_devices

        return get_system_devices(str(network_id))

    @app.route("/api/systems/cache", methods=["DELETE"])
    @ensure_blink_available
    @simple_success_response("clear systems cache")
    def clear_systems_cache_route() -> JsonDict:
        """Clear systems cache route - thin wrapper around connexion handler."""
        from ..connexion_handlers.system import clear_systems_cache

        return clear_systems_cache()
