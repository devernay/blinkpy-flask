#!/usr/bin/env python3
"""Targeted tests for routes/camera.py - covering highest missed lines."""

import unittest
from unittest.mock import patch

from flask import Flask

from blinkapp.routes.camera import setup_camera_routes


class TestCameraRoutesExpansion(unittest.TestCase):
    """Test uncovered camera route functions with highest missed lines."""

    def test_setup_camera_routes(self) -> None:
        """Test setup_camera_routes function."""
        app = Flask(__name__)

        # Should not raise exception
        setup_camera_routes(app)

        # Should have registered routes
        rules = list(app.url_map.iter_rules())
        self.assertGreater(len(rules), 0)

        # Check specific routes are registered (thumbnail routes moved to thumbnails module)
        endpoints = [rule.endpoint for rule in rules]
        self.assertIn("list_cameras", endpoints)
        self.assertIn("get_camera_details", endpoints)

    def test_camera_routes_registration(self) -> None:
        """Test camera routes are properly registered."""
        app = Flask(__name__)
        setup_camera_routes(app)

        # Test that camera routes exist
        with app.test_client() as client:
            # Test camera list endpoint exists
            response = client.get("/api/cameras")
            # Should not be 404 (route exists)
            self.assertNotEqual(response.status_code, 404)

            # Test camera details endpoint exists
            response = client.get("/api/cameras/12345")
            # Should not be 404 (route exists)
            self.assertNotEqual(response.status_code, 404)

    def test_camera_recording_route_registration(self) -> None:
        """Test camera recording route registration."""
        app = Flask(__name__)

        # Mock all required decorators to pass through
        with patch(
            "blinkapp.utils.decorators.api_route_with_validation"
        ) as mock_decorator:
            with patch(
                "blinkapp.utils.decorators.ensure_blink_available"
            ) as mock_ensure:
                # Make decorators pass through the function unchanged
                mock_decorator.side_effect = lambda *args, **kwargs: lambda func: func
                mock_ensure.side_effect = lambda func: func

                setup_camera_routes(app)

                # Check if recording route was registered
                routes = [rule.rule for rule in app.url_map.iter_rules()]
                recording_route = "/api/cameras/<camera_id_str>/record"

                # Route should be registered
                self.assertIn(recording_route, routes)
