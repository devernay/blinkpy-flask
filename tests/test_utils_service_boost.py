"""Test coverage boost for utils_service.py missed lines."""

import unittest

from blinkapp.services.utils_service import (
    format_device_temperature,
)


class TestUtilsServiceBoost(unittest.TestCase):
    """Test utils service coverage boost."""

    def test_format_device_temperature_valid(self) -> None:
        """Test format_device_temperature with valid temperature."""
        result = format_device_temperature(72.5)
        self.assertEqual(result, "72.5°F")

    def test_format_device_temperature_none(self) -> None:
        """Test format_device_temperature with None."""
        result = format_device_temperature(None)
        self.assertEqual(result, "N/A")

    def test_format_device_temperature_invalid(self) -> None:
        """Test format_device_temperature with invalid value."""
        result = format_device_temperature("invalid")
        self.assertEqual(result, "N/A")

    def test_format_device_temperature_string_number(self) -> None:
        """Test format_device_temperature with string number."""
        result = format_device_temperature("68.2")
        self.assertEqual(result, "68.2°F")

    def test_format_device_temperature_zero(self) -> None:
        """Test format_device_temperature with zero."""
        result = format_device_temperature(0)
        self.assertEqual(result, "0.0°F")

    def test_format_device_temperature_negative(self) -> None:
        """Test format_device_temperature with negative value."""
        result = format_device_temperature(-10)
        self.assertEqual(result, "-10.0°F")

    def test_format_device_temperature_type_error(self) -> None:
        """Test format_device_temperature with TypeError."""
        result = format_device_temperature([1, 2, 3])
        self.assertEqual(result, "N/A")


if __name__ == "__main__":
    unittest.main()
