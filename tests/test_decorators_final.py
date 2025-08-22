"""Final test coverage for decorators.py missed lines."""

import unittest

from blinkapp.utils.decorators import (
    error_context,
    safe_execute,
)


class TestDecoratorsFinal(unittest.TestCase):
    """Final decorators coverage tests."""

    def test_error_context_basic(self) -> None:
        """Test error_context basic functionality."""
        with error_context("test operation"):
            pass  # Should not raise

    def test_error_context_custom_exception(self) -> None:
        """Test error_context with custom exception type."""
        from blinkapp.utils.errors import ValidationError

        with self.assertRaises(ValidationError):
            with error_context("test operation", ValidationError):
                raise ValueError("Test error")

    def test_safe_execute_exception(self) -> None:
        """Test safe_execute with exception."""

        def test_func() -> str:
            raise ValueError("Test error")

        result = safe_execute(test_func, "default_value")

        self.assertEqual(result, "default_value")

    def test_safe_execute_no_logging(self) -> None:
        """Test safe_execute with no logging."""

        def test_func() -> str:
            raise ValueError("Test error")

        result = safe_execute(test_func, "default_value", log_error=False)

        self.assertEqual(result, "default_value")


if __name__ == "__main__":
    unittest.main()
