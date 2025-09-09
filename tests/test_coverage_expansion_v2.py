"""Targeted coverage expansion tests for highest missed line modules."""

from unittest.mock import patch

from blinkapp.services import auth_service


class TestAuthService:
    """Test auth_service.py functions (104 missed lines)."""

    @patch("blinkapp.services.auth_service.get_blink_instance")
    def test_is_blink_authenticated_no_instance(self, mock_get_blink):
        """Test is_blink_authenticated when no blink instance."""
        mock_get_blink.return_value = None

        result = auth_service.is_blink_authenticated()
        assert result is False

    def test_is_valid_email_format_valid(self):
        """Test is_valid_email_format with valid email."""
        result = auth_service.is_valid_email_format("test@example.com")
        assert result is True

    def test_is_valid_email_format_invalid(self):
        """Test is_valid_email_format with invalid email."""
        result = auth_service.is_valid_email_format("invalid-email")
        assert result is False

    def test_validate_credentials_empty(self):
        """Test validate_credentials with empty credentials."""
        result = auth_service.validate_credentials("", "")
        assert result is False

    def test_validate_credentials_valid(self):
        """Test validate_credentials with valid credentials."""
        result = auth_service.validate_credentials("test@example.com", "password123")
        assert result is True

    def test_validate_credentials_invalid_email(self):
        """Test validate_credentials with invalid email format."""
        result = auth_service.validate_credentials("invalid-email", "password123")
        assert result is False


class TestApiResponses:
    """Test utils/api_responses.py functions (9 missed lines)."""

    def test_create_api_response_success(self):
        """Test create_api_response with success."""
        from blinkapp.utils.api_responses import create_api_response

        result = create_api_response(success=True, data={"test": "data"})
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["data"] == {"test": "data"}
        assert "timestamp" in result

    def test_create_api_response_error(self):
        """Test create_api_response with error."""
        from blinkapp.utils.api_responses import create_api_response

        result = create_api_response(success=False, error="Test error")
        assert isinstance(result, dict)
        assert result["success"] is False
        assert result["error"] == "Test error"
        assert "timestamp" in result

    def test_create_api_response_success_no_data(self):
        """Test create_api_response success without data."""
        from blinkapp.utils.api_responses import create_api_response

        result = create_api_response(success=True)
        assert result["success"] is True
        assert "data" not in result


class TestConnexionDecorators:
    """Test utils/connexion_decorators.py (1 missed line)."""

    def test_import_connexion_decorators(self):
        """Test importing connexion_decorators module."""
        from blinkapp.utils import connexion_decorators

        assert connexion_decorators is not None
