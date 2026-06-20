"""Tests for the before_request authentication guard."""

import json
import unittest


class TestAuthGuard(unittest.TestCase):
    """Authentication guard for protected endpoints (REQUIRE_AUTH enabled)."""

    def setUp(self) -> None:
        """Set up a test client with the auth guard enabled.

        Tests:
            - Not a test; provides an app/client with REQUIRE_AUTH=True
        """
        from blinkapp import app

        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["SECRET_KEY"] = "test-secret-key"
        self._prev_require_auth = self.app.config.get("REQUIRE_AUTH", True)
        self.app.config["REQUIRE_AUTH"] = True
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        """Restore the previous REQUIRE_AUTH config.

        Tests:
            - Not a test; resets config so other tests are unaffected
        """
        self.app.config["REQUIRE_AUTH"] = self._prev_require_auth

    def test_unauthenticated_api_returns_401_json(self) -> None:
        """Unauthenticated API requests are rejected with a 401 JSON body.

        Tests:
            - GET /api/systems without a session returns HTTP 401
            - The body is JSON with success=False
        """
        response = self.client.get("/api/systems")
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data["success"])

    def test_unauthenticated_page_redirects_to_login(self) -> None:
        """Unauthenticated page requests redirect to the login page.

        Tests:
            - GET / without a session returns a 302 redirect
            - The redirect target is the login page
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers.get("Location", ""))

    def test_unauthenticated_protected_page_redirects(self) -> None:
        """The logs page is protected when unauthenticated.

        Tests:
            - GET /logs without a session returns a 302 redirect to login
        """
        response = self.client.get("/logs")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers.get("Location", ""))

    def test_login_page_is_public(self) -> None:
        """The login page is reachable without authentication.

        Tests:
            - GET /login returns HTTP 200 (not blocked by the guard)
        """
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)

    def test_authenticated_api_is_not_blocked(self) -> None:
        """An authenticated session passes the guard for API requests.

        Tests:
            - With session['authenticated']=True, GET /api/systems is not 401
        """
        with self.client.session_transaction() as sess:
            sess["authenticated"] = True
        response = self.client.get("/api/systems")
        self.assertNotEqual(response.status_code, 401)
