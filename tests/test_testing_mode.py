"""Test that testing mode prevents external API calls."""

from unittest.mock import patch

import pytest


def test_testing_mode_enabled():
    """Test that testing mode is automatically enabled in tests."""
    from blinkapp.config import Config

    assert Config.TESTING_MODE is True


def test_blink_instance_requires_mocking():
    """Test that get_blink_instance requires proper mocking in testing mode."""
    from blinkapp.services.blink_service import get_blink_instance

    # Should raise an error when not mocked
    with pytest.raises(
        RuntimeError, match="Testing mode enabled but no Blink instance mocked"
    ):
        get_blink_instance()


def test_blink_instance_works_with_proper_mock():
    """Test that get_blink_instance works when properly mocked."""
    from blinkapp.services.blink_service import get_blink_instance
    from tests.test_base import create_mock_blink_instance

    mock_blink = create_mock_blink_instance(available=True)

    with patch("blinkapp.services.blink_service._blink", mock_blink):
        blink = get_blink_instance()
        assert blink is not None
        assert blink.available is True


def test_ensure_blink_initialized_requires_mocking():
    """Test that ensure_blink_initialized requires proper mocking in testing mode."""
    from blinkapp.services.blink_service import ensure_blink_initialized

    # Should raise an error when not mocked
    with pytest.raises(
        RuntimeError, match="Testing mode enabled but no Blink instance mocked"
    ):
        ensure_blink_initialized()


def test_ensure_blink_initialized_works_with_proper_mock():
    """Test that ensure_blink_initialized works when properly mocked."""
    from blinkapp.services.blink_service import ensure_blink_initialized
    from tests.test_base import create_mock_blink_instance

    mock_blink = create_mock_blink_instance(available=True)

    with patch("blinkapp.services.blink_service._blink", mock_blink):
        blink = ensure_blink_initialized()
        assert blink is not None
        assert blink.available is True


def test_network_guard_blocks_connections():
    """Test that network guard blocks socket connections."""
    import socket

    from blinkapp.utils.network_guard import NetworkGuard

    with NetworkGuard():
        with pytest.raises(RuntimeError, match="Network connections blocked"):
            socket.socket()


def test_network_guard_blocks_aiohttp():
    """Test that network guard blocks aiohttp requests."""
    import aiohttp

    from blinkapp.utils.network_guard import NetworkGuard

    with NetworkGuard():
        with pytest.raises(RuntimeError, match="HTTP requests blocked"):
            aiohttp.ClientSession()
