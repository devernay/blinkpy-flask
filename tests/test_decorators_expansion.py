#!/usr/bin/env python3
"""Targeted tests for utils/decorators.py expansion - covering missed lines."""

import unittest

from blinkapp.utils.decorators import error_context, safe_execute
from blinkapp.utils.errors import BlinkError


class TestDecoratorsExpansion(unittest.TestCase):
    """Test uncovered decorator functions."""

    def test_error_context_success(self) -> None:
        """Test error_context decorator with successful execution."""
        with error_context("test operation"):
            result = "success"
        self.assertEqual(result, "success")

    def test_error_context_with_exception(self) -> None:
        """Test error_context decorator with exception."""
        with self.assertRaises(BlinkError):
            with error_context("test operation"):
                raise ValueError("test error")

    def test_safe_execute_success(self) -> None:
        """Test safe_execute with successful function."""

        def test_func() -> str:
            return "success"

        result = safe_execute(test_func, "test operation")
        self.assertEqual(result, "success")

    def test_safe_execute_with_exception(self) -> None:
        """Test safe_execute with exception."""

        def test_func() -> str:
            raise ValueError("test error")

        result = safe_execute(test_func, "test operation")
        self.assertEqual(result, "test operation")  # Returns operation name on error
