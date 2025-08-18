#!/usr/bin/env python3
"""Tests for utils_service.py - utility functions."""

import unittest

from blinkapp.services.utils_service import (
    format_battery_level,
    format_device_temperature,
)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions with pure function approach."""

    def test_format_device_temperature_valid(self):
        """Test temperature formatting with valid values."""
        self.assertEqual(format_device_temperature(72.5), "72.5°F")
        self.assertEqual(format_device_temperature("68"), "68.0°F")
        self.assertEqual(format_device_temperature(0), "0.0°F")

    def test_format_device_temperature_invalid(self):
        """Test temperature formatting with invalid values."""
        self.assertEqual(format_device_temperature(None), "N/A")
        self.assertEqual(format_device_temperature("invalid"), "N/A")
        self.assertEqual(format_device_temperature(""), "N/A")

    def test_format_battery_level_good(self):
        """Test battery level formatting - good range."""
        self.assertEqual(format_battery_level(130), "Good")
        self.assertEqual(format_battery_level("125"), "Good")
        self.assertEqual(format_battery_level(121), "Good")

    def test_format_battery_level_fair(self):
        """Test battery level formatting - fair range."""
        self.assertEqual(format_battery_level(115), "Fair")
        self.assertEqual(format_battery_level("111"), "Fair")
        self.assertEqual(format_battery_level(120), "Fair")

    def test_format_battery_level_low(self):
        """Test battery level formatting - low range."""
        self.assertEqual(format_battery_level(105), "Low")
        self.assertEqual(format_battery_level("100"), "Low")
        self.assertEqual(format_battery_level(110), "Low")

    def test_format_battery_level_invalid(self):
        """Test battery level formatting with invalid values."""
        self.assertEqual(format_battery_level(None), "N/A")
        self.assertEqual(format_battery_level("invalid"), "N/A")
        self.assertEqual(format_battery_level(""), "N/A")
