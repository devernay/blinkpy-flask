"""
Formatting utilities for the Blink Camera Flask application.

This module provides pure formatting functions for converting data into
user-friendly display formats, including time formatting, data organization,
and UI display helpers.
"""

import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

__all__ = [
    "format_clips_by_day",
    "format_time_ago",
]


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
        if "clips" in day_data:
            clips_list = day_data["clips"]
            # Sort clips within each day by time (newest first)
            # This ensures consistent ordering regardless of API response order
            assert isinstance(clips_list, list), (
                f"Expected clips_list to be list, got {type(clips_list)}"
            )
            clips_list.sort(key=lambda x: x["time"], reverse=True)
            # Add clip count for UI display (shows "5 clips" in interface)
            day_data["count"] = len(clips_list)
        clips.append(day_data)
    return clips


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
