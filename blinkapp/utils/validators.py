"""
Validation utilities for the Blink Camera Flask application.

This module provides pure validation functions for input sanitization,
security checks, and data validation. Functions are designed to be stateless
and reusable across different modules.
"""

import logging
import re

logger = logging.getLogger(__name__)

__all__ = [
    "validate_string_input",
    "validate_camera_id",
    "validate_tcp_url",
    "is_valid_email_format",
    "validate_credentials",
]


def validate_string_input(value: str, max_length: int, field_name: str) -> str:
    """Validate string input for length and basic safety.

    Args:
        value: String value to validate.
        max_length: Maximum allowed length.
        field_name: Name of the field for error messages.

    Returns:
        Validated string value.

    Raises:
        ValidationError: If validation fails.
    """
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} cannot be empty")

    if len(value) > max_length:
        raise ValueError(f"{field_name} too long (max {max_length} characters)")

    value_lower = value.lower()

    # XSS prevention
    if "<" in value or ">" in value or "&" in value:
        raise ValueError(f"{field_name} contains invalid characters")

    # SQL injection prevention
    sql_patterns = [
        "'",
        '"',
        ";",
        "--",
        "/*",
        "*/",
        "drop",
        "select",
        "insert",
        "update",
        "delete",
        "union",
        "exec",
        "execute",
    ]
    if any(pattern in value_lower for pattern in sql_patterns):
        raise ValueError(f"{field_name} contains invalid characters")

    # JavaScript injection prevention
    js_patterns = ["javascript:", "vbscript:", "onload", "onerror", "onclick"]
    if any(pattern in value_lower for pattern in js_patterns):
        raise ValueError(f"{field_name} contains invalid characters")

    # Template injection prevention
    template_patterns = ["<%", "%>", "${", "#{"]
    if any(pattern in value for pattern in template_patterns):
        raise ValueError(f"{field_name} contains invalid characters")

    return value


def validate_camera_id(camera_id: str) -> str:
    """Validate camera ID format."""
    if not camera_id or not isinstance(camera_id, str):
        raise ValueError("Invalid camera ID")

    camera_id = camera_id.strip()
    if not camera_id:
        raise ValueError("Camera ID cannot be empty")

    # Basic alphanumeric validation
    if not re.match(r"^[a-zA-Z0-9_-]+$", camera_id):
        raise ValueError("Camera ID contains invalid characters")

    return camera_id


def validate_tcp_url(url: str) -> str:
    """Validate TCP URL format."""
    if not url or not isinstance(url, str):
        raise ValueError("Invalid TCP URL")

    url = url.strip()
    if not url.startswith("tcp://"):
        raise ValueError("URL must start with tcp://")

    return url


def is_valid_email_format(email: str) -> bool:
    """Check if email has valid format."""
    if not email or not isinstance(email, str):
        return False

    # Basic email regex
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip()))


def validate_credentials(username: str, password: str) -> tuple[str, str]:
    """Validate login credentials."""
    if not username or not password:
        raise ValueError("Username and password are required")

    username = validate_string_input(username, 100, "Username")
    password = validate_string_input(password, 200, "Password")

    if not is_valid_email_format(username):
        raise ValueError("Username must be a valid email address")

    return username, password
