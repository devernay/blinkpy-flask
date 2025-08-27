"""System service for Blink Camera Flask application.

This module handles all system-related business logic including
system listing, device management, and system arm/disarm operations.
"""

from __future__ import annotations

__all__ = [
    "get_systems",
    "get_devices",
    "arm_system",
    "refresh_system",
]

import logging
from typing import TYPE_CHECKING, Any

from blinkpy.camera import BlinkCamera

if TYPE_CHECKING:
    from blinkapp.models.ids import NetworkId

logger = logging.getLogger(__name__)


def get_systems() -> dict[str, Any]:
    """Get list of available Blink systems.

    Retrieves all configured Blink sync modules and their associated
    network information. Each system represents a separate Blink hub
    with its own set of cameras.

    Returns:
        Dictionary with list of systems
    """
    from blinkapp.services.blink_service import blink

    assert blink is not None, "Blink must be initialized"

    logger.debug(f"Getting systems - sync count: {len(blink.sync)}")
    systems: list[dict[str, Any]] = []
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


def get_devices(network_id: NetworkId) -> dict[str, Any]:
    """Get devices for a specific Blink system.

    Args:
        network_id: Validated NetworkId object

    Returns:
        Dictionary with list of devices
    """
    from blinkapp import (
        logger,
    )
    from blinkapp.models.ids import CameraId
    from blinkapp.routes.camera import update_camera_thumbnail
    from blinkapp.services.blink_validators import require_sync_module
    from blinkapp.services.cache_service import ensure_thumbnail_cache_initialized
    from blinkapp.services.utils_service import create_device_data
    from blinkapp.utils.errors import ValidationError
    from blinkapp.utils.parsers import extract_thumbnail_timestamp

    devices: list[dict[str, Any]] = []

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
    thumbnail_cache_instance = ensure_thumbnail_cache_initialized()
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
        cached_entry = thumbnail_cache_instance.get(cache_key)
        cached_ts = cached_entry.get("timestamp", 0) if cached_entry else 0

        # Update thumbnail if needed
        update_camera_thumbnail(camera, cache_key, current_ts, cached_ts)

        # Create device data
        device_data = create_device_data(camera, cache_key, current_ts, cached_ts)
        logger.debug(f"Camera device data for {camera.name}: {device_data}")
        devices.append(device_data)

    return {"devices": devices}


def arm_system(network_id: NetworkId, armed: bool) -> dict[str, Any]:
    """Arm or disarm a Blink system.

    Args:
        network_id: Validated NetworkId object
        armed: True to arm, False to disarm

    Returns:
        Dictionary with operation result
    """
    from blinkapp.services.blink_service import blink_connection
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
        if sync_module is not None and blink_connection:
            blink_connection.execute(sync_module.async_arm(armed))
        return {"armed": armed}


def refresh_system() -> dict[str, Any]:
    """Refresh all Blink systems.

    Returns:
        Dictionary with refresh result
    """
    from blinkapp.config import Config
    from blinkapp.models.responses import create_api_response
    from blinkapp.services.blink_service import blink, blink_connection

    assert blink is not None, "Blink must be initialized"

    logger.debug("Refreshing all Blink systems")

    if blink_connection:
        success = blink_connection.execute(blink.refresh(force=True))
    else:
        success = False

    if success is not True:
        response, _ = create_api_response(
            success=False,
            error=Config.ErrorMessages.SYSTEM_REFRESH_FAILED,
            status_code=500,
        )
        return response  # Return just the dict, not the tuple

    return {}  # Empty dict for success
