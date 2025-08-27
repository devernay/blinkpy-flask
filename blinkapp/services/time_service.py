"""Time operations with dependency injection for better testability."""

from collections.abc import Callable
from datetime import datetime

__all__ = [
    "get_current_timestamp",
    "get_current_time",
    "seconds_since_now_from_datetime",
]


def get_current_timestamp(time_provider: Callable[[], int] | None = None) -> int:
    """Get current timestamp with injectable time provider."""
    if time_provider is None:

        def default_time_provider() -> int:
            return int(datetime.now().timestamp())

        time_provider = default_time_provider

    return time_provider()


def get_current_time(time_provider: Callable[[], datetime] | None = None) -> datetime:
    """Get current datetime with injectable time provider."""
    if time_provider is None:
        time_provider = datetime.now

    return time_provider()


def seconds_since_now_from_datetime(dt: "datetime") -> int:
    """Calculate seconds elapsed since now from datetime object.

    Args:
        dt: Datetime object with timezone info

    Returns:
        Seconds elapsed since now (positive if datetime is in the past)

    Raises:
        ValueError: If datetime has no timezone info
    """
    from datetime import UTC, datetime

    if dt.tzinfo is None:
        raise ValueError("Datetime object must include timezone information")

    now = datetime.now(UTC)
    if dt.tzinfo != UTC:
        dt = dt.astimezone(UTC)

    diff = now - dt
    return int(diff.total_seconds())
