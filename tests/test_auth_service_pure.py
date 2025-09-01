#!/usr/bin/env python3
"""Tests for auth_service.py pure functions - targeting missed lines."""

import unittest

from blinkapp.services.auth_service import (
    create_auth_config,
    extract_username_domain,
    is_valid_email_format,
    validate_credentials,
)


class TestAuthServicePure(unittest.TestCase):
    """Pure unit tests for auth service functions.

    Inherits from unittest.TestCase because:
    - Tests pure functions without mocks or Flask dependencies
    - No async operations or global state to clean up
    - Simple validation and utility function testing
    """

    """Test auth service pure functions."""

    def test_extract_username_domain_with_at_symbol(self) -> None:
        """Test extract_username_domain with @ symbol - line 48."""
        result = extract_username_domain("user@example.com")

        # Should return domain part
        self.assertEqual(result, "example.com")

    def test_extract_username_domain_without_at_symbol(self) -> None:
        """Test extract_username_domain without @ symbol - line 50."""
        result = extract_username_domain("username")

        # Should return empty string
        self.assertEqual(result, "")

    def test_is_valid_email_format_valid_email(self) -> None:
        """Test is_valid_email_format with valid email - line 57."""
        result = is_valid_email_format("user@example.com")

        # Should return True for valid email
        self.assertTrue(result)

    def test_is_valid_email_format_empty_email(self) -> None:
        """Test is_valid_email_format with empty email - line 55."""
        result = is_valid_email_format("")

        # Should return False for empty email
        self.assertFalse(result)

    def test_is_valid_email_format_no_at_symbol(self) -> None:
        """Test is_valid_email_format without @ symbol - line 55."""
        result = is_valid_email_format("username")

        # Should return False without @ symbol
        self.assertFalse(result)

    def test_is_valid_email_format_none(self) -> None:
        """Test is_valid_email_format with None - line 55."""
        from typing import cast

        result = is_valid_email_format(
            cast(str, None)
        )  # Intentionally testing invalid input

        # Should return False for None
        self.assertFalse(result)

    def test_validate_credentials_valid(self) -> None:
        """Test validate_credentials with valid credentials - line 63."""
        result = validate_credentials("user@example.com", "password123")

        # Should return True for valid credentials
        self.assertTrue(result)

    def test_validate_credentials_empty_username(self) -> None:
        """Test validate_credentials with empty username - line 63."""
        result = validate_credentials("", "password123")

        # Should return False for empty username
        self.assertFalse(result)

    def test_validate_credentials_empty_password(self) -> None:
        """Test validate_credentials with empty password - line 63."""
        result = validate_credentials("user@example.com", "")

        # Should return False for empty password
        self.assertFalse(result)

    def test_validate_credentials_no_at_symbol(self) -> None:
        """Test validate_credentials without @ in username - line 63."""
        result = validate_credentials("username", "password123")

        # Should return False without @ symbol
        self.assertFalse(result)

    def test_create_auth_config(self) -> None:
        """Test create_auth_config - line 68."""
        result = create_auth_config("user@example.com", "password123")

        # Should return dict with username and password
        expected = {"username": "user@example.com", "password": "password123"}
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
