"""Tests for models/ids.py to improve coverage."""

import unittest

from blinkapp.models.ids import CameraId


class TestIdsCoverage(unittest.TestCase):
    """Pure unit tests for ID model edge cases and coverage.

    Inherits from unittest.TestCase because:
    - Tests simple model methods and validation logic
    - No external dependencies, mocks, or async operations
    - Pure unit testing of data model behavior
    """

    """Test IDs module for coverage improvement."""

    def test_camera_id_int_invalid(self) -> None:
        """Test CameraId __int__ with invalid value."""
        camera_id = CameraId("invalid_number")

        with self.assertRaises(ValueError) as context:
            int(camera_id)

        self.assertIn("Cannot convert Camera ID", str(context.exception))
        self.assertIn("invalid_number", str(context.exception))

    def test_camera_id_int_valid(self) -> None:
        """Test CameraId __int__ with valid value."""
        camera_id = CameraId("123")

        result = int(camera_id)

        self.assertEqual(result, 123)


if __name__ == "__main__":
    unittest.main()
