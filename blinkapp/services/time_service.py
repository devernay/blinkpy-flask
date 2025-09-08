"""Time operations with dependency injection for better testability.

This module provides time-related utilities with injectable time providers
to enable deterministic testing and consistent time handling across the
application.

Key features:
- Timestamp generation with configurable providers
- Time difference calculations
- Testable time operations via dependency injection
- Consistent datetime handling with timezone awareness

All functions support optional time providers for testing scenarios
where deterministic time values are required.
"""

from datetime import datetime

__all__ = [
    "seconds_since_now_from_datetime",
]


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
