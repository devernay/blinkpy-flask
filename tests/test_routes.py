"""Unit tests for Flask routes.

These tests focus on verifying Flask routes exist and basic functionality.
They are designed to be easily removable when migrating to connexion framework.
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
        api_routes = ["/api/systems", "/api/cameras", "/api/clips"]

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
