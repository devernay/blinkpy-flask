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
