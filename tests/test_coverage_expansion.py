#!/usr/bin/env python3
"""
Coverage Expansion Tests - Simple working tests for uncovered code paths
"""

import os
import sys
import unittest

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestValidatorsExpansion(unittest.TestCase):
    """Test validators.py - expand coverage on working functions."""

    def test_extract_thumbnail_timestamp_with_ts(self):
        """Test timestamp extraction with ts parameter."""
        from blinkapp.utils.validators import extract_thumbnail_timestamp

        url = "http://example.com/thumb.jpg?ts=1640995200&ext="
        result = extract_thumbnail_timestamp(url)
        self.assertEqual(result, 1640995200)

    def test_format_time_ago_none_input(self):
        """Test format_time_ago with None input."""
        from blinkapp.utils.validators import format_time_ago

        result = format_time_ago(None)
        self.assertEqual(result, "Unknown")


class TestModelsIds(unittest.TestCase):
    """Test models/ids.py - expand coverage."""

    def test_clip_id_local_parts_error(self):
        """Test ClipId get_local_parts with cloud clip."""
        from blinkapp.models.ids import ClipId

        cloud_clip = ClipId("12345")  # Cloud clip format
        with self.assertRaises(ValueError):
            cloud_clip.get_local_parts()


class TestUtilsDecorators(unittest.TestCase):
    """Test utils/decorators.py - expand coverage."""

    def test_error_context_success(self):
        """Test error_context decorator with successful operation."""
        from blinkapp.utils.decorators import error_context

        @error_context("test operation")
        def test_func():
            return "success"

        result = test_func()
        self.assertEqual(result, "success")


class TestErrorClasses(unittest.TestCase):
    """Test utils/errors.py - expand coverage."""

    def test_authentication_error(self):
        """Test AuthenticationError creation."""
        from blinkapp.utils.errors import AuthenticationError

        error = AuthenticationError("Auth failed")
        self.assertEqual(str(error), "Auth failed")

    def test_cache_error(self):
        """Test CacheError creation."""
        from blinkapp.utils.errors import CacheError

        error = CacheError("Cache failed")
        self.assertEqual(str(error), "Cache failed")

    def test_validation_error(self):
        """Test ValidationError creation."""
        from blinkapp.utils.errors import ValidationError

        error = ValidationError("Validation failed")
        self.assertEqual(str(error), "Validation failed")


if __name__ == "__main__":
    unittest.main()
