"""Connexion-compatible system management handlers."""

from ..models.ids import NetworkId
from ..models.types import JsonDict
from ..services.system_service import arm_system, get_devices


def get_systems() -> JsonDict:
    """Get list of available Blink systems.

    Returns:
        Systems list dictionary
    """
    from ..services.system_service import get_systems as service_get_systems

    return service_get_systems()


def get_system_details(network_id: str) -> JsonDict | tuple[JsonDict, int]:
    """Get system details.

    Args:
        network_id: Network ID string

    Returns:
        System details dictionary
    """
    from ..services.system_service import get_systems

    try:
        network_id_obj = NetworkId(network_id)
        systems_response = get_systems()

        # Type narrowing: ensure response is a dict
        if not isinstance(systems_response, dict):
            return {"success": False, "error": "Invalid systems response"}, 500

        if not systems_response.get("success", False):
            return systems_response

        # Type narrowing: ensure data is a dict
        data = systems_response.get("data", {})
        if not isinstance(data, dict):
            return {"success": False, "error": "Invalid systems data"}, 500

        systems = data.get("systems", [])
        # Type narrowing: ensure systems is iterable
        if not isinstance(systems, list | tuple):
            return {"success": False, "error": "Invalid systems format"}, 500

        for system in systems:
            # Type narrowing: ensure system is a dict
            if isinstance(system, dict) and str(system.get("network_id")) == str(network_id_obj):
                return {"success": True, "data": system}

        return {"success": False, "error": "System not found"}, 404
    except ValueError:
        return {"success": False, "error": "Invalid network ID"}, 400


def get_system_devices(network_id: str) -> JsonDict | tuple[JsonDict, int]:
    """Get devices for a specific Blink system.

    Args:
        network_id: Network ID string

    Returns:
        Devices list dictionary
    """

    try:
        network_id_obj = NetworkId(network_id)
        return get_devices(network_id_obj)
    except ValueError:
        return {"success": False, "error": "Invalid network ID"}, 400

    return get_devices(network_id)


def update_system_settings(
    network_id: str, body: JsonDict
) -> JsonDict | tuple[JsonDict, int]:
    """Update a Blink system (arm/disarm).

    Args:
        network_id: Network ID string
        body: Request body containing system updates

    Returns:
        Update result dictionary
    """
    try:
        network_id_obj = NetworkId(network_id)
    except ValueError:
        return {"success": False, "error": "Invalid network ID"}, 400

    if "armed" not in body:
        return {"success": False, "error": "Missing required field: armed"}, 400

    armed = body.get("armed")
    if not isinstance(armed, bool):
        return {"success": False, "error": "Field 'armed' must be boolean"}, 400

    return arm_system(network_id_obj, armed)


def clear_systems_cache() -> JsonDict:
    """Clear systems cache.

    Returns:
        Cache clear result dictionary
    """
    from ..services.system_service import refresh_system

    return refresh_system()
