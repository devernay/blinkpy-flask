#!/usr/bin/env python3
"""Tests for decorators.py simple functions - targeting missed lines."""

import unittest

from blinkapp.utils.decorators import (
    safe_execute,
)
from blinkapp.utils.route_decorators import (
    _get_operation_name,
    _is_error_response,
)


class TestDecoratorsSimple(unittest.TestCase):
    """Test decorators simple functions."""

    def test_safe_execute_exception_with_default(self) -> None:
        """Test safe_execute with exception and default - lines 102-107."""

        def failing_func():
            raise ValueError("Test error")

        result = safe_execute(failing_func, default="default_value")

        # Should return default value
        self.assertEqual(result, "default_value")

    def test_safe_execute_exception_no_default(self) -> None:
        """Test safe_execute with exception and no default - lines 102-107."""

        def failing_func():
            raise ValueError("Test error")

        result = safe_execute(failing_func)

        # Should return None
        self.assertIsNone(result)

    def test_safe_execute_exception_no_logging(self) -> None:
        """Test safe_execute with exception and no logging - lines 102-107."""

        def failing_func():
            raise ValueError("Test error")

        result = safe_execute(failing_func, log_error=False)

        # Should return None
        self.assertIsNone(result)

    def test_get_operation_name_with_provided_name(self) -> None:
        """Test _get_operation_name with provided name - line 218."""

        def test_func() -> None:
            pass

        result = _get_operation_name(test_func, "custom_operation")

        # Should return provided name
        self.assertEqual(result, "custom_operation")

    def test_get_operation_name_without_provided_name(self) -> None:
        """Test _get_operation_name without provided name - line 219."""

        def test_func() -> None:
            pass

        result = _get_operation_name(test_func)

        # Should return function name with underscores replaced by spaces
        self.assertEqual(result, "test func")

    def test_is_error_response_with_response_object(self) -> None:
        """Test _is_error_response with Response object - line 453."""
        from flask import Response

        mock_response = Response("test")
        result = _is_error_response(mock_response)

        # Should return True for Response object
        self.assertTrue(result)

    def test_is_error_response_with_tuple(self) -> None:
        """Test _is_error_response with tuple - line 453."""
        result = _is_error_response(("error", 400))

        # Should return True for tuple
        self.assertTrue(result)

    def test_is_error_response_with_dict(self) -> None:
        """Test _is_error_response with dict - line 453."""
        result = _is_error_response({"error": "test"})

        # Should return False for dict
        self.assertFalse(result)

    def test_is_error_response_with_string(self) -> None:
        """Test _is_error_response with string - line 453."""
        result = _is_error_response("test")

        # Should return False for string
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
