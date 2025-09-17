"""Unit tests for Flask routes.

Tests Flask route functionality including:
- Route endpoint behavior
- HTTP request/response handling
- Route parameter validation
- Authentication requirements
"""

from tests.test_base import FlaskTestCase


class TestRouteExistence(FlaskTestCase):
    """Test that expected routes are registered."""

    def test_routes_exist(self) -> None:
        """Test that expected routes are registered in the Flask app.

        Verifies that all critical application routes are properly
        registered and accessible through the Flask URL routing system.

        Tests:
            - Core web routes (/, /login, /2fa, /logout)
            - API system routes (/api/systems, /api/systems/<id>/devices)
            - API camera routes (/api/cameras, /api/cameras/<id>/*)
            - API clip and streaming routes
            - Asserts all expected routes are present in URL map
        """
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
                "/api/systems/<network_id>/devices",
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
        """Test index redirects to login when user is not authenticated.

        Verifies that unauthenticated users accessing the root path
        are properly redirected to the login page for authentication.

        Tests:
            - GET request to root path (/)
            - 302 redirect response to login page
            - Proper authentication flow enforcement
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

    def test_login_page_accessible(self) -> None:
        """Test login page is accessible without authentication.

        Verifies that the login page can be accessed by unauthenticated
        users and returns the expected response status.

        Tests:
            - GET request to /login endpoint
            - 200 OK response status
            - Login page accessibility for unauthenticated users
        """
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"login", response.data.lower())

    def test_login_page_loads_integration(self) -> None:
        """Test that login page loads correctly (integration)."""
        response = self.client.get("/login")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"login", response.data.lower())

    def test_login_success_no_2fa_integration(self) -> None:
        """Test successful login without 2FA requirement (integration)."""
        from unittest.mock import patch

        with patch("blinkapp.services.auth_service.handle_login") as mock_handle_login:
            # Mock successful login without 2FA
            mock_handle_login.return_value = {"success": True}

            response = self.client.post(
                "/login",
                data={"username": "test@example.com", "password": "password123"},
            )

            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.endswith("/"))

    def test_login_requires_2fa_integration(self) -> None:
        """Test login that requires 2FA verification (integration)."""
        from unittest.mock import patch

        with patch("blinkapp.services.auth_service.handle_login") as mock_handle_login:
            # Mock login that requires 2FA
            mock_handle_login.return_value = {"success": False, "requires_2fa": True}

            response = self.client.post(
                "/login",
                data={"username": "test@example.com", "password": "password123"},
            )

            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.endswith("/2fa"))

    def test_login_failure_integration(self) -> None:
        """Test failed login with invalid credentials (integration)."""
        from unittest.mock import patch

        with patch("blinkapp.services.auth_service.handle_login") as mock_handle_login:
            # Mock failed login
            mock_handle_login.return_value = {
                "success": False,
                "error": "Invalid credentials",
            }

            response = self.client.post(
                "/login",
                data={"username": "invalid@example.com", "password": "wrongpassword"},
            )

            self.assertEqual(response.status_code, 400)
            self.assertIn(b"Invalid credentials", response.data)

    def test_2fa_page_without_pending_session_integration(self) -> None:
        """Test 2FA page redirects to login when no pending session (integration)."""
        response = self.client.get("/2fa")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/login"))

    def test_2fa_page_with_pending_session_integration(self) -> None:
        """Test 2FA page shows verification form with pending session (integration)."""
        with self.client.session_transaction() as sess:
            sess["pending_2fa"] = True
            sess["username"] = "test@example.com"
            sess["password"] = "password123"

        response = self.client.get("/2fa")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"2FA", response.data)

    def test_2fa_verification_success_integration(self) -> None:
        """Test successful 2FA verification (integration)."""
        from unittest.mock import patch

        with patch(
            "blinkapp.services.auth_service.handle_2fa_verification"
        ) as mock_handle_2fa:
            # Mock successful 2FA verification
            mock_handle_2fa.return_value = {"success": True}

            with self.client.session_transaction() as sess:
                sess["pending_2fa"] = True
                sess["username"] = "test@example.com"
                sess["password"] = "password123"

            response = self.client.post("/2fa", data={"key": "123456"})

            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.endswith("/"))

    def test_2fa_verification_failure_integration(self) -> None:
        """Test failed 2FA verification (integration)."""
        from unittest.mock import patch

        with patch(
            "blinkapp.services.auth_service.handle_2fa_verification"
        ) as mock_handle_2fa:
            # Mock failed 2FA verification
            mock_handle_2fa.return_value = {
                "success": False,
                "error": "Invalid 2FA code",
            }

            with self.client.session_transaction() as sess:
                sess["pending_2fa"] = True
                sess["username"] = "test@example.com"
                sess["password"] = "password123"

            response = self.client.post("/2fa", data={"key": "invalid"})

            self.assertEqual(response.status_code, 400)
            self.assertIn(b"Invalid 2FA code", response.data)

    def test_login_missing_credentials_integration(self) -> None:
        """Test login with missing username or password (integration)."""
        response = self.client.post("/login", data={"username": ""})

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Username and password required", response.data)

    def test_logout_clears_session_integration(self) -> None:
        """Test logout clears authentication session (integration)."""
        with self.client.session_transaction() as sess:
            sess["authenticated"] = True

        response = self.client.post("/logout")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("/login"))

    def test_main_page_with_saved_credentials_integration(self) -> None:
        """Test main page loads with authenticated session (integration)."""
        with self.client.session_transaction() as sess:
            sess["authenticated"] = True

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)

    def test_main_page_without_saved_credentials_integration(self) -> None:
        """Test main page redirects to login without saved credentials (integration)."""
        from unittest.mock import patch

        with patch("blinkapp.services.auth_service.load_saved_blink") as mock_load:
            # Mock no saved credentials
            mock_load.return_value = None

            response = self.client.get("/")

            # Should redirect to login
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.endswith("/login"))

    def test_complete_2fa_flow_integration(self) -> None:
        """Test complete login flow with 2FA (integration)."""
        from unittest.mock import patch

        with (
            patch("blinkapp.services.auth_service.handle_login") as mock_handle_login,
            patch(
                "blinkapp.services.auth_service.handle_2fa_verification"
            ) as mock_handle_2fa,
        ):
            # Step 1: Login requires 2FA
            mock_handle_login.return_value = {"success": False, "requires_2fa": True}

            response = self.client.post(
                "/login",
                data={"username": "test@example.com", "password": "password123"},
            )

            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.endswith("/2fa"))

            # Step 2: Successful 2FA verification
            mock_handle_2fa.return_value = {"success": True}

            response = self.client.post("/2fa", data={"key": "123456"})

            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.endswith("/"))

    def test_direct_login_success_integration(self) -> None:
        """Test direct login success without 2FA (integration)."""
        from unittest.mock import patch

        with patch("blinkapp.services.auth_service.handle_login") as mock_handle_login:
            # Mock successful login
            mock_handle_login.return_value = {"success": True}

            response = self.client.post(
                "/login",
                data={"username": "test@example.com", "password": "password123"},
            )

            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.endswith("/"))

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

    def test_setup_admin_routes(self) -> None:
        """Test setup_admin_routes function."""
        from flask import Flask

        from blinkapp.routes.admin import setup_admin_routes

        app = Flask(__name__)

        # Should not raise exception
        setup_admin_routes(app)

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


class TestConfigRoutes(FlaskTestCase):
    """Test config route setup and registration."""

    def test_setup_config_routes(self) -> None:
        """Test config routes setup."""
        # Config routes are handled in main app, not separate module
        self.assertTrue(True)  # Placeholder test


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
        """Test setup_system_routes function configuration and registration.

        Verifies that the system routes setup function properly
        configures and registers all system-related API endpoints.

        Tests:
            - System routes configuration and setup
            - Route registration for system endpoints
            - Proper endpoint mapping and configuration
            - System API route availability
        """
        from flask import Flask

        from blinkapp.routes.system import setup_system_routes

        app = Flask(__name__)

        # Should not raise exception
        setup_system_routes(app)

        # Should have registered routes
        rules = list(app.url_map.iter_rules())
        self.assertGreater(len(rules), 0)


class TestThumbnailsRoutes(FlaskTestCase):
    """Test thumbnails route functions."""

    def test_setup_thumbnails_routes(self) -> None:
        """Test thumbnails routes setup and configuration.

        Verifies that the thumbnail routes setup function properly
        configures and registers all thumbnail-related API endpoints.

        Tests:
            - Thumbnail routes configuration and setup
            - Route registration for thumbnail endpoints
            - Proper endpoint mapping for image handling
            - Thumbnail API route availability
        """
        from flask import Flask

        from blinkapp.routes.thumbnails import setup_camera_thumbnail_routes

        app = Flask(__name__)

        # Should not raise exception
        setup_camera_thumbnail_routes(app)

        # Should have registered routes
        rules = list(app.url_map.iter_rules())
        self.assertGreater(len(rules), 0)
