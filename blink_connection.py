"""Blink connection management module.

Provides thread-safe access to Blink API operations through a dedicated
event loop thread. Ensures all async Blink operations are properly isolated
from the main Flask application thread.

Classes:
    BlinkConnection: Manages single Blink connection with dedicated thread
    BlinkError: Base exception for Blink-related errors

Usage:
    connection = BlinkConnection(timeout=30)
    connection.start()
    result = connection.execute(some_async_operation())
    connection.shutdown()
"""

import asyncio
import concurrent.futures
import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)


class BlinkError(Exception):
    """Base exception for Blink-related errors.

    Raised when Blink operations fail, including connection issues,
    API timeouts, and thread management problems.
    """

    pass


class BlinkConnection:
    """Manages a single Blink connection with dedicated thread.

    Provides thread-safe access to Blink API operations by running all
    async operations in a dedicated event loop thread.
    """

    def __init__(self, timeout: int = 30) -> None:
        """Initialize Blink connection.

        Args:
            timeout: Default timeout in seconds for Blink operations
        """
        self.timeout: int = timeout
        self.thread: threading.Thread | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.blink: Any | None = None
        self._started: bool = False

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
        except (asyncio.TimeoutError, concurrent.futures.TimeoutError) as e:
            raise BlinkError(f"Blink operation timed out: {str(e)}") from e
        except (RuntimeError, OSError) as e:
            raise BlinkError(f"Blink operation failed: {str(e)}") from e

    def shutdown(self) -> None:
        """Shutdown Blink connection and clean up resources.

        Gracefully closes Blink session, stops event loop, and marks
        connection as not started.
        """
        # Close Blink session
        if self.blink:
            try:
                if hasattr(self.blink, "close") and callable(self.blink.close):
                    if self.loop and self.loop.is_running():
                        future = asyncio.run_coroutine_threadsafe(
                            self.blink.close(), self.loop
                        )
                        future.result(timeout=2)
            except (asyncio.TimeoutError, RuntimeError, OSError) as e:
                logger.debug(f"Session cleanup: {e}")

        # Stop event loop
        if self.loop and self.loop.is_running():
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except (RuntimeError, OSError) as e:
                logger.error(f"Error stopping loop: {e}")

        self._started = False
