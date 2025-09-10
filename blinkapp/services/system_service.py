from __future__ import annotations
"""System service for Blink Camera Flask application.

This module handles all system-related business logic including
system listing, device management, and system arm/disarm operations.
"""

from typing import Dict, Any


__all__ = [
    "get_systems",
    "get_devices",
    "arm_system",
    "refresh_system",
]

import logging
from typing import TYPE_CHECKING

from blinkpy.camera import BlinkCamera

if TYPE_CHECKING:
    from blinkapp.models.ids import NetworkId

from ..models.types import DeviceDict, JsonDict, SystemDict

logger = logging.getLogger(__name__)


def get_systems() -> JsonDict:
    """Get list of available Blink systems.

    Retrieves all configured Blink sync modules and their associated
    network information. Each system represents a separate Blink hub
    with its own set of cameras.

    Returns:
        Dictionary with list of systems
    """
    from blinkapp.services.blink_service import ensure_blink_initialized

    blink = ensure_blink_initialized()

    logger.debug(f"Getting systems - sync count: {len(blink.sync)}")
    systems: list[SystemDict] = []
    for name, sync in blink.sync.items():
        logger.debug(f"Processing sync: {name}, network_id: {sync.network_id}")
        systems.append(
            {
                "name": name,
                "network_id": sync.network_id,
                "armed": sync.arm,
                "online": sync.online,
            }
        )

    return {"systems": systems}


def get_devices(network_id: NetworkId) -> JsonDict:
    """Get devices for a specific Blink system.

    Args:
        network_id: Validated NetworkId object

    Returns:
        Dictionary with list of devices
    """
    from blinkapp.models.ids import CameraId
    from blinkapp.routes.thumbnails import update_camera_thumbnail
    from blinkapp.services.blink_validators import require_sync_module
    from blinkapp.services.cache_service import (
        ensure_camera_thumbnail_cache_initialized,
    )
    from blinkapp.services.device_service import create_device_data
    from blinkapp.utils.errors import ValidationError
    from blinkapp.utils.parsers import extract_thumbnail_timestamp

    devices: list[DeviceDict] = []

    # Find the sync module for this network
    sync_module, error_response = require_sync_module(network_id)
    if error_response is not None:
        error_dict, status_code = error_response
        error_message = error_dict.get("error", "Unknown error")
        raise ValidationError(str(error_message), status_code)

    assert sync_module is not None
    # Add sync module
    devices.append(
        {
            "type": "sync_module",
            "name": "Sync Module",
            "online": sync_module.online,
            "id": sync_module.sync_id,
        }
    )

    # Add cameras - refresh thumbnails in Blink thread
    camera_thumbnail_cache_instance = ensure_camera_thumbnail_cache_initialized()
    for _, camera in sync_module.cameras.items():
        if not isinstance(camera, BlinkCamera):
            continue

        logger.debug(
            f"Processing camera: {camera.name}, current thumbnail: {camera.thumbnail}"
        )

        if camera.camera_id is None:
            continue

        cache_key = CameraId(camera.camera_id)
        current_ts = extract_thumbnail_timestamp(camera.thumbnail)
        cached_entry = camera_thumbnail_cache_instance.get(cache_key)
        cached_ts = cached_entry.get("timestamp", 0) if cached_entry else 0

        # Update thumbnail if needed
        update_camera_thumbnail(camera, current_ts, cached_ts)

        # Create device data
        device_data = create_device_data(camera, current_ts, cached_ts)  # type: ignore[misc]
        logger.debug(f"Camera device data for {camera.name}: {device_data}")
        devices.append(device_data)

    return {"devices": devices}


def arm_system(network_id: NetworkId, armed: bool) -> JsonDict:
    """Arm or disarm a Blink system.

    Args:
        network_id: Validated NetworkId object
        armed: True to arm, False to disarm

    Returns:
        Dictionary with operation result
    """
    from blinkapp.services.blink_service import ensure_blink_connection_initialized
    from blinkapp.services.blink_validators import require_sync_module
    from blinkapp.utils.decorators import error_context
    from blinkapp.utils.errors import ValidationError

    logger.debug(f"{'Arming' if armed else 'Disarming'} system {network_id}")

    # Find the sync module for this network
    sync_module, error_response = require_sync_module(network_id)
    if error_response is not None:
        error_dict, status_code = error_response
        error_message = error_dict.get("error", "Unknown error")
        raise ValidationError(str(error_message), status_code)

    with error_context("arm/disarm system"):
        if sync_module is not None:
            blink_conn = ensure_blink_connection_initialized()
            blink_conn.execute(sync_module.async_arm(armed))
        return {"armed": armed}


def refresh_system() -> JsonDict:
    """Refresh all Blink systems.

    Returns:
        Dictionary with refresh result
    """
    from blinkapp.config import Config
    from blinkapp.models.responses import create_api_response
    from blinkapp.services.blink_service import (
        ensure_blink_connection_initialized,
        ensure_blink_initialized,
    )

    blink = ensure_blink_initialized()

    logger.debug("Refreshing all Blink systems")

    try:
        blink_conn = ensure_blink_connection_initialized()
        success = blink_conn.execute(blink.refresh(force=True))
    except RuntimeError:
        success = False

    if success is not True:
        response, _ = create_api_response(
            success=False,
            error=Config.ErrorMessages.SYSTEM_REFRESH_FAILED,
            status_code=500,
        )
        return response  # Return just the dict, not the tuple

    return {}  # Empty dict for success
