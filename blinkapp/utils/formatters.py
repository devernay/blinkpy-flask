"""
Formatting utilities for the Blink Camera Flask application.

This module provides formatting functions for displaying data in user-friendly
formats, including time formatting and data organization.
"""

import logging
from datetime import UTC, datetime

from blinkapp.models.types import ClipData, ClipDayGroup

logger = logging.getLogger(__name__)

__all__ = [
    "format_clips_by_day",
    "format_time_duration",
]


def format_clips_by_day(clips: list[ClipData]) -> list[ClipDayGroup]:
    """Format clips grouped by day.

    Args:
        clips: List of clip data to group by day.

    Returns:
        List of clip day groups organized by date.
    """
    if not clips:
        return []

    # Group clips by date
    days: dict[str, ClipDayGroup] = {}
    for clip in clips:
        try:
            if "created_at" in clip:
                dt = datetime.fromisoformat(
                    str(clip["created_at"]).replace("Z", "+00:00")
                )
                date_key = dt.strftime("%Y-%m-%d")
                date_display = dt.strftime("%B %d, %Y")
            else:
                dt = datetime.now(UTC)
                date_key = dt.strftime("%Y-%m-%d")
                date_display = dt.strftime("%B %d, %Y")

            if date_key not in days:
                days[date_key] = {"date": date_display, "clips": []}
            clips_list = days[date_key]["clips"]
            if isinstance(clips_list, list):
                clips_list.append(clip)
        except (ValueError, KeyError):
            continue

    return sorted(days.values(), key=lambda x: str(x["date"]), reverse=True)


def format_time_duration(seconds: int) -> str:
    """Format a time duration in seconds to human readable string.

    Args:
        seconds: Duration in seconds (must be non-negative)

    Returns:
        Formatted duration string (e.g., "30s", "5m", "2h", "3d")

    Raises:
        ValueError: If seconds is negative
    """
    if seconds < 0:
        raise ValueError("Duration cannot be negative")
    elif seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours}h"
    else:
        days = seconds // 86400
        return f"{days}d"



