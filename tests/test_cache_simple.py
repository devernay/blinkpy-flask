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
    import os
    import tempfile

    # Use a temporary directory that we can actually write to
    with tempfile.TemporaryDirectory() as temp_dir:
        test_path = os.path.join(temp_dir, "test_cache")
        result = ensure_cache_directory(test_path)
        assert result == test_path
        assert os.path.exists(test_path)
        assert os.path.isdir(test_path)
