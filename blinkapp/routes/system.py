"""System management routes for the Blink Flask application."""

from flask import Flask, request

from app_types import JsonDict
from blinkapp.models.ids import NetworkId
from blinkapp.services.system_service import (
    arm_system,
    get_devices,
    get_systems,
    refresh_system,
)
from blinkapp.utils.decorators import ensure_blink_available
from route_decorators import (
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
        return get_systems()

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
        return get_devices(network_id)

    @app.route("/api/systems/<network_id_str>/arm", methods=["POST"])
    @ensure_blink_available
    @api_route_with_validation(
        "arm/disarm system",
        validate_params={"network_id_str": NetworkId},
        validate_json=True,
        required_fields=["armed"],
    )
    def arm_system_route(network_id: NetworkId) -> JsonDict:
        """Arm or disarm a Blink system.

        Args:
            network_id: Validated NetworkId object

        Returns:
            JSON response with success status or error message
        """
        data = request.get_json()
        armed = data["armed"]
        return arm_system(network_id, armed)

    @app.route("/api/systems/refresh", methods=["PUT"])
    @ensure_blink_available
    @simple_success_response("System refreshed successfully")
    def refresh_system_route() -> JsonDict:
        """Manually refresh the Blink system.

        Returns:
            JSON response with success status or error message
        """
        return refresh_system()
