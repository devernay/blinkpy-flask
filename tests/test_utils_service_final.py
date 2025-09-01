"""Final test coverage for utils_service.py missed lines."""

import unittest

from blinkapp.services.device_service import (
    create_device_data,
    format_device_temperature,
)

from .test_base import create_mock_camera


class TestUtilsServiceFinal(unittest.TestCase):
    """Final utils service coverage tests."""

    def test_format_device_temperature_basic(self) -> None:
        """Test format_device_temperature basic functionality."""
        result = format_device_temperature(68.5, "F")
        self.assertEqual(result, "68.5°F")

    def test_create_device_data_exception_handling(self) -> None:
        """Test create_device_data with exception in timestamp calculation."""
        mock_camera = create_mock_camera(
            camera_id="test_camera_123",
            name="Test Camera",
            battery="ok",
            temperature=72.5,
            temperature_calibrated=72.8,
            wifi_strength=4,
            motion_enabled=True,
            updated_at="invalid-timestamp",
            last_record={"created_at": "2025-01-15T10:30:00+00:00"},
        )

        result = create_device_data(mock_camera)

        # Should handle exception gracefully
        self.assertIsInstance(result, dict)
        self.assertIn("last_updated", result)
        self.assertEqual(result["id"], "test_camera_123")
        self.assertEqual(result["name"], "Test Camera")
        self.assertEqual(result["temperature"], 72.5)  # Should be numeric
        self.assertEqual(result["temperature_calibrated"], 72.8)  # New calibrated field

    def test_create_device_data_no_last_record(self) -> None:
        """Test create_device_data with no last_record."""
        mock_camera = create_mock_camera(
            camera_id="test_camera_456",
            name="Test Camera",
            battery="low",
            temperature=68.0,
            temperature_calibrated=68.2,
            wifi_strength=3,
            motion_enabled=False,
            updated_at="invalid-timestamp",
            last_record=None,
        )

        result = create_device_data(mock_camera)

        # Should handle missing last_record gracefully
        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], "test_camera_456")
        self.assertEqual(result["name"], "Test Camera")
        self.assertEqual(result["temperature"], 68.0)  # Should be numeric

        self.assertIsInstance(result, dict)
        self.assertIn("last_updated", result)
        self.assertEqual(result["last_updated"], "Never")

    def test_create_device_data_last_record_fallback(self) -> None:
        """Test create_device_data fallback to last_record timestamp."""
        mock_camera = create_mock_camera(
            camera_id="test_camera_789",
            name="Test Camera",
            battery="ok",
            temperature=70.2,
            temperature_calibrated=70.5,
            wifi_strength=5,
            motion_enabled=True,
            updated_at="invalid-timestamp",
            last_record={"updated_at": "2025-01-15T10:30:00+00:00"},
        )

        result = create_device_data(mock_camera)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], "test_camera_789")

        self.assertIsInstance(result, dict)
        self.assertIn("last_updated", result)

    def test_create_device_data_last_record_time_key(self) -> None:
        """Test create_device_data with 'time' key in last_record."""
        mock_camera = create_mock_camera(
            camera_id="test_camera_101",
            name="Test Camera",
            battery="low",
            temperature=65.8,
            temperature_calibrated=None,
            wifi_strength=2,
            motion_enabled=False,
            updated_at="invalid-timestamp",
            last_record={"time": "2025-01-15T10:30:00+00:00"},
        )

        result = create_device_data(mock_camera)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], "test_camera_101")

        self.assertIsInstance(result, dict)
        self.assertIn("last_updated", result)


if __name__ == "__main__":
    unittest.main()
