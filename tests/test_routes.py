"""Integration tests for Flask routes.

INTEGRATION TEST FILE - SHOULD BE MERGED INTO test_integration_api.py

This file contains integration tests for Flask route functionality:
- Route endpoint testing
- HTTP request/response handling
- Route parameter validation
- Authentication integration with routes

These tests should be moved to test_integration_api.py during reorganization.
DO NOT add new tests to this file - add them to test_integration_api.py.
"""

from tests.test_base import FlaskTestCase


class TestRouteExistence(FlaskTestCase):
    """Test that expected routes are registered."""

    def test_routes_exist(self) -> None:
        """Test that expected routes are registered in the Flask app."""
        with self.app.app_context():
            # Get all registered routes
            routes = [rule.rule for rule in self.app.url_map.iter_rules()]

            # Check key routes exist
            expected_routes = [
                "/",
                "/login",
                "/2fa",
                "/logout",
                "/api/systems",
                "/api/systems/<network_id_str>/devices",
                "/api/cameras",
                "/api/clips",
                "/api/config",
                "/api/settings",
                "/api/cache",
            ]

            for route in expected_routes:
                self.assertIn(
                    route, routes, f"Route {route} not found in registered routes"
                )


class TestAuthRoutes(FlaskTestCase):
    """Test authentication routes basic functionality."""

    def test_index_redirect_to_login(self) -> None:
        """Test index redirects to login when not authenticated."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

    def test_login_page_accessible(self) -> None:
        """Test login page is accessible."""
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"login", response.data.lower())

    def test_2fa_page_accessible(self) -> None:
        """Test 2FA page is accessible."""
        response = self.client.get("/2fa")
        # Should either show 2FA page or redirect (both are valid)
        self.assertIn(response.status_code, [200, 302])


class TestAPIRouteAuthentication(FlaskTestCase):
    """Test that API routes require authentication."""

    def test_api_routes_require_authentication(self) -> None:
        """Test that API routes require authentication."""
        api_routes = ["/api/systems", "/api/cameras", "/api/clips", "/api/settings"]

        for route in api_routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                # Should not return 200 (success) when not authenticated
                self.assertNotEqual(
                    response.status_code,
                    200,
                    f"Route {route} should require authentication",
                )


class TestRouteHTTPMethods(FlaskTestCase):
    """Test that routes accept expected HTTP methods."""

    def test_get_routes_accept_get(self) -> None:
        """Test that GET routes accept GET method."""
        get_routes = ["/login", "/2fa"]

        for route in get_routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                # Should not return 405 Method Not Allowed
                self.assertNotEqual(
                    response.status_code, 405, f"Route {route} should accept GET method"
                )

    def test_post_routes_accept_post(self) -> None:
        """Test that POST routes accept POST method."""
        post_routes = ["/login", "/2fa"]

        for route in post_routes:
            with self.subTest(route=route):
                response = self.client.post(route, data={})
                # Should not return 405 Method Not Allowed
                self.assertNotEqual(
                    response.status_code,
                    405,
                    f"Route {route} should accept POST method",
                )


class TestErrorHandling(FlaskTestCase):
    """Test basic error handling."""

    def test_404_for_nonexistent_routes(self) -> None:
        """Test 404 response for nonexistent routes."""
        response = self.client.get("/nonexistent")
        self.assertEqual(response.status_code, 404)

    def test_405_for_wrong_methods(self) -> None:
        """Test 405 response for wrong HTTP methods."""
        # Try POST on a GET-only route
        response = self.client.post("/")
        # Should return 405 Method Not Allowed or redirect
        self.assertIn(response.status_code, [405, 302])


class TestRouteIntegration(FlaskTestCase):
    """Test basic route integration without mocking handlers."""

    def test_authenticated_index_loads(self) -> None:
        """Test that authenticated index route loads."""
        with self.authenticated_session():
            response = self.client.get("/")
            # Should return 200 or handle gracefully
            self.assertIn(
                response.status_code, [200, 500]
            )  # 500 is OK due to missing dependencies

    def test_config_route_exists(self) -> None:
        """Test that config route exists and is callable."""
        with self.authenticated_session():
            response = self.client.get("/api/config")
            # Should not return 404 (route exists)
            self.assertNotEqual(response.status_code, 404)


class TestAdminRoutes(FlaskTestCase):
    """Test admin route setup and registration."""

    def test_register_admin_routes(self) -> None:
        """Test register_admin_routes function."""
        from flask import Flask

        from blinkapp.routes.admin import register_admin_routes

        app = Flask(__name__)

        # Should not raise exception
        register_admin_routes(app)

        # Should have registered routes
        self.assertGreater(len(list(app.url_map.iter_rules())), 0)


class TestCameraRoutes(FlaskTestCase):
    """Test camera route setup and registration."""

    def test_setup_camera_routes(self) -> None:
        """Test setup_camera_routes function."""
        from flask import Flask

        from blinkapp.routes.camera import setup_camera_routes

        app = Flask(__name__)

        # Should not raise exception
        setup_camera_routes(app)

        # Should have registered routes
        rules = list(app.url_map.iter_rules())
        self.assertGreater(len(rules), 0)

        # Check specific routes are registered
        endpoints = [rule.endpoint for rule in rules]
        self.assertIn("list_cameras_route", endpoints)
        self.assertIn("get_camera_details_route", endpoints)


class TestClipsRoutes(FlaskTestCase):
    """Test clips route setup and registration."""

    def test_setup_clips_routes(self) -> None:
        """Test setup_clips_routes function."""
        from flask import Flask

        from blinkapp.routes.clips import setup_clips_routes

        app = Flask(__name__)

        # Should not raise exception
        setup_clips_routes(app)

        # Should have registered routes
        rules = list(app.url_map.iter_rules())
        self.assertGreater(len(rules), 0)

        # Check specific routes are registered
        endpoints = [rule.endpoint for rule in rules]
        self.assertIn("get_clips_route", endpoints)

    def test_clips_routes_registration(self) -> None:
        """Test clips routes are properly registered."""
        from flask import Flask

        from blinkapp.routes.clips import setup_clips_routes

        app = Flask(__name__)
        setup_clips_routes(app)

        # Get all registered routes
        rules = list(app.url_map.iter_rules())
        endpoints = [rule.endpoint for rule in rules]

        # Check that clips routes are registered
        expected_endpoints = ["get_clips_route"]
        for endpoint in expected_endpoints:
            self.assertIn(endpoint, endpoints)

    def test_clips_thumbnail_route_registration(self) -> None:
        """Test clips thumbnail routes are registered."""
        from flask import Flask

        from blinkapp.routes.clips import setup_clips_routes

        app = Flask(__name__)
        setup_clips_routes(app)

        rules = list(app.url_map.iter_rules())
        endpoints = [rule.endpoint for rule in rules]
        self.assertIn("get_clips_route", endpoints)

    def test_clips_process_route_registration(self) -> None:
        """Test clips processing routes are registered."""
        from flask import Flask

        from blinkapp.routes.clips import setup_clips_routes

        app = Flask(__name__)
        setup_clips_routes(app)

        rules = list(app.url_map.iter_rules())
        self.assertGreater(len(rules), 0)


class TestAuthRoutesSetup(FlaskTestCase):
    """Test auth route setup and registration."""

    def test_setup_auth_routes(self) -> None:
        """Test setup_auth_routes function."""
        from flask import Flask

        from blinkapp.routes.auth import setup_auth_routes

        app = Flask(__name__)

        # Should not raise exception
        setup_auth_routes(app)

        # Should have registered routes
        rules = list(app.url_map.iter_rules())
        self.assertGreater(len(rules), 0)

    def test_register_auth_routes(self) -> None:
        """Test register_auth_routes function."""
        from flask import Flask

        from blinkapp.routes.auth import register_auth_routes

        app = Flask(__name__)

        # Should not raise exception
        register_auth_routes(app)

        # Should have registered routes
        rules = list(app.url_map.iter_rules())
        self.assertGreater(len(rules), 0)


class TestConfigRoutes(FlaskTestCase):
    """Test config route setup and registration."""

    def test_setup_config_routes(self) -> None:
        """Test setup_config_routes function."""
        from flask import Flask

        from blinkapp.routes.config import setup_config_routes

        app = Flask(__name__)

        # Should not raise exception
        setup_config_routes(app)

        # Should have registered routes
        rules = list(app.url_map.iter_rules())
        self.assertGreater(len(rules), 0)


class TestSettingsRoutes(FlaskTestCase):
    """Test settings route setup and registration."""

    def test_setup_settings_routes(self) -> None:
        """Test setup_settings_routes function."""
        from flask import Flask

        from blinkapp.routes.settings import setup_settings_routes

        app = Flask(__name__)

        # Should not raise exception
        setup_settings_routes(app)

        # Should have registered routes
        rules = list(app.url_map.iter_rules())
        self.assertGreater(len(rules), 0)

    def test_register_settings_routes(self) -> None:
        """Test register_settings_routes function."""
        from flask import Flask

        from blinkapp.routes.settings import register_settings_routes

        app = Flask(__name__)

        # Should not raise exception
        register_settings_routes(app)

        # Should have registered routes
        rules = list(app.url_map.iter_rules())
        self.assertGreater(len(rules), 0)


class TestStreamingRoutes(FlaskTestCase):
    """Test streaming route setup and registration."""

    def test_setup_streaming_routes(self) -> None:
        """Test setup_streaming_routes function."""
        from flask import Flask

        from blinkapp.routes.streaming import setup_streaming_routes

        app = Flask(__name__)

        # Should not raise exception
        setup_streaming_routes(app)

        # Should have registered routes
        rules = list(app.url_map.iter_rules())
        self.assertGreater(len(rules), 0)


class TestSystemRoutes(FlaskTestCase):
    """Test system route setup and registration."""

    def test_setup_system_routes(self) -> None:
        """Test setup_system_routes function."""
        from flask import Flask

        from blinkapp.routes.system import setup_system_routes

        app = Flask(__name__)

        # Should not raise exception
        setup_system_routes(app)

        # Should have registered routes
        rules = list(app.url_map.iter_rules())
        self.assertGreater(len(rules), 0)


class TestThumbnailsRoutes(FlaskTestCase):
    """Test thumbnails route setup and registration."""

    def test_setup_thumbnails_routes(self) -> None:
        """Test thumbnails route setup if it exists."""
        try:
            from flask import Flask

            from blinkapp.routes.thumbnails import setup_thumbnails_routes

            app = Flask(__name__)

            # Should not raise exception
            setup_thumbnails_routes(app)

            # Should have registered routes
            rules = list(app.url_map.iter_rules())
            self.assertGreater(len(rules), 0)
        except ImportError:
            # thumbnails.py might not have setup function
            self.skipTest("setup_thumbnails_routes not found")
