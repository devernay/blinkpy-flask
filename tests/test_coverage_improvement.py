#!/usr/bin/env python3
"""Tests to improve code coverage to 70%."""

from unittest.mock import Mock, patch

from .test_base import FlaskTestCase


class TestMainApp(FlaskTestCase):
    """Test main app functions (currently 20% coverage)."""

    def test_create_api_response_success(self) -> None:
        """Test create_api_response with success."""
        from blinkapp import create_api_response

        response, status = create_api_response(success=True, data={"test": "data"})
        self.assertEqual(status, 200)
        self.assertTrue(response["success"])

    def test_create_api_response_custom_status(self) -> None:
        """Test create_api_response with custom status."""
        from blinkapp import create_api_response

        response, status = create_api_response(
            success=False, error="Test error", status_code=500
        )
        self.assertEqual(status, 500)
        self.assertFalse(response["success"])


class TestValidators(FlaskTestCase):
    """Test validators.py (currently 18% coverage)."""



    def test_validate_camera_id_valid(self) -> None:
        """Test validate_camera_id with valid ID."""
        from blinkapp.utils.validators import validate_camera_id

        result = validate_camera_id("12345")
        self.assertEqual(result, "12345")

    def test_validate_camera_id_invalid(self) -> None:
        """Test validate_camera_id with invalid ID."""
        from blinkapp.utils.validators import validate_camera_id

        with self.assertRaises(ValueError):
            validate_camera_id("")

