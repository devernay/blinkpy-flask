"""Minimal tests for __main__.py to achieve basic coverage."""

import argparse
import signal
from unittest.mock import Mock, patch

from blinkapp.__main__ import (
    configure_logging,
    create_argument_parser,
    run_app,
    setup_signal_handlers,
    signal_handler,
)


def test_create_argument_parser():
    """Test argument parser creation."""
    parser = create_argument_parser()
    assert isinstance(parser, argparse.ArgumentParser)

    # Test default arguments - use actual defaults from Config
    args = parser.parse_args([])
    assert args.host == "0.0.0.0"  # Actual default from Config
    assert args.port == 5000
    assert args.debug is False


def test_configure_logging():
    """Test logging configuration."""
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        configure_logging("DEBUG")

        # Verify setLevel was called
        assert mock_logger.setLevel.called


def test_setup_signal_handlers():
    """Test signal handler setup."""
    with patch("signal.signal") as mock_signal, patch("atexit.register") as mock_atexit:
        setup_signal_handlers()

        # Verify signal handlers were registered
        mock_signal.assert_any_call(signal.SIGINT, signal_handler)
        mock_signal.assert_any_call(signal.SIGTERM, signal_handler)
        assert mock_atexit.called


def test_signal_handler():
    """Test signal handler function."""
    with (
        patch("blinkapp.logger") as mock_logger,
        patch("blinkapp.__main__.cleanup_resources") as mock_cleanup,
        patch("sys.exit") as mock_exit,
    ):
        signal_handler(signal.SIGINT, None)

        assert mock_logger.info.called
        assert mock_cleanup.called
        mock_exit.assert_called_with(0)


def test_run_app_dump_system():
    """Test run_app with dump-system option."""
    args = Mock()
    args.dump_system = True

    with patch("blinkapp.services.utils_service.handle_dump_system") as mock_dump:
        run_app(args)
        assert mock_dump.called


def test_run_app_normal():
    """Test run_app normal execution."""
    args = Mock()
    args.dump_system = False
    args.cache = "/test/cache"
    args.host = "localhost"
    args.port = 8080
    args.debug = True

    with (
        patch("blinkapp.__main__.app") as mock_app,
        patch("blinkapp.__main__.startup") as mock_startup,
    ):
        # Mock app.run to prevent actual server start
        mock_app.run = Mock()

        run_app(args)

        assert mock_startup.called
        mock_app.run.assert_called_with(host="localhost", port=8080, debug=True)
