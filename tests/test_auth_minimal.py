"""Minimal tests for auth_service.py to improve coverage."""

import asyncio
from unittest.mock import Mock, patch

from blinkapp.services.auth_service import (
    is_authenticated,
    load_saved_blink,
)


def test_is_authenticated_true():
    """Test authentication check when authenticated."""
    mock_blink = Mock()
    mock_blink.auth.token = "valid_token"

    result = is_authenticated(blink_instance=mock_blink)
    assert result is True


def test_is_authenticated_false():
    """Test authentication check when not authenticated."""
    mock_blink = Mock()
    mock_blink.auth.token = None

    result = is_authenticated(blink_instance=mock_blink)
    assert result is False


def test_is_authenticated_no_blink():
    """Test authentication check when blink is None."""
    result = is_authenticated(blink_instance=None)
    assert result is False


def test_load_saved_blink():
    """Test loading saved blink configuration."""
    with (
        patch("blinkapp.services.cache_service.load_cache") as mock_load,
        patch("blinkapp.services.auth_service.initialize_blink") as mock_init,
    ):
        mock_load.return_value = {"username": "test@example.com", "password": "pass"}

        # Mock the async function properly
        async def mock_init_func(*args, **kwargs):
            return True

        mock_init.return_value = mock_init_func("test", "pass")

        result = asyncio.run(load_saved_blink())
        assert result is True
