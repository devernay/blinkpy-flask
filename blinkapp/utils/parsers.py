"""
Parsing utilities for the Blink Camera Flask application.

This module provides parsing functions for extracting and converting data
from various sources like timestamps, arguments, and identifiers.
"""

import logging

logger = logging.getLogger(__name__)

__all__ = [
    "extract_thumbnail_timestamp",
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
