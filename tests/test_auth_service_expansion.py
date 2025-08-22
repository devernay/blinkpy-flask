#!/usr/bin/env python3
"""Targeted tests for services/auth_service.py - covering highest missed lines."""

import unittest

from blinkapp.services.auth_service import (
    create_auth_config,
    is_authenticated,
    validate_credentials,
)


class TestAuthServiceExpansion(unittest.TestCase):
    """Test uncovered auth service functions with highest missed lines."""

    def test_is_authenticated_basic(self) -> None:
        """Test is_authenticated basic functionality."""
        result = is_authenticated()

        # Should return a boolean
        self.assertIsInstance(result, bool)

    def test_validate_credentials_basic(self) -> None:
        """Test validate_credentials basic functionality."""
        result = validate_credentials("user@example.com", "password123")

        # Should return a boolean
        self.assertIsInstance(result, bool)

    def test_create_auth_config_basic(self) -> None:
        """Test create_auth_config basic functionality."""
        result = create_auth_config("user@example.com", "password123")

        # Should return a dictionary
        self.assertIsInstance(result, dict)
        self.assertIn("username", result)
        self.assertIn("password", result)
