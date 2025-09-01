#!/usr/bin/env python3
"""Final tests for services/auth_service.py - targeting more missed lines."""

import unittest

from blinkapp.services.auth_service import (
    extract_username_domain,
    is_valid_email_format,
)


class TestAuthServiceFinal(unittest.TestCase):
    """Test auth service functions with more missed lines."""

    def test_extract_username_domain_multiple_at(self) -> None:
        """Test extract_username_domain with multiple @ symbols."""
        result = extract_username_domain("test@sub@example.com")
        self.assertEqual(result, "sub")

    def test_is_valid_email_format_empty_username(self) -> None:
        """Test is_valid_email_format with empty username."""
        result = is_valid_email_format("@example.com")
        self.assertFalse(result)

    def test_is_valid_email_format_empty_domain(self) -> None:
        """Test is_valid_email_format with empty domain."""
        result = is_valid_email_format("test@")
        self.assertFalse(result)
