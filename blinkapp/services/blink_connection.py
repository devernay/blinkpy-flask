"""Blink connection service for managing async operations.

This module provides a dedicated thread and event loop for handling all
Blink API operations asynchronously, ensuring thread safety and proper
resource management for the Flask application.

Key components:
- BlinkConnection: Main connection manager with dedicated thread
- Async operation execution with timeout handling
- Stream management for live video feeds
- Proper cleanup and shutdown procedures

The connection runs in its own thread to avoid blocking the Flask
request-response cycle while maintaining a persistent connection
to the Blink API servers.
"""

import asyncio
import concurrent.futures
import logging
import threading
from collections.abc import Coroutine
from typing import Any, TypeVar

from blinkapp.config import Config
from blinkapp.utils.errors import BlinkError

logger = logging.getLogger(__name__)

T = TypeVar("T")

__all__ = [
    "BlinkConnection",
    "initialize_blink_connection",
    "get_blink_connection",
    "shutdown_blink_connection",
]


class BlinkConnection:
    """Manages a single Blink connection with dedicated thread and event loop.

    This class provides thread-safe access to Blink API operations by running
    all async operations in a dedicated background thread. This prevents
    blocking the Flask application while maintaining persistent connections.

    Features:
    - Dedicated asyncio event loop in separate thread
    - Timeout handling for all operations
    - Stream management for live video feeds
    - Proper resource cleanup on shutdown
    """

    def __init__(self, timeout: int | None = None) -> None:
        """Initialize Blink connection manager.

        Args:
            timeout: Operation timeout in seconds (uses config default if None)
        """
        super().__init__()
        self.timeout: int = (
            timeout if timeout is not None else Config.BLINK_CONNECTION_TIMEOUT
        )
        self.thread: threading.Thread | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.blink: Any = None  # Blink instance from blinkpy library
        self._started: bool = False
        self._active_streams: dict[str, Any] = {}  # Track active video streams

    def start(self) -> None:
        """Start Blink thread and event loop."""
        if not self.thread or not self.thread.is_alive():

            def run_loop() -> None:
                """Run the asyncio event loop for Blink operations.

                This function runs indefinitely, processing async operations
                submitted to the Blink connection thread.
                """
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                self.loop.run_forever()

            self.thread = threading.Thread(target=run_loop, daemon=True)
            self.thread.start()
            import time

            time.sleep(0.1)
            self._started = True

    def execute(self, coro: Coroutine[Any, Any, T], timeout: int | None = None) -> T:
        """Execute async Blink operation in dedicated thread."""
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

    def cleanup_active_streams(self) -> None:
        """Clean up all active livestreams."""
        if not self._active_streams:
            return

        logger.info(f"Cleaning up {len(self._active_streams)} active streams")
        for stream_id, stream in list(self._active_streams.items()):
            try:
                stream.stop()
                logger.info(f"Stopped active livestream {stream_id}")
            except (AttributeError, RuntimeError, OSError) as e:
                logger.warning(f"Error stopping livestream {stream_id}: {e}")

        self._active_streams.clear()

    def shutdown(self) -> None:
        """Shutdown Blink connection and clean up resources."""
        self.cleanup_active_streams()

        if self.blink is not None:
            try:
                if self.loop and self.loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(
                        self.blink.close(), self.loop
                    )
                    future.result(timeout=Config.FUTURE_RESULT_TIMEOUT)
            except (TimeoutError, RuntimeError, OSError) as e:
                logger.debug(f"Session cleanup: {e}")

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
