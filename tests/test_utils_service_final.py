"""Final test coverage for utils_service.py missed lines."""

import unittest
from unittest.mock import Mock

from blinkapp.services.device_service import (
    create_device_data,
    format_battery_level,
    format_device_temperature,
)


class TestUtilsServiceFinal(unittest.TestCase):
    """Final utils service coverage tests."""

    def test_format_device_temperature_basic(self) -> None:
        """Test format_device_temperature basic functionality."""
        result = format_device_temperature(68.5)
        self.assertEqual(result, "68.5°F")

    def test_format_battery_level_good(self) -> None:
        """Test format_battery_level with good level."""
        result = format_battery_level(125)
        self.assertEqual(result, "Good")

    def test_format_battery_level_fair(self) -> None:
        """Test format_battery_level with fair level."""
        result = format_battery_level(115)
        self.assertEqual(result, "Fair")

    def test_format_battery_level_low(self) -> None:
        """Test format_battery_level with low level."""
        result = format_battery_level(105)
        self.assertEqual(result, "Low")

    def test_create_device_data_exception_handling(self) -> None:
        """Test create_device_data with exception in timestamp calculation."""
        mock_camera = Mock()
        mock_camera.name = "Test Camera"
        mock_camera.updated_at = "invalid-timestamp"  # Will cause ValueError
        mock_camera.last_record = {"created_at": "2025-01-15T10:30:00+00:00"}

        result = create_device_data(mock_camera, "test_cache_key")  # type: ignore[arg-type]

        # Should handle exception gracefully
        self.assertIsInstance(result, dict)
        self.assertIn("last_updated", result)

    def test_create_device_data_no_last_record(self) -> None:
        """Test create_device_data with no last_record."""
        mock_camera = Mock()
        mock_camera.name = "Test Camera"
        mock_camera.updated_at = "invalid-timestamp"
        mock_camera.last_record = None

        result = create_device_data(mock_camera, "test_cache_key")  # type: ignore[arg-type]

        self.assertIsInstance(result, dict)
        self.assertIn("last_updated", result)
        self.assertEqual(result["last_updated"], "Never")

    def test_create_device_data_last_record_fallback(self) -> None:
        """Test create_device_data fallback to last_record timestamp."""
        mock_camera = Mock()
        mock_camera.name = "Test Camera"
        mock_camera.updated_at = "invalid-timestamp"
        mock_camera.last_record = {"updated_at": "2025-01-15T10:30:00+00:00"}

        result = create_device_data(mock_camera, "test_cache_key")  # type: ignore[arg-type]

        self.assertIsInstance(result, dict)
        self.assertIn("last_updated", result)

    def test_create_device_data_last_record_time_key(self) -> None:
        """Test create_device_data with 'time' key in last_record."""
        mock_camera = Mock()
        mock_camera.name = "Test Camera"
        mock_camera.updated_at = "invalid-timestamp"
        mock_camera.last_record = {"time": "2025-01-15T10:30:00+00:00"}

        result = create_device_data(mock_camera, "test_cache_key")  # type: ignore[arg-type]

        self.assertIsInstance(result, dict)
        self.assertIn("last_updated", result)


if __name__ == "__main__":
    unittest.main()
