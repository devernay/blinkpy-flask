"""System management routes for the Blink Flask application."""

from typing import Any

from flask import Flask, request

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
        """Get systems route - retrieves all available Blink systems and their status.

        Returns:
            JsonDict: List of Blink systems with details and device counts.
        """
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
        """Get system details route - retrieves detailed information for a specific Blink system.

        Args:
            network_id: NetworkId object representing the system to get details for.

        Returns:
            JsonDict | tuple[JsonDict, int]: System details data or error response with status code.
        """
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
        """Update system route - modifies system settings like arm/disarm status.

        Args:
            network_id: NetworkId object representing the system to update.

        Returns:
            JsonDict | tuple[JsonDict, int]: Updated system data or error response with status code.
        """
        from ..connexion_handlers.system import update_system_settings

        # Get JSON body with proper type narrowing
        # NOTE: pyright doesn't recognize Flask's request.get_json() method properly
        # This is a known Flask typing limitation, method exists and works at runtime
        body_data: Any = request.get_json()  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]  # Flask typing limitation
        if body_data is None:
            body_data = {}
        body: JsonDict = body_data if isinstance(body_data, dict) else {}
        return update_system_settings(str(network_id), body)

    @app.route("/api/systems/<network_id>/devices")
    @ensure_blink_available
    @api_route_with_validation(
        "get system devices", validate_params={"network_id": validate_network_id}
    )
    def get_system_devices_route(
        network_id: NetworkId,
    ) -> JsonDict | tuple[JsonDict, int]:
        """Get system devices route - retrieves all devices (cameras, sync modules) for a system.

        Args:
            network_id: NetworkId object representing the system to get devices for.

        Returns:
            JsonDict | tuple[JsonDict, int]: Device list data or error response with status code.
        """
        from ..connexion_handlers.system import get_system_devices

        return get_system_devices(str(network_id))

    @app.route("/api/systems/cache", methods=["DELETE"])
    @ensure_blink_available
    @simple_success_response("clear systems cache")
    def clear_systems_cache_route() -> JsonDict:
        """Clear systems cache route - removes cached system data to force refresh.

        Returns:
            JsonDict: Success response indicating systems cache was cleared.
        """
        from ..connexion_handlers.system import clear_systems_cache

        return clear_systems_cache()
