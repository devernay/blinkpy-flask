#!/usr/bin/env python3
"""Final targeted tests for validators.py - covering the remaining missed lines."""

import unittest

from blinkapp.utils.formatters import format_time_ago


class TestValidatorsFinal(unittest.TestCase):
    """Test remaining uncovered validator functions."""

    def test_format_time_ago_unsupported_type(self) -> None:
        """Test format_time_ago with unsupported timestamp type."""
        result = format_time_ago({"invalid": "object"})  # type: ignore[arg-type]

        self.assertEqual(result, "Unknown")

    def test_format_time_ago_invalid_string(self) -> None:
        """Test format_time_ago with invalid string format."""
        result = format_time_ago("not_a_timestamp")

        self.assertEqual(result, "Unknown")

    def test_format_time_ago_exception_handling(self) -> None:
        """Test format_time_ago exception handling."""
        # Test with None to trigger exception path
        result = format_time_ago(None)

        self.assertEqual(result, "Unknown")
