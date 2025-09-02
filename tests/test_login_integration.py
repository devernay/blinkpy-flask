"""Integration tests for login flow with real server requests."""

from unittest.mock import patch

import pytest

from blinkapp import app as flask_app


@pytest.fixture
def app():
    """Create test Flask app."""
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret-key"
    return flask_app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestLoginIntegration:
    """Integration tests for login authentication flow."""

    def test_login_page_loads(self, client):
        """Test that login page loads correctly."""
        response = client.get("/login")
        assert response.status_code == 200
        assert b"Blink Camera System" in response.data
        assert b"Username" in response.data
        assert b"Password" in response.data

    @patch("blinkapp.services.auth_service.handle_login")
    def test_login_success_no_2fa(self, mock_handle_login, client):
        """Test successful login without 2FA requirement."""
        # Mock successful login without 2FA
        mock_handle_login.return_value = {"success": True}

        response = client.post(
            "/login", data={"username": "test@example.com", "password": "validpassword"}
        )

        # Should redirect to main page
        assert response.status_code == 302
        assert response.location.endswith("/")

    @patch("blinkapp.services.auth_service.handle_login")
    def test_login_requires_2fa(self, mock_handle_login, client):
        """Test login that requires 2FA verification."""
        # Mock login that requires 2FA
        mock_handle_login.return_value = {"success": False, "requires_2fa": True}

        response = client.post(
            "/login", data={"username": "test@example.com", "password": "validpassword"}
        )

        # Should redirect to 2FA page
        assert response.status_code == 302
        assert response.location.endswith("/2fa")

    @patch("blinkapp.services.auth_service.handle_login")
    def test_login_failure(self, mock_handle_login, client):
        """Test failed login with invalid credentials."""
        # Mock failed login
        mock_handle_login.return_value = {
            "success": False,
            "error": "Authentication failed",
        }

        response = client.post(
            "/login", data={"username": "test@example.com", "password": "wrongpassword"}
        )

        # Should return error on login page
        assert response.status_code == 400
        assert b"Authentication failed" in response.data

    def test_2fa_page_without_pending_session(self, client):
        """Test 2FA page redirects to login when no pending session."""
        response = client.get("/2fa")

        # Should redirect to login page
        assert response.status_code == 302
        assert response.location.endswith("/login")

    def test_2fa_page_with_pending_session(self, client):
        """Test 2FA page shows verification form with pending session."""
        with client.session_transaction() as sess:
            sess["pending_2fa"] = True
            sess["temp_username"] = "test@example.com"
            sess["temp_password"] = "password"

        response = client.get("/2fa")

        # Should show 2FA form
        assert response.status_code == 200
        assert b"Verification Code" in response.data
        assert b"Enter code from email" in response.data
        assert b"Verify Code" in response.data

    @patch("blinkapp.services.auth_service.handle_2fa_verification")
    def test_2fa_verification_success(self, mock_handle_2fa, client):
        """Test successful 2FA verification."""
        # Mock successful 2FA verification
        mock_handle_2fa.return_value = {"success": True}

        with client.session_transaction() as sess:
            sess["pending_2fa"] = True
            sess["temp_username"] = "test@example.com"
            sess["temp_password"] = "password"

        response = client.post("/2fa", data={"code": "123456"})

        # Should redirect to main page
        assert response.status_code == 302
        assert response.location.endswith("/")

    @patch("blinkapp.services.auth_service.handle_2fa_verification")
    def test_2fa_verification_failure(self, mock_handle_2fa, client):
        """Test failed 2FA verification."""
        # Mock failed 2FA verification
        mock_handle_2fa.return_value = {"success": False, "error": "Invalid 2FA code"}

        with client.session_transaction() as sess:
            sess["pending_2fa"] = True
            sess["temp_username"] = "test@example.com"
            sess["temp_password"] = "password"

        response = client.post("/2fa", data={"code": "wrong"})

        # Should return error on 2FA page
        assert response.status_code == 400
        assert b"Invalid 2FA code" in response.data

    def test_login_missing_credentials(self, client):
        """Test login with missing username or password."""
        response = client.post("/login", data={"username": ""})

        assert response.status_code == 400
        assert b"Username and password required" in response.data

    def test_logout_clears_session(self, client):
        """Test logout clears authentication session."""
        with client.session_transaction() as sess:
            sess["authenticated"] = True

        response = client.post("/logout")

        # Should redirect to login
        assert response.status_code == 302
        assert response.location.endswith("/login")

    def test_main_page_with_saved_credentials(self, client):
        """Test main page loads with authenticated session."""
        with client.session_transaction() as sess:
            sess["authenticated"] = True

        response = client.get("/")

        # Should show main page
        assert response.status_code == 200

    @patch("blinkapp.services.auth_service.load_saved_blink")
    def test_main_page_without_saved_credentials(self, mock_load, client):
        """Test main page redirects to login without saved credentials."""
        # Mock no saved credentials
        mock_load.return_value = False

        response = client.get("/")

        # Should redirect to login
        assert response.status_code == 302
        assert response.location.endswith("/login")


class TestLoginFlowEnd2End:
    """End-to-end login flow tests."""

    @patch("blinkapp.services.auth_service.handle_login")
    @patch("blinkapp.services.auth_service.handle_2fa_verification")
    def test_complete_2fa_flow(self, mock_handle_2fa, mock_handle_login, client):
        """Test complete login flow with 2FA."""

        def mock_login_side_effect(username, password):
            # Simulate the session setting that happens in real handle_login
            from flask import session

            session["pending_2fa"] = True
            session["temp_username"] = username
            session["temp_password"] = password
            return {"success": False, "requires_2fa": True}

        # Step 1: Initial login requires 2FA
        mock_handle_login.side_effect = mock_login_side_effect

        with client:
            # Login with credentials
            response = client.post(
                "/login", data={"username": "test@example.com", "password": "password"}
            )

            # Should redirect to 2FA
            assert response.status_code == 302
            assert response.location.endswith("/2fa")

            # Step 2: 2FA page should show verification form
            response = client.get("/2fa")
            assert response.status_code == 200
            assert b"Verification Code" in response.data

            # Step 3: Submit 2FA code
            mock_handle_2fa.return_value = {"success": True}
            response = client.post("/2fa", data={"code": "123456"})

            # Should redirect to main page
            assert response.status_code == 302
            assert response.location.endswith("/")

    @patch("blinkapp.services.auth_service.handle_login")
    def test_direct_login_success(self, mock_handle_login, client):
        """Test direct login success without 2FA."""
        # Mock successful login
        mock_handle_login.return_value = {"success": True}

        # Login with credentials
        response = client.post(
            "/login", data={"username": "test@example.com", "password": "password"}
        )

        # Should redirect directly to main page
        assert response.status_code == 302
        assert response.location.endswith("/")
