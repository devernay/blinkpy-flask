"""Tests for time_service module."""

import unittest
from unittest.mock import Mock

from blinkapp.services.time_service import (
    format_timestamp,
    get_current_time,
    get_current_timestamp,
)


class TestTimeService(unittest.TestCase):
    """Test time service functions."""

    def test_get_current_timestamp_with_provider(self) -> None:
        """Test get current timestamp with custom provider."""
        mock_provider = Mock(return_value=1234567890)
        result = get_current_timestamp(mock_provider)
        self.assertEqual(result, 1234567890)
        mock_provider.assert_called_once()

    def test_get_current_timestamp_default_provider(self) -> None:
        """Test get current timestamp with default provider."""
        result = get_current_timestamp()
        self.assertIsInstance(result, int)
        self.assertGreater(result, 0)

    def test_format_timestamp_with_formatter(self) -> None:
        """Test format timestamp with custom formatter."""
        mock_formatter = Mock(return_value="formatted")
        result = format_timestamp(1234567890, mock_formatter)
        self.assertEqual(result, "formatted")
        mock_formatter.assert_called_once_with(1234567890)

    def test_format_timestamp_default_formatter(self) -> None:
        """Test format timestamp with default formatter."""
        result = format_timestamp(1234567890)
        self.assertIsInstance(result, str)
        # Should contain time ago format
        self.assertTrue(any(char in result for char in "dhms"))

    def test_get_current_time_with_provider(self) -> None:
        """Test get current time with custom provider."""
        from datetime import datetime

        mock_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_provider = Mock(return_value=mock_time)
        result = get_current_time(mock_provider)
        self.assertEqual(result, mock_time)
        mock_provider.assert_called_once()

    def test_get_current_time_default_provider(self) -> None:
        """Test get current time with default provider."""
        from datetime import datetime

        result = get_current_time()
        self.assertIsInstance(result, datetime)
        # Should be recent
        self.assertGreater(result.year, 2020)


if __name__ == "__main__":
    unittest.main()
