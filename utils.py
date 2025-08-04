"""Utility functions for the Blink Camera Flask application."""

import argparse
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from config import Config
from ids import ClipId

if TYPE_CHECKING:
    from typing import Any

    JsonDict = dict[str, Any]
    ApiResponse = tuple[JsonDict, int]

logger = logging.getLogger(__name__)


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        args: Optional list of arguments to parse (for testing)

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(description="Blink Camera Flask Web Interface")
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=5000, help="Port to bind to (default: 5000)"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "--cache", default=Config.DEFAULT_CACHE_DIR, help="Cache directory path"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level",
    )
    parser.add_argument(
        "--dump-system",
        action="store_true",
        help="Dump Blink system information and exit (requires saved credentials)",
    )

    return parser.parse_args(args)


def validate_string_input(value: str, max_length: int, field_name: str) -> str:
    """Validate string input for length and basic safety.

    Args:
        value: Input string to validate
        max_length: Maximum allowed length
        field_name: Name of field for error messages

    Returns:
        Validated and stripped string

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} cannot be empty")

    if len(value) > max_length:
        raise ValueError(f"{field_name} too long (max {max_length} characters)")

    # Basic XSS prevention
    if "<" in value or ">" in value or "&" in value:
        raise ValueError(f"{field_name} contains invalid characters")

    return value


def parse_clip_id(
    clip_id_str: str,
) -> tuple[ClipId | None, tuple["ApiResponse", int] | None]:
    """Parse and validate clip ID from URL parameter.

    Args:
        clip_id_str: URL-encoded clip ID string

    Returns:
        Tuple of (clip_id, error_response). One will be None.
    """
    try:
        from urllib.parse import unquote

        clip_id_str = unquote(clip_id_str)
        clip_id = ClipId(clip_id_str)
        return clip_id, None
    except ValueError as e:
        error_response = create_api_response(
            success=False, error=str(e), status_code=400
        )
        return None, error_response


def format_clips_by_day(
    clips_by_day: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    """Format clips by day into sorted list.

    Args:
        clips_by_day: Dictionary of clips grouped by day

    Returns:
        Sorted list of day groups
    """
    clips = []
    for day_key in sorted(clips_by_day.keys(), reverse=True):
        day_data = clips_by_day[day_key]
        day_data["clips"].sort(key=lambda x: x["time"], reverse=True)
        day_data["count"] = len(day_data["clips"])
        clips.append(day_data)
    return clips


def format_time_ago(timestamp_str: str | int | None) -> str:
    """Format timestamp as 'Xd ago' format.

    Args:
        timestamp_str: ISO format timestamp string, Unix timestamp integer, or None

    Returns:
        Formatted time string like '5d ago', '2h ago', '30m ago', or 'Unknown'
    """
    try:
        if timestamp_str is None:
            return "Unknown"

        # Handle different input types
        if isinstance(timestamp_str, int):
            # Unix timestamp (seconds since epoch)
            timestamp = datetime.fromtimestamp(timestamp_str, tz=timezone.utc)
        elif isinstance(timestamp_str, str):
            # ISO format timestamp string
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        else:
            logger.debug(f"Unsupported timestamp type: {type(timestamp_str)}")
            return "Unknown"

        now = datetime.now(timestamp.tzinfo)
        diff = now - timestamp
        days = diff.days
        if days == 0:
            hours = diff.seconds // 3600
            if hours == 0:
                minutes = diff.seconds // 60
                return f"{minutes}m ago"
            return f"{hours}h ago"
        return f"{days}d ago"
    except (ValueError, TypeError, AttributeError, OSError) as e:
        logger.debug(f"Failed to format time ago for '{timestamp_str}': {e}")
        return "Unknown"


def create_api_response(
    success: bool = True,
    data: object = None,
    error: str | None = None,
    status_code: int = Config.HTTP_STATUS_OK,
) -> tuple["JsonDict", int]:
    """Create standardized API response format.

    Args:
        success: Whether the operation was successful
        data: Response data (for successful operations)
        error: Error message (for failed operations)
        status_code: HTTP status code

    Returns:
        Tuple of (response_dict, status_code)
    """
    response: JsonDict = {
        "success": success,
        "timestamp": datetime.now().isoformat(),
        "data": data if success else None,
        "error": error if not success else None,
    }

    return response, status_code


def ensure_cache_paths_initialized() -> None:
    """Ensure cache paths are initialized, raising an error if not.

    This function serves as a type guard for mypy to understand that
    the cache path variables are not None after this call.

    Raises:
        RuntimeError: If cache paths haven't been initialized
    """
    # Import here to avoid circular imports
    from app import CACHE_DIR, CLIPS_CACHE_DIR, CREDENTIALS_FILE, THUMBNAIL_CACHE_DIR

    if (
        CACHE_DIR is None
        or CREDENTIALS_FILE is None
        or THUMBNAIL_CACHE_DIR is None
        or CLIPS_CACHE_DIR is None
    ):
        raise RuntimeError(
            "Cache paths not initialized. Call initialize_cache_paths() first."
        )
