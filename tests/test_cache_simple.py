"""Simple tests for cache service functions."""

from unittest.mock import Mock

from blinkapp.services.cache_service import (
    ensure_cache_directory,
    validate_cache_directory,
)


def test_validate_cache_directory():
    """Test cache directory validation."""
    # Test with /tmp which should exist on most systems
    result = validate_cache_directory("/tmp")
    assert isinstance(result, bool)


def test_ensure_cache_directory():
    """Test cache directory creation."""
    mock_validator = Mock(return_value=True)

    # Should not create directory if validator returns True
    ensure_cache_directory("/test", validator=mock_validator)
    mock_validator.assert_called_once_with("/test")
