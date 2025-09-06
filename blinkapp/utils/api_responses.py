"""Utility functions for creating standardized API responses."""

from datetime import UTC, datetime

from ..models.types import JsonDict, JsonValue


def create_api_response(
    success: bool, data: JsonValue = None, error: str | None = None
) -> JsonDict:
    """Create a standardized API response with timestamp.

    Args:
        success: Whether the operation was successful
        data: Response data (for successful responses)
        error: Error message (for failed responses)

    Returns:
        Standardized API response dict with timestamp
    """
    response: JsonDict = {
        "success": success,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if success and data is not None:
        response["data"] = data
    elif not success and error:
        response["error"] = error

    return response


def create_success_response(data: JsonValue = None) -> JsonDict:
    """Create a successful API response.

    Args:
        data: Response data

    Returns:
        Successful API response with timestamp
    """
    return create_api_response(success=True, data=data)


def create_error_response(error: str, status_code: int = 400) -> tuple[JsonDict, int]:
    """Create an error API response.

    Args:
        error: Error message
        status_code: HTTP status code

    Returns:
        Tuple of (error response dict, status code)
    """
    return create_api_response(success=False, error=error), status_code
