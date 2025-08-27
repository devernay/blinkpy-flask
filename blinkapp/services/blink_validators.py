"""
Blink-specific validation utilities for the Blink Camera Flask application.

This module provides validation functions that are specific to Blink system
operations, including sync module validation and network-specific checks.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blinkpy.sync_module import BlinkSyncModule

from blinkapp.config import Config
from blinkapp.models.ids import NetworkId
from blinkapp.models.responses import create_api_response
from blinkapp.models.types import ApiResponse

logger = logging.getLogger(__name__)

__all__ = [
    "require_sync_module",
]


def require_sync_module(
    network_id: NetworkId,
) -> tuple["BlinkSyncModule | None", ApiResponse | None]:
    """Validate and retrieve sync module for network operations.

    This function ensures that a valid sync module exists for the given
    network ID before proceeding with network-specific operations. It
    provides consistent error handling for missing or invalid sync modules.

    Args:
        network_id: Network ID to validate and retrieve sync module for

    Returns:
        Tuple of (sync_module, error_response):
        - If successful: (BlinkSyncModule, None)
        - If failed: (None, ApiResponse with error details)

    Example:
        >>> sync_module, error = require_sync_module(network_id)
        >>> if error:
        ...     return error
        >>> # Use sync_module safely
    """
    from blinkapp.services.blink_service import blink

    if not blink or not blink.available:
        logger.warning(f"Blink not available for network {network_id}")
        return None, create_api_response(
            success=False,
            error="Blink system not available. Please check your connection.",
            status_code=Config.HTTP_STATUS_SERVICE_UNAVAILABLE,
        )

    # Search through all sync modules for matching network ID
    for name in blink.sync:
        sync_module = blink.sync[name]
        if str(sync_module.network_id) == str(network_id):
            return sync_module, None

    # Network ID not found - return standardized error response
    logger.warning(f"Sync module not found for network {network_id}")
    return None, create_api_response(
        success=False,
        error=f"Network {network_id} not found",
        status_code=Config.HTTP_STATUS_NOT_FOUND,
    )
