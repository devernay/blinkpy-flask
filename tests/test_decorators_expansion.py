#!/usr/bin/env python3
"""Targeted tests for utils/decorators.py expansion - covering missed lines."""

import unittest

from blinkapp.utils.decorators import safe_execute


class TestDecoratorsExpansion(unittest.TestCase):
    """Test uncovered decorator functions."""

    def test_safe_execute_with_exception_expansion(self) -> None:
        """Test safe_execute with exception - expansion version."""

        def expansion_test_func() -> str:
            raise ValueError("test error")

        result = safe_execute(expansion_test_func, "test operation")
        self.assertEqual(result, "test operation")  # Returns operation name on error
