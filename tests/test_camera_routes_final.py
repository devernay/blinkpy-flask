#!/usr/bin/env python3
"""Final tests for routes/camera.py - targeting more missed lines."""

import unittest

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

            # Test camera liveview endpoint exists
            response = client.get("/api/cameras/12345/liveview")
            # Should not be 404 (route exists)
            self.assertNotEqual(response.status_code, 404)

    def test_camera_hls_route_registration(self) -> None:
        """Test camera HLS route registration."""
        app = Flask(__name__)
        setup_camera_routes(app)

        with app.test_client() as client:
            # Test HLS endpoint exists
            response = client.get("/api/cameras/12345/hls/playlist.m3u8")
            # Should not be 404 (route exists)
            self.assertNotEqual(response.status_code, 404)

    def test_camera_refresh_route_registration(self) -> None:
        """Test camera refresh route registration."""
        app = Flask(__name__)
        setup_camera_routes(app)

        with app.test_client() as client:
            # Test refresh endpoint exists
            response = client.put("/api/cameras/12345/refresh")
            # Should not be 404 (route exists)
            self.assertNotEqual(response.status_code, 404)
