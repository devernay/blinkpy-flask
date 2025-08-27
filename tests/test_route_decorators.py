#!/usr/bin/env python3
"""
Unit tests for route decorators.

This module tests the route decorators that eliminate duplication
in Flask route handlers.
"""

import json
import sys
from typing import cast
from unittest.mock import MagicMock, Mock, patch

from flask import Flask, Response
from test_base import BaseTestCase


class TestRouteDecorators(BaseTestCase):
    """Test cases for route decorators."""

    def setUp(self) -> None:
        # Store original blinkapp module if it exists
        self._original_blinkapp = sys.modules.get("blinkapp")

        # Create a fresh Flask app for each test to avoid state contamination
        self.test_app = Flask(__name__)
        self.test_app.config["TESTING"] = True
        self.client = self.test_app.test_client()

    def tearDown(self) -> None:
        """Restore original blinkapp module and call parent tearDown."""
        # Restore original blinkapp module
        if self._original_blinkapp is not None:
            sys.modules["blinkapp"] = self._original_blinkapp
        elif "blinkapp" in sys.modules:
            del sys.modules["blinkapp"]

        # Call parent tearDown for global state cleanup
        super().tearDown()

    def _setup_mock_blinkapp(self):
        """Setup mock blinkapp module for testing."""
        mock_blinkapp = MagicMock()

        # Use real Config class instead of duplicating it
        from blinkapp.config import Config

        mock_blinkapp.Config = Config

        # Mock functions
        def create_api_response(success=True, data=None, error=None, status_code=200):
            response = {"success": success, "timestamp": "2023-01-01T00:00:00Z"}
            if data is not None:
                response["data"] = data
            if error is not None:
                response["error"] = error
            return response, status_code

        def handle_api_error(error, operation=None, status_code=500):
            return create_api_response(
                success=False, error=str(error), status_code=status_code
            )

        mock_blinkapp.create_api_response = create_api_response
        mock_blinkapp.handle_api_error = handle_api_error
        mock_blinkapp.logger = Mock()

        sys.modules["blinkapp"] = mock_blinkapp
        return mock_blinkapp

    def _parse_response(self, response: object) -> tuple[dict, int]:
        """Helper to parse response tuple and extract JSON data."""
        response_tuple = cast(tuple[object, int], response)
        response_obj = cast(Response, response_tuple[0])
        json_response = json.loads(response_obj.data)
        status_code = response_tuple[1]
        return json_response, status_code

    def test_api_route_success(self) -> None:
        """Test @api_route decorator with successful response."""
        # Setup mock and import decorator
        self._setup_mock_blinkapp()
        from blinkapp.utils.route_decorators import api_route

        @api_route("test operation")
        def test_success() -> dict[str, object]:
            return {"message": "success", "data": [1, 2, 3]}

        with self.test_app.test_request_context():
            response = test_success()

        json_response, status_code = self._parse_response(response)

        self.assertEqual(status_code, 200)
        self.assertTrue(json_response["success"])
        self.assertEqual(json_response["data"]["message"], "success")
        self.assertEqual(json_response["data"]["data"], [1, 2, 3])
        self.assertIn("timestamp", json_response)

    def test_api_route_exception(self) -> None:
        """Test @api_route decorator with exception handling."""
        self._setup_mock_blinkapp()
        from blinkapp.utils.route_decorators import api_route

        @api_route("test error operation")
        def test_error() -> dict[str, object]:
            raise ValueError("Test error message")

        with self.test_app.test_request_context():
            response = test_error()

        json_response, status_code = self._parse_response(response)

        self.assertEqual(status_code, 500)
        self.assertFalse(json_response["success"])
        self.assertIn("Test error message", json_response["error"])

    def test_api_route_with_validation_success(self) -> None:
        """Test @api_route decorator with validation success."""
        self._setup_mock_blinkapp()
        from blinkapp.models.ids import CameraId
        from blinkapp.utils.route_decorators import api_route_with_validation

        @api_route_with_validation(
            "test operation", validate_params={"camera_id_str": CameraId}
        )
        def test_validate(camera_id: CameraId) -> dict[str, str]:
            return {"validated_id": str(camera_id)}

        with self.test_app.test_request_context():
            with patch("flask.request") as mock_request:
                mock_request.view_args = {"camera_id_str": "valid123"}
                # Call with the _str parameter, decorator will validate and pass camera_id
                response = test_validate(camera_id_str="valid123")

        json_response, status_code = self._parse_response(response)
        self.assertEqual(status_code, 200)
        self.assertTrue(json_response["success"])
        self.assertEqual(json_response["data"]["validated_id"], "valid123")

    def test_api_route_with_validation_invalid_param(self) -> None:
        """Test @api_route decorator with validation invalid param."""
        self._setup_mock_blinkapp()
        from blinkapp.models.ids import CameraId
        from blinkapp.utils.route_decorators import api_route_with_validation

        @api_route_with_validation(
            "test operation", validate_params={"camera_id_str": CameraId}
        )
        def test_validate(camera_id: CameraId) -> dict[str, str]:
            return {"validated_id": str(camera_id)}

        with self.test_app.test_request_context():
            with patch("flask.request") as mock_request:
                mock_request.view_args = {"camera_id_str": "invalid!@#"}
                # Call with invalid parameter, should trigger validation error
                response = test_validate(camera_id_str="invalid!@#")

        json_response, status_code = self._parse_response(response)
        self.assertEqual(status_code, 400)
        self.assertFalse(json_response["success"])
        self.assertIn("error", json_response)

    def test_simple_success_response(self) -> None:
        """Test simple success response decorator."""
        self._setup_mock_blinkapp()
        from blinkapp.utils.route_decorators import simple_success_response

        @simple_success_response("test operation")
        def test_simple_success() -> dict[str, str]:
            return {"message": "simple success"}

        with self.test_app.test_request_context():
            response = test_simple_success()

        json_response, status_code = self._parse_response(response)
        self.assertEqual(status_code, 200)
        self.assertTrue(json_response["success"])
        # simple_success_response wraps the message in {"message": message}
        self.assertEqual(json_response["data"]["message"], "test operation")

    def test_simple_success_response_with_exception(self) -> None:
        """Test simple success response with exception."""
        self._setup_mock_blinkapp()
        from blinkapp.utils.route_decorators import simple_success_response

        @simple_success_response("test operation")
        def test_simple_error() -> dict[str, str]:
            raise ValueError("Test error")

        with self.test_app.test_request_context():
            response = test_simple_error()

        json_response, status_code = self._parse_response(response)
        self.assertEqual(status_code, 500)
        self.assertFalse(json_response["success"])
        self.assertIn("error", json_response)
