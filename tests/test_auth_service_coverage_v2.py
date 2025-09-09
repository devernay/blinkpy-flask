"""Test coverage for auth_service."""

from unittest.mock import Mock, patch

from blinkapp.services import auth_service

from .test_base import BaseTestCase


class TestAuthValidation(BaseTestCase):
    """Test authentication validation functions."""

    def test_is_valid_email_format_valid(self):
        """Test valid email format."""
        assert auth_service.is_valid_email_format("test@example.com") is True
        assert auth_service.is_valid_email_format("user.name+tag@domain.co.uk") is True

    def test_is_valid_email_format_invalid(self):
        """Test invalid email format."""
        assert auth_service.is_valid_email_format("invalid") is False
        assert auth_service.is_valid_email_format("@domain.com") is False
        assert auth_service.is_valid_email_format("user@") is False
        assert auth_service.is_valid_email_format("") is False

    def test_validate_credentials_valid(self):
        """Test valid credentials."""
        assert (
            auth_service.validate_credentials("test@example.com", "password123") is True
        )

    def test_validate_credentials_invalid_email(self):
        """Test invalid email in credentials."""
        assert auth_service.validate_credentials("invalid", "password123") is False

    def test_validate_credentials_empty_password(self):
        """Test empty password in credentials."""
        assert auth_service.validate_credentials("test@example.com", "") is False

    def test_validate_credentials_empty_username(self):
        """Test empty username in credentials."""
        assert auth_service.validate_credentials("", "password123") is False


class TestBlinkAuthentication(BaseTestCase):
    """Test Blink authentication functions."""

    def test_is_blink_authenticated_no_instance(self):
        """Test authentication check with no instance."""
        result = auth_service.is_blink_authenticated(None)
        assert result is False

    def test_is_blink_authenticated_with_mock(self):
        """Test authentication check with mock instance."""
        mock_blink = Mock()
        mock_auth = Mock()
        mock_auth.token = "valid_token"
        mock_blink.auth = mock_auth

        result = auth_service.is_blink_authenticated(mock_blink)
        assert result is True

    def test_is_blink_authenticated_startup_false(self):
        """Test authentication check with no token."""
        mock_blink = Mock()
        mock_auth = Mock()
        mock_auth.token = None
        mock_blink.auth = mock_auth

        result = auth_service.is_blink_authenticated(mock_blink)
        assert result is False

    def test_is_blink_authenticated_exception(self):
        """Test authentication check with exception."""
        mock_blink = Mock()
        mock_auth = Mock()
        mock_auth.token = "valid_token"
        mock_blink.auth = mock_auth

        result = auth_service.is_blink_authenticated(mock_blink)
        assert result is True


class TestSessionCreation(BaseTestCase):
    """Test session creation functions."""

    def test_create_blink_session_custom_factory(self):
        """Test creating blink session with custom factory."""
        mock_session = Mock()

        with patch("aiohttp.ClientSession", return_value=mock_session) as mock_factory:
            result = auth_service._create_blink_session()

            assert result == mock_session
            mock_factory.assert_called_once()


class TestHandleLogin(BaseTestCase):
    """Test handle_login function."""

    def test_handle_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        result = auth_service.handle_login("invalid", "")

        assert result["success"] is False
        assert "error" in result
