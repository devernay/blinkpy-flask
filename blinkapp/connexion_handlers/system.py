"""Connexion-compatible system management handlers."""

from typing import Any

from ..models.ids import NetworkId
from ..services.system_service import arm_system, get_devices, get_systems


def get_systems_route() -> dict[str, Any]:
    """Get list of available Blink systems.

    Connexion-compatible handler that returns system information.
    """
    return get_systems()


def get_system_devices_route(
    network_id_str: str,
) -> dict[str, Any] | tuple[dict[str, Any], int]:
    """Get devices for a specific Blink system.

    Args:
        network_id_str: Network ID as string from URL path

    Returns:
        Devices list dictionary
    """
    try:
        network_id = NetworkId(network_id_str)
    except ValueError:
        return {"success": False, "error": "Invalid network ID"}, 400

    return get_devices(network_id)


def get_devices_route(
    network_id_str: str,
) -> dict[str, Any] | tuple[dict[str, Any], int]:
    """Get devices for a specific Blink system.

    Args:
        network_id_str: Network ID as string from URL path

    Returns:
        Devices list dictionary
    """
    try:
        network_id = NetworkId(network_id_str)
    except ValueError:
        return {"success": False, "error": "Invalid network ID"}, 400

    return get_devices(network_id)


def update_system_route(
    network_id_str: str, body: dict[str, Any]
) -> dict[str, Any] | tuple[dict[str, Any], int]:
    """Update a Blink system (arm/disarm).

    Args:
        network_id_str: Network ID as string from URL path
        body: Request body containing system updates

    Returns:
        Update result dictionary
    """
    try:
        network_id = NetworkId(network_id_str)
    except ValueError:
        return {"success": False, "error": "Invalid network ID"}, 400

    if "armed" not in body:
        return {"success": False, "error": "Missing required field: armed"}, 400

    armed = body.get("armed")
    if not isinstance(armed, bool):
        return {"success": False, "error": "Field 'armed' must be boolean"}, 400

    return arm_system(network_id, armed)


def clear_systems_cache_route() -> dict[str, Any]:
    """Clear systems cache.

    Returns:
        Cache clear result dictionary
    """
    from ..services.system_service import refresh_system

    return refresh_system()
