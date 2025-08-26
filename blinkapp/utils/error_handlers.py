"""
Error handling utilities for the Blink Camera Flask application.

This module provides centralized error handling for API endpoints with
consistent error response formatting and user-friendly error messages.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blinkpy.sync_module import BlinkSyncModule

from blinkapp.config import Config
from blinkapp.models.ids import NetworkId
from blinkapp.models.responses import create_api_response
from blinkapp.models.types import ApiResponse
from blinkapp.utils.errors import ValidationError

logger = logging.getLogger(__name__)


def handle_api_error(
    error: Exception,
    operation: str,
    status_code: int = Config.HTTP_STATUS_INTERNAL_ERROR,
) -> ApiResponse:
    """Handle API errors with user-friendly messages.

    Provides centralized error handling for all API endpoints with consistent
    error response format and appropriate HTTP status codes. This function
    translates technical exceptions into user-friendly messages while
    preserving the original error information in logs.

    Args:
        error: Exception that occurred during operation
        operation: Human-readable description of the failed operation
        status_code: HTTP status code to return (default: 500)

    Returns:
        Standardized error response tuple (response_dict, status_code)

    Example:
        >>> try:
        ...     # Some operation that might fail
        ...     pass
        ... except Exception as e:
        ...     return handle_api_error(e, "updating camera settings")
    """
    # Log the full technical error for debugging
    logger.error(f"Error {operation}: {error}")

    # Handle ValidationError with custom status code - these have specific
    # status codes that should be preserved (e.g., 400 for bad input)
    if isinstance(error, ValidationError):
        return create_api_response(
            success=False, error=str(error), status_code=error.status_code
        )

    # Map common exceptions to user-friendly messages that don't expose
    # internal implementation details to end users
    error_message = str(error)
    if isinstance(error, ConnectionError):
        error_message = (
            "Unable to connect to your Blink system. Please check your "
            "internet connection and try again."
        )
    elif isinstance(error, TimeoutError):
        error_message = "The request timed out. Please try again in a moment."
    elif isinstance(error, ValueError):
        # For ValueError, preserve the original message for better debugging
        error_message = str(error)
    elif "authentication" in str(error).lower() or "login" in str(error).lower():
        # Use predefined auth error message for consistency
        error_message = Config.ErrorMessages.AUTH_FAILED
    elif "not found" in str(error).lower():
        error_message = "The requested item could not be found."
    elif status_code >= 500:
        # For server errors, use generic message to avoid exposing internals
        error_message = Config.ErrorMessages.INTERNAL_ERROR

    return create_api_response(
        success=False, error=error_message, status_code=status_code
    )


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
