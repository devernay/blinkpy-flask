"""Test coverage boost for utils_service.py missed lines."""

import unittest

from blinkapp.services.utils_service import (
    format_battery_level,
    format_device_temperature,
)


class TestUtilsServiceBoost(unittest.TestCase):
    """Test utils service coverage boost."""

    def test_format_device_temperature_valid(self):
        """Test format_device_temperature with valid temperature."""
        result = format_device_temperature(72.5)
        self.assertEqual(result, "72.5°F")

    def test_format_device_temperature_none(self):
        """Test format_device_temperature with None."""
        result = format_device_temperature(None)
        self.assertEqual(result, "N/A")

    def test_format_device_temperature_invalid(self):
        """Test format_device_temperature with invalid value."""
        result = format_device_temperature("invalid")
        self.assertEqual(result, "N/A")

    def test_format_device_temperature_string_number(self):
        """Test format_device_temperature with string number."""
        result = format_device_temperature("68.2")
        self.assertEqual(result, "68.2°F")

    def test_format_device_temperature_zero(self):
        """Test format_device_temperature with zero."""
        result = format_device_temperature(0)
        self.assertEqual(result, "0.0°F")

    def test_format_device_temperature_negative(self):
        """Test format_device_temperature with negative value."""
        result = format_device_temperature(-10)
        self.assertEqual(result, "-10.0°F")

    def test_format_device_temperature_type_error(self):
        """Test format_device_temperature with TypeError."""
        result = format_device_temperature([1, 2, 3])
        self.assertEqual(result, "N/A")

    def test_format_battery_level_good(self):
        """Test format_battery_level with good voltage."""
        result = format_battery_level(125)
        self.assertEqual(result, "Good")

    def test_format_battery_level_fair(self):
        """Test format_battery_level with fair voltage."""
        result = format_battery_level(115)
        self.assertEqual(result, "Fair")

    def test_format_battery_level_low(self):
        """Test format_battery_level with low voltage."""
        result = format_battery_level(105)
        self.assertEqual(result, "Low")

    def test_format_battery_level_none(self):
        """Test format_battery_level with None."""
        result = format_battery_level(None)
        self.assertEqual(result, "N/A")

    def test_format_battery_level_invalid(self):
        """Test format_battery_level with invalid value."""
        result = format_battery_level("invalid")
        self.assertEqual(result, "N/A")

    def test_format_battery_level_string_number(self):
        """Test format_battery_level with string number."""
        result = format_battery_level("120")
        self.assertEqual(result, "Fair")

    def test_format_battery_level_boundary_good(self):
        """Test format_battery_level at good boundary."""
        result = format_battery_level(121)  # Just above 120
        self.assertEqual(result, "Good")

    def test_format_battery_level_boundary_fair(self):
        """Test format_battery_level at fair boundary."""
        result = format_battery_level(111)  # Just above 110
        self.assertEqual(result, "Fair")

    def test_format_battery_level_boundary_low(self):
        """Test format_battery_level at low boundary."""
        result = format_battery_level(110)  # Exactly 110
        self.assertEqual(result, "Low")

    def test_format_battery_level_exact_120(self):
        """Test format_battery_level at exact 120 boundary."""
        result = format_battery_level(120)
        self.assertEqual(result, "Fair")

    def test_format_battery_level_type_error(self):
        """Test format_battery_level with TypeError."""
        result = format_battery_level([1, 2, 3])
        self.assertEqual(result, "N/A")

    def test_format_battery_level_negative(self):
        """Test format_battery_level with negative value."""
        result = format_battery_level(-50)
        self.assertEqual(result, "Low")

    def test_format_battery_level_zero(self):
        """Test format_battery_level with zero."""
        result = format_battery_level(0)
        self.assertEqual(result, "Low")


if __name__ == "__main__":
    unittest.main()
