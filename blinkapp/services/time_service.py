"""Time operations with dependency injection for better testability."""

from collections.abc import Callable
from datetime import datetime

__all__ = [
    "get_current_timestamp",
    "format_timestamp",
    "get_current_time",
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


def format_timestamp(
    timestamp: int, formatter: Callable[[int], str] | None = None
) -> str:
    """Format timestamp with injectable formatter."""
    if formatter is None:
        from blinkapp.utils.formatters import format_time_ago

        formatter = format_time_ago

    return formatter(timestamp)
