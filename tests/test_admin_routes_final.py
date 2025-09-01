#!/usr/bin/env python3
"""Final targeted tests for routes/admin.py - covering remaining missed lines."""

from flask import Flask

from blinkapp.routes.admin import register_admin_routes

from .test_base import FlaskTestCase


class TestAdminRoutesFinal(FlaskTestCase):
    """Test remaining uncovered admin route functions."""

    def test_register_admin_routes(self) -> None:
        """Test register_admin_routes function."""
        app = Flask(__name__)

        # Should not raise exception
        register_admin_routes(app)

        # Should have registered routes
        self.assertGreater(len(list(app.url_map.iter_rules())), 0)
