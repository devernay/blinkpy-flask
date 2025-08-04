#!/usr/bin/env python3
"""
Unit tests for route decorators.

This module tests the route decorators that eliminate duplication
in Flask route handlers.
"""

import json
import sys
import unittest
from unittest.mock import MagicMock, Mock

from flask import Flask, request


# Mock the app module dependencies for testing
class MockConfig:
    ErrorMessages = Mock()
    ErrorMessages.INVALID_JSON_DATA = "Invalid JSON data"
    ErrorMessages.CAMERA_NOT_FOUND = "Camera not found"
    HTTP_STATUS_INTERNAL_ERROR = 500


def create_api_response(success=True, data=None, error=None, status_code=200):
    """Mock create_api_response function."""
    response = {"success": success, "timestamp": "2025-01-27T12:00:00Z"}
    if data is not None:
        response["data"] = data
    if error is not None:
        response["error"] = error
    return response, status_code


def handle_api_error(error, operation, status_code=500):
    """Mock handle_api_error function."""
    return create_api_response(success=False, error=str(error), status_code=status_code)


# Mock the blinkapp module
mock_blinkapp = MagicMock()
mock_blinkapp.Config = MockConfig
mock_blinkapp.create_api_response = create_api_response
mock_blinkapp.handle_api_error = handle_api_error
mock_blinkapp.ResponseReturnValue = tuple
sys.modules["blinkapp"] = mock_blinkapp

# Now import our decorators
from route_decorators import (  # noqa: E402
    api_route,
    api_route_with_validation,
    simple_success_response,
)

# Create test Flask app
app = Flask(__name__)


class TestRouteDecorators(unittest.TestCase):
    """Test cases for route decorators."""

    def setUp(self) -> None:
        self.app = app
        self.client = app.test_client()
        app.config["TESTING"] = True

    def test_api_route_success(self) -> None:
        """Test @api_route decorator with successful response."""

        @app.route("/test/success")
        @api_route("test operation")
        def test_success() -> None:
            return {"message": "success", "data": [1, 2, 3]}

        with app.test_request_context():
            response = test_success()

        # Should return jsonified response with status code
        self.assertIsInstance(response, tuple)
        self.assertEqual(len(response), 2)

        # Parse the JSON response
        json_response = json.loads(response[0].data)
        status_code = response[1]

        self.assertEqual(status_code, 200)
        self.assertTrue(json_response["success"])
        self.assertEqual(json_response["data"]["message"], "success")

    def test_api_route_exception(self) -> None:
        """Test @api_route decorator with exception handling."""

        @app.route("/test/error")
        @api_route("test error operation")
        def test_error() -> None:
            raise ValueError("Test error message")

        with app.test_request_context():
            response = test_error()

        json_response = json.loads(response[0].data)
        status_code = response[1]

        self.assertEqual(status_code, 500)
        self.assertFalse(json_response["success"])
        self.assertIn("Test error message", json_response["error"])

    def test_api_route_with_validation_success(self) -> None:
        """Test @api_route_with_validation decorator with valid parameters."""

        def validate_id(id_str):
            """Mock validator that converts string to int."""
            return int(id_str)

        @app.route("/test/validate/<id_str>")
        @api_route_with_validation(
            "test validation", validate_params={"id_str": validate_id}
        )
        def test_validate(**kwargs) -> None:
            # The decorator should have converted id_str to id
            validated_id = kwargs.get("id") or kwargs.get("id_str")
            if isinstance(validated_id, str):
                validated_id = int(validated_id)  # Fallback conversion
            return {"validated_id": validated_id, "type": type(validated_id).__name__}

        with app.test_request_context("/test/validate/123"):
            # Call the function with the parameter
            response = test_validate(id_str="123")

        json_response = json.loads(response[0].data)
        self.assertTrue(json_response["success"])
        self.assertEqual(json_response["data"]["validated_id"], 123)
        self.assertEqual(json_response["data"]["type"], "int")

    def test_api_route_with_validation_invalid_param(self) -> None:
        """Test @api_route_with_validation decorator with invalid parameters."""

        def validate_id(id_str):
            """Mock validator that raises ValueError for invalid input."""
            if not id_str.isdigit():
                raise ValueError("ID must be numeric")
            return int(id_str)

        @app.route("/test/validate/<id_str>")
        @api_route_with_validation(
            "test validation", validate_params={"id_str": validate_id}
        )
        def test_validate_invalid(**kwargs) -> None:
            validated_id = kwargs.get("id") or kwargs.get("id_str")
            return {"validated_id": validated_id}

        with app.test_request_context("/test/validate/abc"):
            response = test_validate_invalid(id_str="abc")

        json_response = json.loads(response[0].data)
        status_code = response[1]

        self.assertEqual(status_code, 400)
        self.assertFalse(json_response["success"])
        self.assertIn("ID must be numeric", json_response["error"])

    def test_api_route_with_json_validation(self) -> None:
        """Test @api_route_with_validation decorator with JSON validation."""

        @app.route("/test/json", methods=["POST"])
        @api_route_with_validation(
            "test json validation",
            validate_json=True,
            required_fields=["name", "value"],
        )
        def test_json_validation() -> None:
            data = request.get_json()
            return {"received": data}

        with app.test_request_context(
            "/test/json", method="POST", json={"name": "test", "value": 42}
        ):
            response = test_json_validation()

        json_response = json.loads(response[0].data)
        self.assertTrue(json_response["success"])
        self.assertEqual(json_response["data"]["received"]["name"], "test")
        self.assertEqual(json_response["data"]["received"]["value"], 42)

    def test_api_route_with_json_validation_missing_field(self) -> None:
        """Test @api_route_with_validation decorator with missing required field."""

        @app.route("/test/json-missing", methods=["POST"])
        @api_route_with_validation(
            "test json validation",
            validate_json=True,
            required_fields=["name", "value"],
        )
        def test_json_validation_missing() -> None:
            data = request.get_json()
            return {"received": data}

        with app.test_request_context(
            "/test/json-missing", method="POST", json={"name": "test"}
        ):  # Missing "value"
            response = test_json_validation_missing()

        json_response = json.loads(response[0].data)
        status_code = response[1]

        self.assertEqual(status_code, 400)
        self.assertFalse(json_response["success"])
        self.assertIn("Missing required fields: value", json_response["error"])

    def test_simple_success_response(self) -> None:
        """Test @simple_success_response decorator."""

        executed = []

        @app.route("/test/simple-success", methods=["POST"])
        @simple_success_response("Operation completed successfully")
        def test_simple_success() -> None:
            executed.append("function_called")
            # Function executes but doesn't need to return anything

        with app.test_request_context("/test/simple-success", method="POST"):
            response = test_simple_success()

        json_response = json.loads(response[0].data)
        status_code = response[1]

        self.assertEqual(status_code, 200)
        self.assertTrue(json_response["success"])
        self.assertEqual(
            json_response["data"]["message"], "Operation completed successfully"
        )
        self.assertIn("function_called", executed)

    def test_simple_success_response_with_exception(self) -> None:
        """Test @simple_success_response decorator with exception."""

        @app.route("/test/simple-error", methods=["POST"])
        @simple_success_response("This should not appear")
        def test_simple_error() -> None:
            raise RuntimeError("Something went wrong")

        with app.test_request_context("/test/simple-error", method="POST"):
            response = test_simple_error()

        json_response = json.loads(response[0].data)
        status_code = response[1]

        self.assertEqual(status_code, 500)
        self.assertFalse(json_response["success"])
        self.assertIn("Something went wrong", json_response["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
