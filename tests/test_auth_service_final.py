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
        """Test domain extraction with malformed email containing multiple @ symbols.

        Why: Malformed emails with multiple @ symbols can come from user input errors.
        What: Verifies function handles edge case by extracting first domain part.
        How: Passes email with multiple @ symbols and validates extraction logic.
        """
        result = extract_username_domain("test@sub@example.com")
        self.assertEqual(result, "sub")

    def test_is_valid_email_format_empty_username(self) -> None:
        """Test email validation with missing username part.

        Why: Users might accidentally submit forms with incomplete email addresses.
        What: Verifies validation correctly rejects emails with empty username.
        How: Passes email starting with @ and expects False return.
        """
        result = is_valid_email_format("@example.com")
        self.assertFalse(result)

    def test_is_valid_email_format_empty_domain(self) -> None:
        """Test email validation with missing domain part.

        Why: Incomplete email addresses are common user input errors during registration.
        What: Verifies validation correctly rejects emails with empty domain.
        How: Passes email ending with @ and expects False return.
        """
        result = is_valid_email_format("test@")
        self.assertFalse(result)
