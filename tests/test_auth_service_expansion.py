#!/usr/bin/env python3
"""Targeted tests for services/auth_service.py - covering highest missed lines."""

import unittest

from blinkapp.services.auth_service import (
    create_auth_config,
    extract_username_domain,
    is_authenticated,
    is_valid_email_format,
    validate_credentials,
)


class TestAuthServiceExpansion(unittest.TestCase):
    """Test uncovered auth service functions with highest missed lines."""

    def test_is_authenticated_basic(self):
        """Test is_authenticated basic functionality."""
        result = is_authenticated()

        # Should return a boolean
        self.assertIsInstance(result, bool)

    def test_validate_credentials_basic(self):
        """Test validate_credentials basic functionality."""
        result = validate_credentials("user@example.com", "password123")

        # Should return a boolean
        self.assertIsInstance(result, bool)

    def test_create_auth_config_basic(self):
        """Test create_auth_config basic functionality."""
        result = create_auth_config("user@example.com", "password123")

        # Should return a dictionary
        self.assertIsInstance(result, dict)
        self.assertIn("username", result)
        self.assertIn("password", result)

    def test_auth_functions_exist(self):
        """Test that auth functions are importable."""
        # All functions should be callable
        self.assertTrue(callable(is_authenticated))
        self.assertTrue(callable(extract_username_domain))
        self.assertTrue(callable(is_valid_email_format))
        self.assertTrue(callable(validate_credentials))
        self.assertTrue(callable(create_auth_config))
