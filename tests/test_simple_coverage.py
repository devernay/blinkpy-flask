"""Simple tests to improve coverage without complex mocking."""

from .test_base import BaseTestCase


class TestSimpleCoverage(BaseTestCase):
    """Simple coverage improvement tests."""

    def test_decorators_basic_usage(self) -> None:
        """Test basic decorator usage."""
        from blinkapp.utils.decorators import error_context

        @error_context("test operation")
        def simple_test_function() -> str:
            return "success"

        result = simple_test_function()
        self.assertEqual(result, "success")


if __name__ == "__main__":
    import unittest

    unittest.main()
