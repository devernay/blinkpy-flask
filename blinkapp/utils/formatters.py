"""Formatting utilities for the Blink Camera Flask application.

This module provides formatting functions for displaying data in user-friendly
formats, including time formatting and data organization.
"""

import logging
from datetime import UTC, datetime

from blinkapp.models.types import ClipApiData as ClipData
from blinkapp.models.types import ClipDayGroup

logger = logging.getLogger(__name__)

__all__ = [
    "format_clips_by_day",
    "format_time_duration",
    "format_clip_time",
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

                # Format date with day of week and conditional year
                current_year = datetime.now(UTC).year
                if dt.year == current_year:
                    date_display = dt.strftime("%A, %B %d")  # "Monday, January 15"
                else:
                    date_display = dt.strftime(
                        "%A, %B %d, %Y"
                    )  # "Monday, January 15, 2024"
            else:
                dt = datetime.now(UTC)
                date_key = dt.strftime("%Y-%m-%d")

                # Format date with day of week and conditional year
                current_year = dt.year
                date_display = dt.strftime("%A, %B %d")  # Current date, no year needed

            if date_key not in days:
                days[date_key] = {"date": date_display, "clips": []}
            clips_list = days[date_key]["clips"]
            if isinstance(clips_list, list):
                clips_list.append(clip)
        except (ValueError, KeyError):
            continue

    # Sort days by date (most recent first) and clips within each day by time (most recent first)
    sorted_days = []
    for date_key in sorted(days.keys(), reverse=True):
        day_group = days[date_key]
        # Sort clips within the day by created_at (most recent first)
        if isinstance(day_group["clips"], list):
            day_group["clips"].sort(
                key=lambda clip: clip.get("created_at", ""), reverse=True
            )
        sorted_days.append(day_group)

    return sorted_days


def format_clip_time(dt: datetime) -> str:
    """Format clip time for UI display.

    Args:
        dt: Datetime object to format

    Returns:
        Formatted time string (e.g., "11:29 AM")
    """
    return dt.astimezone().strftime("%I:%M %p")


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
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    if seconds < 86400:
        hours = seconds // 3600
        return f"{hours}h"
    days = seconds // 86400
    return f"{days}d"
