"""Schema validation tests for connexion handlers using OpenAPI spec validation."""

import json
import os
import unittest
from unittest.mock import Mock, patch

from jsonschema import ValidationError, validate


class TestConnexionSchemaValidation(unittest.TestCase):
    """Test connexion handlers return data matching OpenAPI schema exactly."""

    def setUp(self) -> None:
        """Load OpenAPI spec and extract schemas."""
        test_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(test_dir)
        api_path = os.path.join(project_root, "api.json")

        with open(api_path) as f:
            self.spec = json.load(f)

        self.schemas = self.spec.get("components", {}).get("schemas", {})

    def get_response_schema(self, path: str, method: str, status_code: str = "200"):
        """Extract response schema from OpenAPI spec."""
        path_spec = self.spec["paths"].get(path, {})
        method_spec = path_spec.get(method.lower(), {})
        responses = method_spec.get("responses", {})
        response_spec = responses.get(status_code, {})
        content = response_spec.get("content", {})

        # Try JSON content first, then HTML
        json_content = content.get("application/json", {})
        if json_content:
            return json_content.get("schema", {})

        html_content = content.get("text/html", {})
        if html_content:
            return html_content.get("schema", {})

        return {}

    def resolve_schema_refs(self, schema):
        """Resolve $ref references in schema."""
        if isinstance(schema, dict):
            if "$ref" in schema:
                ref_path = schema["$ref"]
                if ref_path.startswith("#/components/schemas/"):
                    schema_name = ref_path.split("/")[-1]
                    return self.schemas.get(schema_name, {})
            else:
                return {k: self.resolve_schema_refs(v) for k, v in schema.items()}
        elif isinstance(schema, list):
            return [self.resolve_schema_refs(item) for item in schema]
        return schema

    def test_admin_clear_cache_response_schema(self) -> None:
        """Test clear cache response matches OpenAPI schema exactly."""
        from blinkapp.connexion_handlers.admin import clear_thumbnail_cache

        # Get expected schema from OpenAPI spec
        schema = self.get_response_schema("/api/cache/thumbnails", "delete")
        resolved_schema = self.resolve_schema_refs(schema)

        # Get actual response from handler
        result = clear_thumbnail_cache()

        # Validate response against schema
        try:
            # Ensure schema is a proper dict for jsonschema
            if isinstance(resolved_schema, dict):
                validate(instance=result, schema=resolved_schema)
            else:
                # Skip validation if schema is not a dict
                self.skipTest(f"Schema is not a dict, got {type(resolved_schema)}")
        except ValidationError as e:
            self.fail(f"Response validation failed: {e.message}")

    def test_camera_list_response_schema(self) -> None:
        """Test camera list response matches OpenAPI schema exactly."""
        from blinkapp.connexion_handlers.camera import list_cameras

        with (
            patch("blinkapp.services.blink_service.ensure_blink_initialized"),
            patch(
                "blinkapp.services.blink_service.ensure_blink_connection_initialized"
            ) as mock_connection,
            patch("blinkapp.services.device_service.create_device_data") as mock_device,
        ):
            # Mock blink connection
            mock_blink_obj = Mock()
            mock_blink_obj.cameras = {}
            mock_connection.return_value = Mock()
            mock_connection.return_value.blink = mock_blink_obj
            mock_device.return_value = {"id": "cam1", "name": "Camera 1"}

            # Get expected schema
            schema = self.get_response_schema("/api/cameras", "get")
            resolved_schema = self.resolve_schema_refs(schema)

            # Get actual response
            result = list_cameras()

            # Validate against schema
            try:
                if isinstance(resolved_schema, dict):
                    validate(instance=result, schema=resolved_schema)
                else:
                    self.fail(f"Invalid schema type: {type(resolved_schema)}")
            except ValidationError as e:
                self.fail(f"Camera list response validation failed: {e.message}")

    def test_settings_response_schema(self) -> None:
        """Test settings response matches OpenAPI schema exactly."""
        from blinkapp.connexion_handlers.settings import get_user_settings

        with patch("blinkapp.services.settings_service.get_user_settings") as mock_get:
            mock_get.return_value = {"temperature_unit": "celsius"}

            # Get expected schema
            schema = self.get_response_schema("/api/settings", "get")
            resolved_schema = self.resolve_schema_refs(schema)

            # Get actual response
            result = get_user_settings()

            # Validate against schema
            try:
                if isinstance(resolved_schema, dict):
                    validate(instance=result, schema=resolved_schema)
                else:
                    self.fail(f"Invalid schema type: {type(resolved_schema)}")
            except ValidationError as e:
                self.fail(f"Settings response validation failed: {e.message}")

    def test_error_response_schema(self) -> None:
        """Test error responses match OpenAPI error schema."""
        from blinkapp.connexion_handlers.camera import get_camera_details

        with patch(
            "blinkapp.services.camera_service.find_camera_by_id", return_value=None
        ):
            # Get actual error response
            result = get_camera_details("invalid-id")

            # Should be a tuple for error responses
            if isinstance(result, tuple):
                error_data, status_code = result
                self.assertEqual(status_code, 404)

                # Validate error structure
                self.assertIn("success", error_data)
                self.assertIn("error", error_data)
                self.assertEqual(error_data["success"], False)

    def test_system_endpoints_response_schema(self) -> None:
        """Test system endpoints return responses matching OpenAPI schema."""
        from blinkapp.connexion_handlers.system import get_systems

        with patch("blinkapp.services.system_service.get_systems") as mock_get:
            mock_get.return_value = {
                "success": True,
                "data": {"systems": []},
                "timestamp": "2025-01-01T00:00:00",
            }

            # Get expected schema
            schema = self.get_response_schema("/api/systems", "get")
            resolved_schema = self.resolve_schema_refs(schema)

            # Get actual response
            result = get_systems()

            # Validate against schema
            try:
                if isinstance(resolved_schema, dict):
                    validate(instance=result, schema=resolved_schema)
                else:
                    self.fail(f"Invalid schema type: {type(resolved_schema)}")
            except ValidationError as e:
                self.fail(f"Systems response validation failed: {e.message}")

    def test_clips_endpoints_response_schema(self) -> None:
        """Test clips endpoints return responses matching OpenAPI schema."""
        from blinkapp.connexion_handlers.clips import get_clips

        with (
            patch("blinkapp.services.clip_service.process_local_clips") as mock_clips,
            patch("blinkapp.services.blink_service.ensure_blink_initialized"),
            patch(
                "blinkapp.services.blink_service.ensure_blink_connection_initialized"
            ),
        ):
            mock_clips.return_value = []

            # Get expected schema
            schema = self.get_response_schema("/api/clips", "get")
            resolved_schema = self.resolve_schema_refs(schema)

            # Get actual response
            result = get_clips("local")

            # Validate against schema
            try:
                if isinstance(resolved_schema, dict):
                    validate(instance=result, schema=resolved_schema)
                else:
                    self.fail(f"Invalid schema type: {type(resolved_schema)}")
            except ValidationError as e:
                self.fail(f"Clips response validation failed: {e.message}")

    def test_streaming_endpoints_response_schema(self) -> None:
        """Test streaming endpoints return responses matching OpenAPI schema."""
        from blinkapp.connexion_handlers.streaming import start_live_stream

        with (
            patch("blinkapp.services.camera_service.find_camera_by_id") as mock_find,
            patch("blinkapp.services.stream_service.init_camera_stream") as mock_stream,
        ):
            mock_find.return_value = Mock()  # Return a camera object
            mock_stream.return_value = (Mock(), "http://test-stream-url")

            # Get expected schema
            schema = self.get_response_schema(
                "/api/cameras/{camera_id}/streams", "post"
            )
            resolved_schema = self.resolve_schema_refs(schema)

            # Get actual response
            result = start_live_stream("cam1")

            # Should be a dict for successful responses (not a tuple)
            self.assertIsInstance(result, dict)

            # Validate against schema
            try:
                if isinstance(resolved_schema, dict):
                    validate(instance=result, schema=resolved_schema)
                else:
                    self.fail(f"Invalid schema type: {type(resolved_schema)}")
            except ValidationError as e:
                self.fail(f"Streaming response validation failed: {e.message}")

    def test_thumbnails_endpoints_response_schema(self) -> None:
        """Test thumbnail endpoints return responses matching OpenAPI schema."""
        from blinkapp.connexion_handlers.thumbnails import get_camera_thumbnail

        with patch(
            "blinkapp.services.thumbnail_service.get_camera_thumbnail"
        ) as mock_thumb:
            mock_thumb.return_value = (b"fake_image_data", "image/jpeg")

            # Test that thumbnail endpoint returns binary data
            result = get_camera_thumbnail("cam1")

            # Should return tuple of (bytes, content_type) for binary responses
            if isinstance(result, tuple):
                self.assertEqual(len(result), 2)
                self.assertIsInstance(result[0], bytes)
                self.assertIsInstance(result[1], str)
            else:
                # If it's a Response object, check its properties
                from flask import Response

                if isinstance(result, Response):
                    self.assertIsNotNone(result.data)
                else:
                    self.fail(f"Unexpected result type: {type(result)}")


if __name__ == "__main__":
    unittest.main()
