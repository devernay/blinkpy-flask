"""Simple test coverage for auth_service.py functions."""

from unittest.mock import Mock, patch

from aiohttp import ClientSession

from blinkapp.services import auth_service

from .test_base import create_mock_auth, create_mock_blink_instance


class TestCreateBlinkSession:
    """Test _create_blink_session function."""

    def test_create_blink_session_default(self):
        """Test creating session with default factory."""
        with patch("aiohttp.ClientSession") as mock_session:
            mock_instance = Mock(spec=ClientSession)
            mock_session.return_value = mock_instance

            result = auth_service._create_blink_session()

            assert result == mock_instance


class TestCreateAuthObject:
    """Test _create_auth_object function."""

    def test_create_auth_object_default(self):
        """Test creating auth object with default factory."""
        with patch("blinkpy.auth.Auth") as mock_auth:
            mock_instance = create_mock_auth()
            mock_auth.return_value = mock_instance
            mock_session = Mock(spec=ClientSession)

            result = auth_service._create_auth_object(
                "test@example.com", "password", mock_session
            )

            assert result == mock_instance


class TestIsValidEmailFormat:
    """Test is_valid_email_format function."""

    def test_is_valid_email_format_true(self):
        """Test valid email format returns True."""
        result = auth_service.is_valid_email_format("test@example.com")
        assert result is True

    def test_is_valid_email_format_false(self):
        """Test invalid email format returns False."""
        result = auth_service.is_valid_email_format("invalid-email")
        assert result is False


class TestIsBlinkAuthenticated:
    """Test is_blink_authenticated function."""

    def test_is_blink_authenticated_true(self):
        """Test blink authentication check returns True."""
        mock_blink = create_mock_blink_instance()
        mock_blink.auth.token = "some-token"

        result = auth_service.is_blink_authenticated(mock_blink)

        assert result is True

    def test_is_blink_authenticated_false_no_blink(self):
        """Test blink authentication check returns False when no blink."""
        with patch(
            "blinkapp.services.blink_service.ensure_blink_initialized",
            side_effect=RuntimeError,
        ):
            result = auth_service.is_blink_authenticated()

            assert result is False

    def test_is_blink_authenticated_false_no_token(self):
        """Test blink authentication check returns False when no token."""
        mock_blink = create_mock_blink_instance()
        mock_blink.auth.token = None

        result = auth_service.is_blink_authenticated(mock_blink)

        assert result is False


class TestHandleLogout:
    """Test handle_logout function."""

    def test_handle_logout_success(self):
        """Test successful logout handling."""
        from flask import Flask

        app = Flask(__name__)
        app.secret_key = "test-secret-key"

        with app.test_request_context():
            with patch(
                "blinkapp.services.blink_service.get_blink_instance"
            ) as mock_get:
                mock_blink = create_mock_blink_instance()
                mock_get.return_value = mock_blink

                result = auth_service.handle_logout()

                assert result["success"] is True

    def test_handle_logout_no_blink(self):
        """Test logout handling with no blink instance."""
        from flask import Flask

        app = Flask(__name__)
        app.secret_key = "test-secret-key"

        with app.test_request_context():
            with patch(
                "blinkapp.services.blink_service.get_blink_instance", return_value=None
            ):
                result = auth_service.handle_logout()

                assert result["success"] is True
