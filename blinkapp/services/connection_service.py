"""Connection service for Blink Camera Flask application.

This module handles all connection-related business logic including
executor management, HTTP session management, and connection initialization.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    import requests


T = TypeVar("T")

__all__ = [
    "initialize_connections",
    "ensure_executor_initialized",
    "ensure_http_session_initialized",
    "executor",  # Global executor instance used in tests
]

logger = logging.getLogger(__name__)

# Global connection instances
executor: ThreadPoolExecutor | None = None
http_session: requests.Session | None = None


def initialize_connections() -> None:
    """Initialize the global connection instances."""
    global executor, http_session
    from concurrent.futures import ThreadPoolExecutor

    import requests

    executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="blink-")
    http_session = requests.Session()


def ensure_executor_initialized() -> ThreadPoolExecutor:
    """Ensure executor is initialized.

    Returns:
        Initialized executor instance

    Raises:
        RuntimeError: If executor hasn't been initialized
    """
    if executor is None:
        raise RuntimeError(
            "Executor not initialized. Call initialize_connections() first."
        )
    return executor


def ensure_http_session_initialized():
    """Ensure HTTP session is initialized.

    Returns:
        Initialized HTTP session instance

    Raises:
        RuntimeError: If http_session hasn't been initialized
    """
    if http_session is None:
        raise RuntimeError(
            "HTTP session not initialized. Call initialize_connections() first."
        )
    return http_session


# ============================================================================
# Blink Connection Management (merged from blink_connection.py)
# ============================================================================

"""Blink connection management module.

Provides thread-safe access to Blink API operations through a dedicated
event loop thread. Ensures all async Blink operations are properly isolated
from the main Flask application thread.

Classes:
    BlinkConnection: Manages single Blink connection with dedicated thread
    BlinkError: Base exception for Blink-related errors

Usage:
    connection = BlinkConnection(timeout=Config.BLINK_CONNECTION_TIMEOUT)
    connection.start()
    result = connection.execute(some_async_operation())
    connection.shutdown()
"""


# Add to exports
__all__.extend(
    [
        "BlinkError",
    ]
)


class BlinkError(Exception):
    """Base exception for Blink-related errors."""

    pass
