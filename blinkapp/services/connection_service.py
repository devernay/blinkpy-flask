"""Connection service for Blink Camera Flask application.

This module handles all connection-related business logic including
executor management, HTTP session management, and connection initialization.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    import requests

from blinkapp.config import Config

__all__ = [
    "initialize_connections",
    "ensure_executor_initialized",
    "ensure_http_session_initialized",
    "BlinkError",
    "BlinkConnection",
    "blink_connection",
    "initialize_blink_connection",
    "get_blink_connection",
    "shutdown_blink_connection",
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
        "BlinkConnection",
        "blink_connection",
        "initialize_blink_connection",
        "get_blink_connection",
        "shutdown_blink_connection",
    ]
)


class BlinkError(Exception):
    """Base exception for Blink-related errors."""

    pass


class BlinkConnection:
    """Manages a single Blink connection with dedicated thread.

    Provides thread-safe access to Blink API operations by running all
    async operations in a dedicated event loop thread.
    """

    def __init__(self, timeout: int | None = None) -> None:
        """Initialize Blink connection.

        Args:
            timeout: Default timeout in seconds for Blink operations.
                    If None, uses Config.BLINK_CONNECTION_TIMEOUT
        """
        super().__init__()
        self.timeout: int = (
            timeout if timeout is not None else Config.BLINK_CONNECTION_TIMEOUT
        )
        self.thread: threading.Thread | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.blink: Any = None  # Blink instance
        self._started: bool = False
        self._active_streams: dict[str, Any] = {}

    def start(self) -> None:
        """Start Blink thread and event loop.

        Creates and starts a dedicated thread with asyncio event loop
        for handling all Blink API operations.

        Raises:
            BlinkError: If thread fails to start
        """
        if not self.thread or not self.thread.is_alive():

            def run_loop() -> None:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                self.loop.run_forever()

            self.thread = threading.Thread(target=run_loop, daemon=True)
            self.thread.start()
            import time

            time.sleep(0.1)
            self._started = True

    def execute(self, coro: Any, timeout: int | None = None) -> Any:
        """Execute async Blink operation in dedicated thread.

        Args:
            coro: Async coroutine to execute
            timeout: Operation timeout in seconds (uses default if None)

        Returns:
            Result of the async operation

        Raises:
            BlinkError: If connection not started or operation fails
        """
        if not self._started:
            raise BlinkError("Connection not started - call start() first")
        if not self.loop:
            raise BlinkError("Event loop not available")

        operation_timeout: int = timeout if timeout is not None else self.timeout

        try:
            future = asyncio.run_coroutine_threadsafe(coro, self.loop)
            return future.result(timeout=operation_timeout)
        except (TimeoutError, concurrent.futures.TimeoutError) as e:
            raise BlinkError(f"Blink operation timed out: {str(e)}") from e
        except (RuntimeError, OSError) as e:
            raise BlinkError(f"Blink operation failed: {str(e)}") from e

    def shutdown(self) -> None:
        """Shutdown Blink connection and clean up resources.

        Gracefully closes Blink session, stops event loop, and marks
        connection as not started.
        """
        # Close Blink session
        if self.blink is not None:
            try:
                if self.loop and self.loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(
                        self.blink.close(), self.loop
                    )
                    future.result(timeout=Config.FUTURE_RESULT_TIMEOUT)
            except (TimeoutError, RuntimeError, OSError) as e:
                logger.debug(f"Session cleanup: {e}")

        # Stop event loop
        if self.loop and self.loop.is_running():
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except (RuntimeError, OSError) as e:
                logger.error(f"Error stopping loop: {e}")

        self._started = False


# Global Blink connection instance
blink_connection: BlinkConnection | None = None


def initialize_blink_connection() -> None:
    """Initialize the global Blink connection."""
    global blink_connection
    if blink_connection is None:
        blink_connection = BlinkConnection()
        blink_connection.start()
        logger.info("Blink connection initialized")


def get_blink_connection() -> BlinkConnection | None:
    """Get the global Blink connection instance."""
    return blink_connection


def shutdown_blink_connection() -> None:
    """Shutdown the global Blink connection."""
    global blink_connection
    if blink_connection:
        blink_connection.shutdown()
        blink_connection = None
        logger.info("Blink connection shutdown")
