"""Test coverage boost for device_service.py missed lines.

This test file specifically targets code paths that were missed by other test files
to improve overall test coverage. Each test focuses on edge cases, error conditions,
and boundary values that might not be covered in the main functional tests.

The tests are designed to:
1. Exercise exception handling paths
2. Test type conversion edge cases
3. Validate boundary conditions
4. Ensure proper fallback behavior
"""

import unittest

from blinkapp.services.device_service import (
    format_device_temperature,
)


class TestUtilsServiceBoost(unittest.TestCase):
    """Test utils service coverage boost.

    This test class focuses on improving code coverage by testing
    specific code paths that may be missed by functional tests.
    """

    def test_format_device_temperature_valid(self) -> None:
        """Test format_device_temperature with valid temperature.

        Tests the happy path where a valid numeric temperature is provided.
        This should convert the temperature to Fahrenheit format with proper units.
        """
        result = format_device_temperature(72.5)
        self.assertEqual(result, "72.5°F")

    def test_format_device_temperature_none(self) -> None:
        """Test format_device_temperature with None input.

        Tests the null handling path where None is passed as temperature.
        This should return the fallback value "N/A" without raising an exception.
        """
        result = format_device_temperature(None)
        self.assertEqual(result, "N/A")

    def test_format_device_temperature_invalid(self) -> None:
        """Test format_device_temperature with invalid string value.

        Tests the None input case.
        """
        result = format_device_temperature(None)
        self.assertEqual(result, "N/A")

    def test_format_device_temperature_float_input(self) -> None:
        """Test format_device_temperature with float input.

        Tests the normal path where a valid float is provided.
        """
        result = format_device_temperature(68.2)
        self.assertEqual(result, "68.2°F")

    def test_format_device_temperature_zero(self) -> None:
        """Test format_device_temperature with zero."""
        result = format_device_temperature(0)
        self.assertEqual(result, "0.0°F")

    def test_format_device_temperature_negative(self) -> None:
        """Test format_device_temperature with negative value."""
        result = format_device_temperature(-10)
        self.assertEqual(result, "-10.0°F")

    def test_format_device_temperature_int_input(self) -> None:
        """Test format_device_temperature with int input."""
        result = format_device_temperature(72)
        self.assertEqual(result, "72.0°F")


if __name__ == "__main__":
    unittest.main()
