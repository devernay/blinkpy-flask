"""API response models and utilities for the Blink Flask application."""

from datetime import datetime

from app_types import JsonDict
from config import Config

# Explicitly define what this module exports
__all__ = [
    "create_api_response",
]


def create_api_response(
    success: bool = True,
    data: object = None,
    error: str | None = None,
    status_code: int = Config.HTTP_STATUS_OK,
) -> tuple["JsonDict", int]:
    """Create standardized API response format.

    Provides consistent JSON response structure across all API endpoints
    with success status, data payload, error messages, and timestamps.

    Args:
        success: Whether the operation was successful
        data: Response data payload (for successful operations)
        error: Error message string (for failed operations)
        status_code: HTTP status code to return

    Returns:
        Tuple of (response_dict, status_code) for Flask route handlers
    """
    response: JsonDict = {
        "success": success,
        "timestamp": datetime.now().isoformat(),
        "data": data if success else None,
        "error": error if not success else None,
    }

    return response, status_code
