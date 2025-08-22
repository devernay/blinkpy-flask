"""Logging operations with dependency injection for better testability."""

from collections.abc import Callable

__all__ = [
    "log_error",
    "log_warning",
    "log_info",
    "log_debug",
]


def log_error(message: str, logger_func: Callable[[str], None] | None = None) -> None:
    """Log error with injectable logger for testing."""
    if logger_func is None:
        from blinkapp import logger

        logger_func = logger.error

    logger_func(message)


def log_warning(message: str, logger_func: Callable[[str], None] | None = None) -> None:
    """Log warning with injectable logger for testing."""
    if logger_func is None:
        from blinkapp import logger

        logger_func = logger.warning

    logger_func(message)


def log_info(message: str, logger_func: Callable[[str], None] | None = None) -> None:
    """Log info with injectable logger for testing."""
    if logger_func is None:
        from blinkapp import logger

        logger_func = logger.info

    logger_func(message)


def log_debug(message: str, logger_func: Callable[[str], None] | None = None) -> None:
    """Log debug with injectable logger for testing."""
    if logger_func is None:
        from blinkapp import logger

        logger_func = logger.debug

    logger_func(message)
