"""Extra test coverage for auth_service.py missed lines."""

import unittest

from blinkapp.services.auth_service import (
    extract_username_domain,
    is_valid_email_format,
)


class TestAuthServiceExtra(unittest.TestCase):
    """Extra auth service coverage tests."""

    def test_is_valid_email_format_valid_emails(self) -> None:
        """Test is_valid_email_format with various valid emails."""
        valid_emails = [
            "user@example.com",
            "test.email@domain.org",
            "user+tag@example.co.uk",
            "123@numbers.com",
            "a@b.co",
        ]

        for email in valid_emails:
            with self.subTest(email=email):
                result = is_valid_email_format(email)
                self.assertTrue(result, f"Email {email} should be valid")

    def test_is_valid_email_format_invalid_emails(self) -> None:
        """Test is_valid_email_format with invalid emails."""
        invalid_emails = [
            "",
            "no-at-sign",
            "@no-user.com",
            "user@",
            "user@domain",  # No dot in domain
            "user@@domain.com",  # Multiple @ symbols
        ]

        for email in invalid_emails:
            with self.subTest(email=email):
                result = is_valid_email_format(email)
                self.assertFalse(result, f"Email {email} should be invalid")

    def test_extract_username_domain_edge_cases(self) -> None:
        """Test extract_username_domain with edge cases."""
        test_cases = [
            ("user@", ""),  # Empty domain
            ("@", ""),  # Just @ symbol
            ("user@@domain.com", ""),  # Double @ at start
        ]

        for username, expected_domain in test_cases:
            with self.subTest(username=username):
                result = extract_username_domain(username)
                self.assertEqual(result, expected_domain)


if __name__ == "__main__":
    unittest.main()
