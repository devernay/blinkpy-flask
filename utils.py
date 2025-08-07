"""
Utility functions for the Blink Camera Flask application.

This module provides common utility functions used throughout the application
for data processing, API response formatting, time calculations, and
command-line argument parsing. Functions are designed to be stateless
and reusable across different modules.
"""

import argparse
import logging
from datetime import UTC, datetime

from app_types import ApiResponse, JsonDict
from config import Config
from ids import ClipId

# Module-level logger for utility function debugging
logger = logging.getLogger(__name__)


# ============================================================================
# Command Line Argument Parsing
# ============================================================================


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments for the Flask application.

    Supports configuration of host, port, debug mode, cache directory,
    and special commands like system dumps.

    Args:
        args: Optional list of arguments to parse (primarily for testing)

    Returns:
        Parsed arguments namespace with all configuration options
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

    Performs comprehensive validation on user input strings to prevent
    security issues and ensure data quality. This includes type checking,
    length limits, and basic XSS prevention.

    Args:
        value: Input string to validate (may contain leading/trailing whitespace)
        max_length: Maximum allowed length after trimming whitespace
        field_name: Human-readable name of field for error messages

    Returns:
        Validated and stripped string ready for use

    Raises:
        ValueError: If validation fails with specific error message

    Example:
        >>> validate_string_input("  test@example.com  ", 50, "Email")
        "test@example.com"
        >>> validate_string_input("<script>alert('xss')</script>", 50, "Username")
        ValueError: Username contains invalid characters
    """
    # Type validation - ensure we received a string
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    # Strip whitespace and check for empty values after trimming
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} cannot be empty")

    # Length validation to prevent abuse and database overflow
    if len(value) > max_length:
        raise ValueError(f"{field_name} too long (max {max_length} characters)")

    # Basic XSS prevention - reject HTML-like content that could be dangerous
    # This is a simple check; more sophisticated validation may be needed
    # for specific use cases
    if "<" in value or ">" in value or "&" in value:
        raise ValueError(f"{field_name} contains invalid characters")

    return value


# ============================================================================
# Data Processing and Parsing
# ============================================================================


def parse_clip_id(
    clip_id_str: str,
) -> tuple[ClipId | None, ApiResponse | None]:
    """Parse and validate clip ID from URL parameter.

    Handles URL decoding and validates the clip ID format to ensure
    it meets the expected structure for Blink clip identifiers.
    This function is used by API endpoints that receive clip IDs
    as URL parameters.

    Args:
        clip_id_str: URL-encoded clip ID string from request parameter
                    (may contain %20 for spaces, etc.)

    Returns:
        Tuple of (clip_id, error_response). Exactly one will be None:
        - If valid: (ClipId instance, None)
        - If invalid: (None, error_response_tuple)

    Example:
        >>> clip_id, error = parse_clip_id("123456")
        >>> if error:
        ...     return error  # Return error to client
        >>> # Use clip_id for further processing
    """
    try:
        from urllib.parse import unquote

        # Decode URL-encoded clip ID (handles %20, %7E, etc.)
        clip_id_str = unquote(clip_id_str)

        # Validate clip ID format using ClipId constructor
        clip_id = ClipId(clip_id_str)
        return clip_id, None
    except ValueError as e:
        # Return standardized error response for invalid clip IDs
        # This maintains consistent API error format
        error_response = create_api_response(
            success=False, error=str(e), status_code=400
        )
        return None, error_response


def format_clips_by_day(
    clips_by_day: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    """Format clips by day into sorted list.

    Takes a dictionary of clips grouped by day and converts it to a
    sorted list suitable for JSON API responses. This function handles
    the final formatting step for both cloud and local clips.

    The function sorts days in reverse chronological order (newest first)
    and clips within each day by time. It also adds clip counts for
    UI display purposes.

    Args:
        clips_by_day: Dictionary with day keys (YYYY-MM-DD) mapping to
                     day objects containing date string and clips list

    Returns:
        Sorted list of day groups, each containing:
        - date: Human-readable date string (e.g., "January 01, 2023")
        - clips: List of clip objects sorted by time (newest first)
        - count: Number of clips in this day for UI display

    Example:
        >>> clips_dict = {"2023-01-01": {"date": "January 01, 2023", "clips": [...]}}
        >>> result = format_clips_by_day(clips_dict)
        >>> result[0]["count"]
        5
    """
    clips = []
    # Sort days in reverse chronological order (newest first for better UX)
    for day_key in sorted(clips_by_day.keys(), reverse=True):
        day_data = clips_by_day[day_key]

        # Ensure day_data is a dict and has clips list
        if isinstance(day_data, dict) and "clips" in day_data:
            clips_list = day_data["clips"]
            if isinstance(clips_list, list):
                # Sort clips within each day by time (newest first)
                # This ensures consistent ordering regardless of API response order
                clips_list.sort(key=lambda x: x["time"], reverse=True)

                # Add clip count for UI display (shows "5 clips" in interface)
                day_data["count"] = len(clips_list)
        clips.append(day_data)
    return clips


# ============================================================================
# Time and Date Formatting
# ============================================================================


def format_time_ago(timestamp_str: str | int | None) -> str:
    """Format timestamp as 'Xd ago' format.

    Converts various timestamp formats into human-readable relative time
    strings like '5d ago', '2h ago', '30m ago' for better user experience.
    This function handles multiple input formats from different parts of
    the Blink API.

    Args:
        timestamp_str: Timestamp in one of these formats:
                      - ISO format string (e.g., "2023-01-01T12:00:00Z")
                      - Unix timestamp integer (seconds since epoch)
                      - None (for missing timestamps)

    Returns:
        Human-readable time string:
        - "Xd ago" for days (e.g., "5d ago")
        - "Xh ago" for hours (e.g., "2h ago")
        - "Xm ago" for minutes (e.g., "30m ago")
        - "Unknown" if timestamp is invalid or None

    Example:
        >>> format_time_ago("2023-01-01T12:00:00Z")
        "5d ago"
        >>> format_time_ago(1672574400)
        "2h ago"
        >>> format_time_ago(None)
        "Unknown"
    """
    try:
        if timestamp_str is None:
            return "Unknown"

        # Handle different input types from various Blink API endpoints
        if isinstance(timestamp_str, int):
            # Unix timestamp (seconds since epoch) from some API responses
            timestamp = datetime.fromtimestamp(timestamp_str, tz=UTC)
        elif isinstance(timestamp_str, str):
            # ISO format timestamp string from Blink API (handle Z suffix)
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        else:
            logger.debug(f"Unsupported timestamp type: {type(timestamp_str)}")
            return "Unknown"

        # Calculate time difference using timezone-aware comparison
        now = datetime.now(timestamp.tzinfo)
        diff = now - timestamp
        days = diff.days

        # Format in most appropriate unit (days > hours > minutes)
        if days == 0:
            hours = diff.seconds // 3600
            if hours == 0:
                minutes = diff.seconds // 60
                return f"{minutes}m ago"
            return f"{hours}h ago"
        return f"{days}d ago"
    except (ValueError, TypeError, AttributeError, OSError) as e:
        # Log debug info but don't fail the operation
        logger.debug(f"Failed to format time ago for '{timestamp_str}': {e}")
        return "Unknown"


# ============================================================================
# API Response Formatting
# ============================================================================


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


def ensure_cache_paths_initialized() -> None:
    """Ensure cache paths are initialized, raising an error if not.

    This function serves as a type guard for mypy to understand that
    the cache path variables are not None after this call.

    Raises:
        RuntimeError: If cache paths haven't been initialized
    """
    # Import here to avoid circular imports
    from blinkapp import (
        CACHE_DIR,
        CLIPS_CACHE_DIR,
        CREDENTIALS_FILE,
        THUMBNAIL_CACHE_DIR,
    )

    if (
        CACHE_DIR is None
        or CREDENTIALS_FILE is None
        or THUMBNAIL_CACHE_DIR is None
        or CLIPS_CACHE_DIR is None
    ):
        raise RuntimeError(
            "Cache paths not initialized. Call initialize_cache_paths() first."
        )
