"""Connexion-compatible system management handlers."""

from ..models.ids import NetworkId
from ..models.types import JsonDict
from ..services.system_service import arm_system
from ..services.system_service import get_devices as service_get_devices
from ..services.system_service import get_systems as service_get_systems


def get_systems() -> JsonDict:
    """Get list of available Blink systems.

    Returns:
        Systems list dictionary
    """
    return service_get_systems()


def get_system_details(network_id_str: str) -> JsonDict | tuple[JsonDict, int]:
    """Get system details.

    Args:
        network_id_str: Network ID string

    Returns:
        System details dictionary
    """
    from ..services.system_service import (
        get_system_details as service_get_system_details,
    )

    try:
        network_id = NetworkId(network_id_str)
        return service_get_system_details(network_id)
    except ValueError:
        return {"success": False, "error": "Invalid network ID"}, 400


def get_system_devices(network_id_str: str) -> JsonDict | tuple[JsonDict, int]:
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

    return service_get_devices(network_id)


def get_devices(network_id_str: str) -> JsonDict | tuple[JsonDict, int]:
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

    return service_get_devices(network_id)


def update_system_settings(
    network_id_str: str, body: JsonDict
) -> JsonDict | tuple[JsonDict, int]:
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


def clear_systems_cache() -> JsonDict:
    """Clear systems cache.

    Returns:
        Cache clear result dictionary
    """
    from ..services.system_service import refresh_system

    return refresh_system()
