"""Connection service for Blink Camera Flask application.

This module handles all connection-related business logic including
executor management, HTTP session management, and connection initialization.
"""

from __future__ import annotations

__all__ = [
    "initialize_connections",
    "ensure_executor_initialized",
    "ensure_http_session_initialized",
]

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    import requests

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


def ensure_executor_initialized():
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
