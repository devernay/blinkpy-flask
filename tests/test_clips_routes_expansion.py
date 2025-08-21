#!/usr/bin/env python3
"""Targeted tests for routes/clips.py expansion - covering missed lines."""

import unittest

from flask import Flask

from blinkapp.routes.clips import setup_clips_routes


class TestClipsRoutesExpansion(unittest.TestCase):
    """Test uncovered clips route functions."""

    def test_setup_clips_routes(self):
        """Test setup_clips_routes function."""
        app = Flask(__name__)

        # Should not raise exception
        setup_clips_routes(app)

        # Should have registered routes
        rules = list(app.url_map.iter_rules())
        self.assertGreater(len(rules), 0)

        # Check specific routes are registered
        endpoints = [rule.endpoint for rule in rules]
        self.assertIn("get_clips", endpoints)
        self.assertIn("process_clip", endpoints)

    def test_clips_routes_registration(self):
        """Test clips routes are properly registered."""
        app = Flask(__name__)
        setup_clips_routes(app)

        # Test that routes exist
        with app.test_client() as client:
            # Test clips endpoint exists (will fail auth but route exists)
            response = client.get("/api/clips")
            # Should not be 404 (route exists)
            self.assertNotEqual(response.status_code, 404)
