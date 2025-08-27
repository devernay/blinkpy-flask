"""
Parsing utilities for the Blink Camera Flask application.

This module provides parsing functions for extracting and converting data
from various sources like timestamps, arguments, and identifiers.
"""

import argparse
import logging

logger = logging.getLogger(__name__)

__all__ = [
    "extract_thumbnail_timestamp",
    "parse_arguments",
    "parse_clip_id",
]


def extract_thumbnail_timestamp(filename: str | None) -> int:
    """Extract timestamp from thumbnail filename.

    Args:
        filename: Thumbnail filename in format "camera_timestamp.jpg"

    Returns:
        Timestamp as integer

    Raises:
        ValueError: If filename format is invalid
    """
    if not filename:
        return 0

    try:
        # Handle URL format with ts parameter like "?ts=1742459551&ext="
        if "ts=" in filename:
            parts = filename.split("ts=")
            if len(parts) > 1:
                timestamp_part = parts[1].split("&")[
                    0
                ]  # Get part before next parameter
                return int(timestamp_part)

        # Handle URL format like "https://example.com/thumb_1742459551.jpg"
        if "thumb_" in filename:
            parts = filename.split("thumb_")
            if len(parts) > 1:
                timestamp_part = parts[1].split(".")[0]  # Remove extension
                return int(timestamp_part)

        # Extract timestamp from filename like "12345_1234567890.jpg"
        base = filename.replace(".jpg", "")
        parts = base.split("_")
        if len(parts) >= 2:
            return int(parts[-1])
        return 0
    except (ValueError, IndexError):
        return 0


def parse_arguments(args_string: str | list[str]) -> argparse.Namespace:
    """Parse command line arguments string into namespace object."""
    import argparse

    from blinkapp.config import Config

    # Create argument parser
    parser = argparse.ArgumentParser(description="Blink Camera Flask Web Interface")
    parser.add_argument(
        "--host",
        default=Config.DEFAULT_HOST,
        help=f"Host to bind to (default: {Config.DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=Config.DEFAULT_PORT,
        help=f"Port to bind to (default: {Config.DEFAULT_PORT})",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level (default: INFO)",
    )
    parser.add_argument(
        "--cache",
        default=Config.DEFAULT_CACHE_DIR,
        help=f"Cache directory (default: {Config.DEFAULT_CACHE_DIR})",
    )
    parser.add_argument(
        "--dump-system", action="store_true", help="Dump system info and exit"
    )

    # Handle both string and list inputs for backward compatibility
    if isinstance(args_string, list):
        args_list = args_string
    else:
        args_list = args_string.split() if args_string else []

    return parser.parse_args(args_list)


def parse_clip_id(clip_id_str: str) -> str:
    """Parse and validate clip ID string.

    Args:
        clip_id_str: Raw clip ID string

    Returns:
        Validated clip ID

    Raises:
        ValueError: If clip ID format is invalid
    """
    if not clip_id_str or not isinstance(clip_id_str, str):
        raise ValueError("Invalid clip ID")

    # Basic validation - alphanumeric and some special chars
    clip_id = clip_id_str.strip()
    if not clip_id:
        raise ValueError("Clip ID cannot be empty")

    return clip_id
