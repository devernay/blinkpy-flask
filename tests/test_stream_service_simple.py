#!/usr/bin/env python3
"""Simple tests for stream_service.py pure functions - targeting missed lines."""

import unittest
from unittest.mock import Mock, patch

from blinkapp.services.stream_service import (
    ensure_stream_manager_initialized,
    generate_hls_url,
    parse_tcp_url,
    validate_camera_id,
    validate_tcp_url,
)


class TestStreamServiceSimple(unittest.TestCase):
    """Test stream service pure functions."""

    def test_parse_tcp_url_empty_string(self) -> None:
        """Test parse_tcp_url with empty string - line 88."""
        result = parse_tcp_url("")

        # Should return empty dict for empty string
        self.assertEqual(result, {})

    def test_parse_tcp_url_none(self) -> None:
        """Test parse_tcp_url with None - line 88."""
        result = parse_tcp_url(None)  # type: ignore[arg-type]

        # Should return empty dict for None
        self.assertEqual(result, {})

    def test_parse_tcp_url_valid_url(self) -> None:
        """Test parse_tcp_url with valid URL - lines 90-100."""
        result = parse_tcp_url("tcp://192.168.1.100:8080")

        # Should parse URL components
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        host, port = result
        self.assertEqual(host, "192.168.1.100")
        self.assertEqual(port, 8080)

    def test_parse_tcp_url_invalid_url(self) -> None:
        """Test parse_tcp_url with invalid URL - exception handling."""
        result = parse_tcp_url("invalid_url")

        # Should return empty dict for invalid URL
        self.assertEqual(result, {})

    def test_generate_hls_url_default_base(self) -> None:
        """Test generate_hls_url with default base URL - line 105."""
        result = generate_hls_url("camera123", "playlist.m3u8")

        # Should use default base URL
        self.assertEqual(result, "http://localhost:8080/hls/camera123/playlist.m3u8")

    def test_generate_hls_url_custom_base(self) -> None:
        """Test generate_hls_url with custom base URL - line 105."""
        result = generate_hls_url("camera456", "http://example.com:9000")

        # Should use custom base URL
        self.assertEqual(result, "http://example.com:9000/hls/camera456/playlist.m3u8")

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
        """Test validate_tcp_url with valid HTTP URL - line 115."""
        result = validate_tcp_url("http://192.168.1.100:8080")

        # Should return True for valid HTTP URL
        self.assertTrue(result)

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
        result = validate_tcp_url(None)  # type: ignore[arg-type]

        # Should return False for None
        self.assertFalse(result)

    def test_ensure_stream_manager_initialized_no_manager(self) -> None:
        """Test ensure_stream_manager_initialized when no manager exists - lines 75-82."""
        # Mock the global stream_manager to be None
        with patch("blinkapp.services.stream_service.stream_manager", None):
            mock_factory = Mock()
            mock_manager = Mock()
            mock_factory.return_value = mock_manager

            # Should raise RuntimeError when no manager exists
            with self.assertRaises(RuntimeError) as context:
                ensure_stream_manager_initialized(mock_factory)

            # Should contain expected error message
            self.assertIn("Stream manager not initialized", str(context.exception))

    def test_ensure_stream_manager_initialized_existing_manager(self) -> None:
        """Test ensure_stream_manager_initialized when manager exists - line 73."""
        mock_existing_manager = Mock()

        # Mock the global stream_manager to exist
        with patch(
            "blinkapp.services.stream_service.stream_manager", mock_existing_manager
        ):
            mock_factory = Mock()

            result = ensure_stream_manager_initialized(mock_factory)

            # Should return existing manager without calling factory
            mock_factory.assert_not_called()
            self.assertEqual(result, mock_existing_manager)


if __name__ == "__main__":
    unittest.main()
