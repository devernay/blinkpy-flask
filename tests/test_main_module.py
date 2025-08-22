#!/usr/bin/env python3
"""Tests for __main__.py module - CLI entry point functionality."""

import argparse
import logging
from unittest.mock import Mock, patch

import pytest

from blinkapp.__main__ import (
    configure_logging,
    create_argument_parser,
    main,
    run_app,
    setup_signal_handlers,
    signal_handler,
)
from blinkapp.models.responses import Config


class TestArgumentParser:
    """Test argument parser creation and configuration."""

    def test_create_argument_parser(self) -> None:
        """Test argument parser creation with default values."""
        parser = create_argument_parser()

        assert isinstance(parser, argparse.ArgumentParser)
        assert (
            parser.description
            and "Blink Camera Flask Web Interface" in parser.description
        )

    def test_parser_default_values(self) -> None:
        """Test parser with no arguments uses defaults."""
        parser = create_argument_parser()
        args = parser.parse_args([])

        assert args.host == Config.DEFAULT_HOST
        assert args.port == Config.DEFAULT_PORT
        assert args.debug is False
        assert args.log_level == "INFO"
        assert args.cache == Config.DEFAULT_CACHE_DIR
        assert args.dump_system is False

    def test_parser_custom_values(self) -> None:
        """Test parser with custom arguments."""
        parser = create_argument_parser()
        args = parser.parse_args(
            [
                "--host",
                "0.0.0.0",
                "--port",
                "8080",
                "--debug",
                "--log-level",
                "DEBUG",
                "--cache",
                "/tmp/cache",
                "--dump-system",
            ]
        )

        assert args.host == "0.0.0.0"
        assert args.port == 8080
        assert args.debug is True
        assert args.log_level == "DEBUG"
        assert args.cache == "/tmp/cache"
        assert args.dump_system is True


class TestLoggingConfiguration:
    """Test logging configuration functionality."""

    def test_configure_logging_info(self) -> None:
        """Test logging configuration with INFO level."""
        configure_logging("INFO")

        assert logging.getLogger().level == logging.INFO
        assert logging.getLogger("blinkpy").level == logging.INFO
        assert logging.getLogger("werkzeug").level == logging.INFO
        assert logging.getLogger("flask").level == logging.INFO

    def test_configure_logging_debug(self) -> None:
        """Test logging configuration with DEBUG level."""
        configure_logging("DEBUG")

        assert logging.getLogger().level == logging.DEBUG
        assert logging.getLogger("blinkpy").level == logging.DEBUG

    def test_configure_logging_error(self) -> None:
        """Test logging configuration with ERROR level."""
        configure_logging("ERROR")

        assert logging.getLogger().level == logging.ERROR


class TestSignalHandling:
    """Test signal handling functionality."""

    @patch("signal.signal")
    @patch("atexit.register")
    def test_setup_signal_handlers(self, mock_atexit: Mock, mock_signal: Mock) -> None:
        """Test signal handler setup."""
        setup_signal_handlers()

        # Verify signal handlers are registered
        assert mock_signal.call_count == 2
        mock_atexit.assert_called_once()

    @patch("sys.exit")
    def test_signal_handler(self, mock_exit: Mock) -> None:
        """Test signal handler execution."""
        signal_handler(15, None)

        mock_exit.assert_called_once_with(0)


class TestAppExecution:
    """Test application execution functionality."""

    @patch("blinkapp.services.utils_service.handle_dump_system")
    def test_run_app_dump_system(self, mock_dump: Mock) -> None:
        """Test run_app with dump_system flag."""
        args = Mock()
        args.dump_system = True

        run_app(args)

        mock_dump.assert_called_once()

    @patch("blinkapp.app.run")
    def test_run_app_normal(self, mock_run: Mock) -> None:
        """Test normal app execution."""
        args = Mock()
        args.dump_system = False
        args.cache = "/tmp/test"
        args.host = "127.0.0.1"
        args.port = 5000
        args.debug = False

        run_app(args)

        mock_run.assert_called_once_with(host="127.0.0.1", port=5000, debug=False)

    @patch("blinkapp.app.run")
    def test_run_app_no_cache_override(self, mock_run: Mock) -> None:
        """Test app execution without cache override."""
        args = Mock()
        args.dump_system = False
        args.cache = None
        args.host = "0.0.0.0"
        args.port = 8080
        args.debug = True

        run_app(args)

        mock_run.assert_called_once_with(host="0.0.0.0", port=8080, debug=True)


class TestMainFunction:
    """Test main function integration."""

    @patch("blinkapp.__main__.run_app")
    @patch("blinkapp.__main__.setup_signal_handlers")
    @patch("blinkapp.__main__.configure_logging")
    @patch("sys.argv", ["blinkapp"])
    def test_main_default_args(
        self, mock_logging: Mock, mock_signals: Mock, mock_run: Mock
    ) -> None:
        """Test main function with default arguments."""
        with patch("blinkapp.app.config", {}) as mock_config:
            main()

            mock_logging.assert_called_once_with("INFO")
            mock_signals.assert_called_once()
            mock_run.assert_called_once()
            assert mock_config["CACHE_DIR"] == Config.DEFAULT_CACHE_DIR

    @patch("blinkapp.__main__.run_app")
    @patch("blinkapp.__main__.setup_signal_handlers")
    @patch("blinkapp.__main__.configure_logging")
    @patch("blinkapp.cleanup_resources")
    @patch("sys.argv", ["blinkapp", "--log-level", "DEBUG", "--cache", "/custom"])
    def test_main_custom_args(
        self, mock_cleanup: Mock, mock_logging: Mock, mock_signals: Mock, mock_run: Mock
    ) -> None:
        """Test main function with custom arguments."""
        with patch("blinkapp.app.config", {}) as mock_config:
            main()

            mock_logging.assert_called_once_with("DEBUG")
            mock_signals.assert_called_once()
            mock_run.assert_called_once()
            assert mock_config["CACHE_DIR"] == "/custom"

    @patch("blinkapp.__main__.run_app", side_effect=KeyboardInterrupt)
    @patch("blinkapp.__main__.setup_signal_handlers")
    @patch("blinkapp.__main__.configure_logging")
    @patch("blinkapp.app.config", {})
    @patch("sys.argv", ["blinkapp"])
    def test_main_keyboard_interrupt(
        self, mock_logging: Mock, mock_signals: Mock, mock_run: Mock
    ) -> None:
        """Test main function handles KeyboardInterrupt."""
        main()

    @patch("blinkapp.__main__.run_app", side_effect=Exception("Test error"))
    @patch("blinkapp.__main__.setup_signal_handlers")
    @patch("blinkapp.__main__.configure_logging")
    @patch("blinkapp.app.config", {})
    @patch("sys.argv", ["blinkapp"])
    def test_main_exception_cleanup(
        self, mock_logging: Mock, mock_signals: Mock, mock_run: Mock
    ) -> None:
        """Test main function cleanup on exception."""
        with pytest.raises(Exception, match="Test error"):
            main()
