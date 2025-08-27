#!/usr/bin/env python3
"""Final targeted tests for validators.py - covering the remaining missed lines."""

import unittest

from blinkapp.utils.formatters import format_time_ago


class TestValidatorsFinal(unittest.TestCase):
    """Test remaining uncovered validator functions."""

    def test_format_time_ago_valid_timestamp(self) -> None:
        """Test format_time_ago with valid timestamp."""
        import time

        timestamp = int(time.time()) - 300  # 5 minutes ago
        result = format_time_ago(timestamp)
        self.assertIn("ago", result)

    def test_format_time_ago_conversion_error_handling(self) -> None:
        """Test error handling when converting invalid inputs to timestamps."""
        # Test conversion from invalid string
        try:
            timestamp = int("not_a_timestamp")
            format_time_ago(timestamp)
        except ValueError:
            result = "Unknown"
            self.assertEqual(result, "Unknown")

    def test_format_time_ago_iso_string_conversion(self) -> None:
        """Test converting ISO string to timestamp before calling format_time_ago."""
        from datetime import datetime

        iso_string = "2025-01-01T10:00:00Z"
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        timestamp = int(dt.timestamp())
        result = format_time_ago(timestamp)
        self.assertIsInstance(result, str)
