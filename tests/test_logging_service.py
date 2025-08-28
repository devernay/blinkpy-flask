"""Tests for logging_service module."""

import unittest
from unittest.mock import Mock, patch

from blinkapp.services.logging_service import (
    log_debug,
    log_error,
    log_info,
    log_warning,
)


class TestLoggingService(unittest.TestCase):
    """Test logging service functions."""

    def test_log_error_with_logger(self) -> None:
        """Test log error with custom logger."""
        mock_logger = Mock(spec=object)
        log_error("test error", mock_logger)
        mock_logger.assert_called_once_with("test error")

    def test_log_error_default_logger(self) -> None:
        """Test log error with default logger."""
        with patch("blinkapp.logger") as mock_logger:
            log_error("test error")
            mock_logger.error.assert_called_once_with("test error")

    def test_log_warning_with_logger(self) -> None:
        """Test log warning with custom logger."""
        mock_logger = Mock(spec=object)
        log_warning("test warning", mock_logger)
        mock_logger.assert_called_once_with("test warning")

    def test_log_warning_default_logger(self) -> None:
        """Test log warning with default logger."""
        with patch("blinkapp.logger") as mock_logger:
            log_warning("test warning")
            mock_logger.warning.assert_called_once_with("test warning")

    def test_log_info_with_logger(self) -> None:
        """Test log info with custom logger."""
        mock_logger = Mock(spec=object)
        log_info("test info", mock_logger)
        mock_logger.assert_called_once_with("test info")

    def test_log_info_default_logger(self) -> None:
        """Test log info with default logger."""
        with patch("blinkapp.logger") as mock_logger:
            log_info("test info")
            mock_logger.info.assert_called_once_with("test info")

    def test_log_debug_with_logger(self) -> None:
        """Test log debug with custom logger."""
        mock_logger = Mock(spec=object)
        log_debug("test debug", mock_logger)
        mock_logger.assert_called_once_with("test debug")

    def test_log_debug_default_logger(self) -> None:
        """Test log debug with default logger."""
        with patch("blinkapp.logger") as mock_logger:
            log_debug("test debug")
            mock_logger.debug.assert_called_once_with("test debug")


if __name__ == "__main__":
    unittest.main()
