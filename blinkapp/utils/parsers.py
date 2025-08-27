"""
Parsing utilities for the Blink Camera Flask application.

This module provides pure parsing functions for extracting and converting
data from various sources like URLs, command line arguments, and API responses.
"""

import argparse
import logging
import re
from urllib.parse import unquote

from blinkapp.config import Config
from blinkapp.models.ids import ClipId
from blinkapp.models.responses import create_api_response
from blinkapp.models.types import ApiResponse

logger = logging.getLogger(__name__)

__all__ = [
    "extract_thumbnail_timestamp",
    "parse_arguments",
    "parse_clip_id",
]


def extract_thumbnail_timestamp(thumbnail_url: str | None) -> int:
    """Extract timestamp from thumbnail URL.

    Parses the 'ts' parameter from Blink thumbnail URLs to determine
    when the thumbnail was generated. This timestamp is used for
    cache invalidation and thumbnail freshness checks.

    The Blink API includes timestamps in thumbnail URLs like:
    "https://immedia-semi.s3.amazonaws.com/production/...?ts=1234567890"

    Args:
        thumbnail_url: URL containing ts parameter (e.g., "...?ts=1234567890")

    Returns:
        Timestamp as integer (Unix epoch), 0 if not found or invalid

    Example:
        >>> extract_thumbnail_timestamp("https://example.com/thumb.jpg?ts=1609459200")
        1609459200
        >>> extract_thumbnail_timestamp("https://example.com/thumb.jpg")
        0
    """
    if not thumbnail_url:
        return 0
    try:
        # Extract numeric timestamp from URL query parameter using regex
        # Pattern matches 'ts=' followed by one or more digits
        match = re.search(r"ts=([0-9]+)", thumbnail_url)
        return int(match.group(1)) if match else 0
    except (AttributeError, ValueError, TypeError) as e:
        # Log debug info for troubleshooting but don't fail the operation
        logger.debug(f"Failed to extract timestamp from URL '{thumbnail_url}': {e}")
        return 0


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
