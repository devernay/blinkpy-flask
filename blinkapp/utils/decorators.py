"""Decorators and utility functions for the Blink Camera Flask application.

This module provides reusable decorators and context managers for common
patterns throughout the application, including error handling, validation,
and resource management.

Key components:
- Error context management with logging and exception handling
- Safe execution wrappers with fallback behavior
- Blink availability checking decorators
- API route validation and response formatting
- Resource cleanup and error recovery patterns

These utilities promote consistent error handling and reduce code duplication
across the application while maintaining clean separation of concerns.
"""

import functools
import logging
import traceback
from collections.abc import Callable, Generator
from contextlib import contextmanager

from blinkapp.config import Config
from blinkapp.models.types import (
    ApiResponse,
    FlaskResponse,
    P,
    T,
)

logger = logging.getLogger(__name__)

__all__ = [
    "error_context",
    "safe_execute",
    "ensure_blink_available",
    "check_blink_availability",
]


@contextmanager
def error_context(
    operation: str, reraise_as: type[Exception] | None = None
) -> Generator[None, None, None]:
    """Context manager for consistent error handling.

    Args:
        operation: Description of the operation being performed
        reraise_as: Exception type to reraise as (default: BlinkError)

    Yields:
        None: Context for the operation

    Raises:
        BlinkError: If the operation fails (or the specified reraise_as type)
    """
    # Import here to avoid circular dependency
    from blinkapp.utils.errors import BlinkError

    if reraise_as is None:
        reraise_as = BlinkError

    try:
        yield
    except Exception as e:
        logger.error(f"Error during {operation}: {e}")
        logger.debug(f"Full traceback for {operation}: {traceback.format_exc()}")
        if isinstance(e, BlinkError):
            raise
        raise reraise_as(f"Failed to {operation}: {str(e)}") from e


def safe_execute(
    func: Callable[[], T], default: T | None = None, log_error: bool = True
) -> T | None:
    """Execute function safely with error logging.

    Args:
        func: Function to execute safely
        default: Default value to return on exception
        log_error: Whether to log errors

    Returns:
        Function result or default value on exception
    """
    try:
        return func()
    except Exception as e:
        if log_error:
            logger.error(f"Safe execution failed: {e}")
            logger.debug(f"Full traceback: {traceback.format_exc()}")
        return default


def ensure_blink_available(
    func: Callable[P, T],
) -> Callable[P, T | FlaskResponse]:
    """Decorator that ensures blink is available before calling the function.

    This decorator automatically checks if the Blink system is initialized and
    available, returning an error response if not. It also serves as a type guard,
    telling type checkers that after the check, blink is guaranteed to be non-None.

    Usage in decorated functions:
        @ensure_blink_available
        def my_function() -> ResponseReturnValue:
            assert blink is not None  # For Pylance type narrowing
            return jsonify(blink.sync)  # No type errors
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | FlaskResponse:
        from flask import jsonify

        error_response = check_blink_availability()
        if error_response is not None:
            response, status_code = error_response
            return jsonify(response), status_code

        # Import blink here to avoid circular imports
        from blinkapp.services.blink_service import blink

        assert blink is not None  # Help type checkers understand this
        assert blink.available  # Additional assertion for Pylance

        return func(*args, **kwargs)

    return wrapper


def check_blink_availability() -> ApiResponse | None:
    """Check if Blink system is initialized and available.

    Returns:
        None if Blink is available, error response tuple if not initialized or unavailable
    """
    # Import here to avoid circular imports
    import blinkapp
    from blinkapp.services.blink_service import blink

    create_api_response = blinkapp.create_api_response

    if blink is None:
        return create_api_response(
            success=False,
            error=Config.ErrorMessages.SYSTEM_NOT_INITIALIZED,
            status_code=Config.HTTP_STATUS_INTERNAL_ERROR,
        )
    if not blink.available:
        return create_api_response(
            success=False,
            error=Config.ErrorMessages.AUTH_FAILED,
            status_code=401,
        )
    return None
