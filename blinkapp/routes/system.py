"""System management routes for the Blink Flask application."""

from typing import Any

from flask import Flask, request
from flask.wrappers import Request

from blinkapp.connexion_handlers.system import (
    clear_systems_cache_route as connexion_clear_cache,
)
from blinkapp.connexion_handlers.system import (
    get_devices_route as connexion_get_devices,
)
from blinkapp.connexion_handlers.system import (
    get_system_devices_route as connexion_get_system_devices,
)
from blinkapp.connexion_handlers.system import (
    get_systems_route as connexion_get_systems,
)
from blinkapp.connexion_handlers.system import (
    update_system_route as connexion_update_system,
)
from blinkapp.models.ids import NetworkId
from blinkapp.models.types import JsonDict
from blinkapp.utils.decorators import (
    ensure_blink_available,
)
from blinkapp.utils.route_decorators import (
    api_route,
    api_route_with_validation,
    simple_success_response,
)

# Explicitly define what this module exports
__all__ = [
    "setup_system_routes",
]


def setup_system_routes(app: Flask) -> None:
    """Set up system management routes."""

    @app.route("/api/systems")
    @ensure_blink_available
    @api_route("get systems")
    def get_systems_route() -> JsonDict:
        """Get list of available Blink systems.

        Retrieves all configured Blink sync modules and their associated
        network information. Each system represents a separate Blink hub
        with its own set of cameras.

        Returns:
            JSON response with list of systems or error message
        """
        return connexion_get_systems()

    @app.route("/api/systems/<network_id_str>")
    @ensure_blink_available
    @api_route_with_validation(
        "get system details",
        validate_params={"network_id_str": NetworkId},
    )
    def get_system_devices_route(network_id: NetworkId) -> JsonDict:
        """Get devices for a specific Blink system.

        Args:
            network_id: Network ID of the system to retrieve devices for

        Returns:
            JSON response with devices list or error message
        """
        result = connexion_get_system_devices(str(network_id))
        if isinstance(result, tuple):
            return result[0]  # Return just the dict part for Flask
        return result

    @app.route("/api/systems/<network_id_str>/devices")
    @ensure_blink_available
    @api_route_with_validation(
        "get devices", validate_params={"network_id_str": NetworkId}
    )
    def get_devices_route(network_id: NetworkId) -> JsonDict:
        """Get devices for a specific Blink system.

        Args:
            network_id: Validated NetworkId object

        Returns:
            JSON response with list of devices or error message
        """
        result = connexion_get_devices(str(network_id))
        if isinstance(result, tuple):
            return result[0]  # Return just the dict part for Flask
        return result

    @app.route("/api/systems/<network_id_str>", methods=["PUT"])
    @ensure_blink_available
    @api_route_with_validation(
        "update system",
        validate_params={"network_id_str": NetworkId},
        validate_json=True,
        required_fields=["armed"],
    )
    def update_system_route(network_id: NetworkId) -> JsonDict:
        """Update a Blink system (arm/disarm).

        Args:
            network_id: Validated NetworkId object

        Returns:
            JSON response with success status or error message
        """
        assert isinstance(request, Request)
        data: dict[str, Any] | None = request.get_json()  # pyright: ignore[reportAttributeAccessIssue]
        if data is None:
            data = {}
        result = connexion_update_system(str(network_id), data)
        if isinstance(result, tuple):
            return result[0]  # Return just the dict part for Flask
        return result

    @app.route("/api/systems/cache", methods=["DELETE"])
    @ensure_blink_available
    @simple_success_response("Systems cache cleared")
    def clear_systems_cache_route() -> JsonDict:
        """Clear systems cache.

        Returns:
            JSON response with success status or error message
        """
        return connexion_clear_cache()
