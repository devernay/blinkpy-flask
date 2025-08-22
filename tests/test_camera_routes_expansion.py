#!/usr/bin/env python3
"""Targeted tests for routes/camera.py - covering highest missed lines."""

import unittest

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
        """Test camera HLS route registration."""
        app = Flask(__name__)
        setup_camera_routes(app)

        with app.test_client() as client:
            # Test HLS endpoint exists
            response = client.get("/api/cameras/12345/streams/test.m3u8")
            # Should not be 404 (route exists)
            self.assertNotEqual(response.status_code, 404)
