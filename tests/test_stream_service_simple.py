#!/usr/bin/env python3
"""Simple tests for stream_service.py pure functions - targeting missed lines."""

import multiprocessing
import unittest
from unittest.mock import Mock, patch

from blinkapp.services.stream_service import (
    ensure_stream_manager_initialized,
    generate_hls_url,
    parse_tcp_url,
    validate_camera_id,
    validate_tcp_url,
)

from .test_base import BaseTestCase, create_mock_stream_manager

try:
    from blinkapp.services.stream_manager import StreamManager
except ImportError:
    # Create a mock class for testing if StreamManager is not available
    class StreamManager:
        pass


class TestStreamServiceSimple(BaseTestCase):
    """Test stream service pure functions."""

    def test_parse_tcp_url_empty_string(self) -> None:
        """Test parse_tcp_url with empty string input.

        Why: Empty strings are common edge cases that can cause crashes if not handled.
        What: Verifies that parse_tcp_url raises ValueError with descriptive message.
        How: Passes empty string and checks exception type and message content.
        """
        # Should raise ValueError for empty string
        with self.assertRaises(ValueError) as context:
            parse_tcp_url("")

        self.assertIn("Invalid TCP URL format", str(context.exception))

    def test_parse_tcp_url_none(self) -> None:
        """Test parse_tcp_url with None input.

        Why: None values can be passed from uninitialized variables or API responses.
        What: Verifies function handles None gracefully by raising AttributeError.
        How: Uses cast to bypass type checking and test runtime behavior.
        """
        from typing import cast

        # Should raise AttributeError for None input
        with self.assertRaises(AttributeError):
            parse_tcp_url(cast(str, None))  # Intentionally testing invalid input

    def test_parse_tcp_url_valid_url(self) -> None:
        """Test parse_tcp_url with valid TCP URL.

        Why: This is the primary happy path for TCP URL parsing in live streaming.
        What: Verifies correct parsing of host and port from TCP URL format.
        How: Passes valid TCP URL and validates returned tuple structure and values.
        """
        result = parse_tcp_url("tcp://192.168.1.100:8080")

        # Should parse URL components correctly
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        host, port = result
        self.assertEqual(host, "192.168.1.100")
        self.assertEqual(port, 8080)

    def test_parse_tcp_url_invalid_url(self) -> None:
        """Test parse_tcp_url with malformed URL input.

        Why: Invalid URLs from user input or corrupted data should be handled gracefully.
        What: Verifies function raises ValueError with descriptive error message.
        How: Passes malformed URL string and validates exception handling.
        """
        # Should raise ValueError for invalid URL format
        with self.assertRaises(ValueError) as context:
            parse_tcp_url("invalid_url")

        self.assertIn("Invalid TCP URL format", str(context.exception))

    def test_generate_hls_url_default_base(self) -> None:
        """Test HLS URL generation for web streaming.

        Why: HLS URLs are critical for serving live camera streams to web browsers.
        What: Verifies correct API endpoint URL construction for HLS streaming.
        How: Passes camera ID and playlist filename, validates returned URL format.
        """
        result = generate_hls_url("camera123", "playlist.m3u8")

        # Should return relative API URL for HLS streaming
        self.assertEqual(result, "/api/cameras/camera123/streams/playlist.m3u8")

    def test_generate_hls_url_custom_base(self) -> None:
        """Test generate_hls_url with custom filename - line 105."""
        result = generate_hls_url("camera456", "custom_stream.m3u8")

        # Should return relative API URL with custom filename
        self.assertEqual(result, "/api/cameras/camera456/streams/custom_stream.m3u8")

    def test_validate_camera_id_valid(self) -> None:
        """Test validate_camera_id with valid ID - line 110."""
        result = validate_camera_id("camera123")

        # Should return True for valid ID
        self.assertTrue(result)

    def test_validate_tcp_url_valid_tcp(self) -> None:
        """Test validate_tcp_url with valid TCP URL - line 115."""
        result = validate_tcp_url("tcp://192.168.1.100:8080")

        # Should return True for valid TCP URL
        self.assertTrue(result)

    def test_validate_tcp_url_valid_http(self) -> None:
        """Test TCP URL validation rejects HTTP URLs.

        Why: Stream service specifically requires TCP protocol for camera connections.
        What: Verifies validation correctly rejects HTTP URLs as invalid for streaming.
        How: Passes HTTP URL and expects False return value.
        """
        result = validate_tcp_url("http://192.168.1.100:8080")

        # Should return False for HTTP URL (TCP protocol required)
        self.assertFalse(result)

    def test_validate_tcp_url_invalid(self) -> None:
        """Test validate_tcp_url with invalid URL - line 115."""
        result = validate_tcp_url("ftp://example.com")

        # Should return False for invalid protocol
        self.assertFalse(result)

    def test_validate_tcp_url_empty(self) -> None:
        """Test validate_tcp_url with empty string - line 115."""
        result = validate_tcp_url("")

        # Should return False for empty string
        self.assertFalse(result)

    def test_validate_tcp_url_none(self) -> None:
        """Test validate_tcp_url with None - line 115."""
        from typing import cast

        result = validate_tcp_url(
            cast(str, None)
        )  # Intentionally testing invalid input

        # Should return False for None
        self.assertFalse(result)

    def test_ensure_stream_manager_initialized_no_manager(self) -> None:
        """Test stream manager initialization failure handling.

        Why: Stream manager is critical for live streaming - failures must be handled gracefully.
        What: Verifies proper error handling when stream manager initialization fails.
        How: Mocks missing stream manager and validates RuntimeError with descriptive message.
        """
        # Mock the global stream_manager to be None
        with patch("blinkapp.services.stream_service.stream_manager", None):
            mock_factory = Mock()  # Factory function
            mock_manager = Mock(spec=multiprocessing.Manager)
            mock_factory.return_value = mock_manager

            # Should raise RuntimeError when no manager exists
            with self.assertRaises(RuntimeError) as context:
                ensure_stream_manager_initialized(mock_factory)

            # Should contain expected error message
            self.assertIn("Stream manager not initialized", str(context.exception))

    def test_ensure_stream_manager_initialized_existing_manager(self) -> None:
        """Test stream manager reuse when already initialized.

        Why: Avoids unnecessary reinitialization of expensive multiprocessing resources.
        What: Verifies existing stream manager is returned without creating new instance.
        How: Mocks existing manager and validates factory is not called.
        """
        mock_existing_manager = create_mock_stream_manager()

        # Mock the global stream_manager to exist
        with patch(
            "blinkapp.services.stream_service.stream_manager", mock_existing_manager
        ):
            mock_factory = Mock()  # Factory function

            result = ensure_stream_manager_initialized(mock_factory)

            # Should return existing manager without calling factory
            mock_factory.assert_not_called()
            self.assertEqual(result, mock_existing_manager)


if __name__ == "__main__":
    unittest.main()
