"""Targeted tests for connection_service.py to improve coverage."""

import unittest
from asyncio import AbstractEventLoop
from concurrent.futures import Future
from unittest.mock import AsyncMock, Mock, patch

from blinkapp.services.blink_connection import BlinkConnection
from blinkapp.services.connection_service import (
    ensure_executor_initialized,
    ensure_http_session_initialized,
)

from .test_base import (
    create_mock_blink_instance,
    create_mock_live_stream,
)


class TestConnectionServiceTargeted(unittest.TestCase):
    """Test connection service functions for coverage improvement."""

    def test_blink_connection_cleanup_streams_error(self) -> None:
        """Test BlinkConnection cleanup with stream error - lines 216-218."""
        connection = BlinkConnection()

        # Mock stream that raises error on stop
        mock_stream = create_mock_live_stream(
            stream_id="stream1", stop_error=RuntimeError("Stream error")
        )
        connection._active_streams = {"stream1": mock_stream}

        with patch("blinkapp.services.blink_connection.logger") as mock_logger:
            connection.cleanup_active_streams()

            # Should log warning about stream error
            mock_logger.warning.assert_called()
            # Should clear streams despite error
            self.assertEqual(len(connection._active_streams), 0)

    def test_blink_connection_shutdown_timeout_error(self) -> None:
        """Test BlinkConnection shutdown with timeout - lines 233-240."""
        connection = BlinkConnection()
        connection.blink = create_mock_blink_instance()
        connection.blink.close = AsyncMock()
        connection.loop = Mock(spec=AbstractEventLoop)
        connection.loop.is_running.return_value = True

        with (
            patch("asyncio.run_coroutine_threadsafe") as mock_run_coro,
            patch("blinkapp.services.blink_connection.logger") as mock_logger,
        ):
            # Mock future that times out
            mock_future = Mock(spec=Future)
            mock_future.result.side_effect = TimeoutError("Timeout")
            mock_run_coro.return_value = mock_future

            connection.shutdown()

            # Should handle timeout gracefully
            mock_logger.debug.assert_called()

    def test_blink_connection_shutdown_runtime_error(self) -> None:
        """Test BlinkConnection shutdown with runtime error - lines 233-240."""
        connection = BlinkConnection()
        connection.blink = create_mock_blink_instance()
        connection.blink.close = AsyncMock()
        connection.loop = Mock(spec=AbstractEventLoop)
        connection.loop.is_running.return_value = True

        with (
            patch("asyncio.run_coroutine_threadsafe") as mock_run_coro,
            patch("blinkapp.services.blink_connection.logger") as mock_logger,
        ):
            # Mock future that raises runtime error
            mock_future = Mock(spec=Future)
            mock_future.result.side_effect = RuntimeError("Runtime error")
            mock_run_coro.return_value = mock_future

            connection.shutdown()

            # Should handle runtime error gracefully
            mock_logger.debug.assert_called()

    def test_blink_connection_shutdown_os_error(self) -> None:
        """Test BlinkConnection shutdown with OS error - lines 233-240."""
        connection = BlinkConnection()
        connection.blink = create_mock_blink_instance()
        connection.blink.close = AsyncMock()
        connection.loop = Mock(spec=AbstractEventLoop)
        connection.loop.is_running.return_value = True

        with (
            patch("asyncio.run_coroutine_threadsafe") as mock_run_coro,
            patch("blinkapp.services.blink_connection.logger") as mock_logger,
        ):
            # Mock future that raises OS error
            mock_future = Mock(spec=Future)
            mock_future.result.side_effect = OSError("OS error")
            mock_run_coro.return_value = mock_future

            connection.shutdown()

            # Should handle OS error gracefully
            mock_logger.debug.assert_called()

    def test_ensure_executor_initialized_already_exists(self) -> None:
        """Test ensure_executor_initialized when executor already exists."""
        # Mock the global executor variable directly
        with patch(
            "blinkapp.services.connection_service.executor", "existing_executor"
        ):
            result = ensure_executor_initialized()
            # Should return existing executor
            self.assertEqual(result, "existing_executor")

    def test_ensure_executor_initialized_create_new(self) -> None:
        """Test ensure_executor_initialized creates new executor."""
        # Test that it raises RuntimeError when executor is None
        with patch("blinkapp.services.connection_service.executor", None):
            with self.assertRaises(RuntimeError) as context:
                ensure_executor_initialized()
            self.assertIn("Executor not initialized", str(context.exception))

    def test_ensure_http_session_initialized_already_exists(self) -> None:
        """Test ensure_http_session_initialized when session already exists."""
        # Mock the global http_session variable directly
        with patch(
            "blinkapp.services.connection_service.http_session", "existing_session"
        ):
            result = ensure_http_session_initialized()
            # Should return existing session
            self.assertEqual(result, "existing_session")

    def test_ensure_http_session_initialized_create_new(self) -> None:
        """Test ensure_http_session_initialized creates new session."""
        # Test that it raises RuntimeError when http_session is None
        with patch("blinkapp.services.connection_service.http_session", None):
            with self.assertRaises(RuntimeError) as context:
                ensure_http_session_initialized()
            self.assertIn("HTTP session not initialized", str(context.exception))


if __name__ == "__main__":
    unittest.main()
