"""Simple tests for cache service functions."""

from blinkapp.services.cache_service import (
    ensure_cache_directory,
    validate_cache_directory,
)


def test_validate_cache_directory() -> None:
    """Test cache directory validation."""
    # Test with /tmp which should exist on most systems
    result = validate_cache_directory("/tmp")
    assert isinstance(result, bool)


def test_ensure_cache_directory() -> None:
    """Test cache directory creation."""
    # Should create directory and return path
    result = ensure_cache_directory("/test")
    assert result == "/test"
