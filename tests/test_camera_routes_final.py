#!/usr/bin/env python3
"""Final tests for routes/camera.py - targeting more missed lines."""

import unittest
from unittest.mock import patch

from flask import Flask

from blinkapp.routes.camera import setup_camera_routes


class TestCameraRoutesFinal(unittest.TestCase):
    """Test camera route functions with more missed lines."""

    def test_setup_camera_routes(self) -> None:
        """Test setup_camera_routes function."""
        app = Flask(__name__)

        # Should not raise exception
        setup_camera_routes(app)

        # Should have registered routes
        rules = list(app.url_map.iter_rules())
        self.assertGreater(len(rules), 0)

        # Check specific routes are registered
        endpoints = [rule.endpoint for rule in rules]
        self.assertIn("get_camera_thumbnail", endpoints)

    def test_camera_routes_registration(self) -> None:
        """Test camera routes are properly registered."""
        app = Flask(__name__)
        setup_camera_routes(app)

        # Test that routes exist
        with app.test_client() as client:
            # Test camera thumbnail endpoint exists (will fail auth but route exists)
            response = client.get("/api/cameras/12345/thumbnail")
            # Should not be 404 (route exists)
            self.assertNotEqual(response.status_code, 404)

            # Test camera stream endpoint exists
            response = client.post("/api/cameras/12345/streams")
            # Should not be 404 (route exists)
            self.assertNotEqual(response.status_code, 404)

    def test_camera_hls_route_registration(self) -> None:
        """Test camera stream file route registration."""
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

                # Check if route was registered
                routes = [rule.rule for rule in app.url_map.iter_rules()]
                hls_route = "/api/cameras/<camera_id_str>/streams/<path:filename>"

                # Route should be registered
                self.assertIn(hls_route, routes)

    def test_camera_refresh_route_registration(self) -> None:
        """Test camera thumbnail cache clear route registration."""
        app = Flask(__name__)
        setup_camera_routes(app)

        with app.test_client() as client:
            # Test thumbnail cache clear endpoint exists
            response = client.delete("/api/cameras/12345/thumbnail")
            # Should not be 404 (route exists)
            self.assertNotEqual(response.status_code, 404)
