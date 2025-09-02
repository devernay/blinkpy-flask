#!/usr/bin/env python3
"""Unit tests for __main__.py module - CLI entry point functionality.

This file contains ONLY unit tests for the CLI entry point module:
- Argument parser creation and validation
- Command-line argument handling
- App runner function behavior
- Logging configuration

DO NOT add integration tests here - those belong in test_integration_*.py files.
"""

import argparse
import logging
from unittest.mock import Mock, patch

import pytest

from blinkapp.__main__ import (
    configure_logging,
    create_argument_parser,
    run_app,
)


class TestArgumentParser:
    """Test argument parser creation and configuration."""

    def test_create_argument_parser_defaults(self) -> None:
        """Test argument parser with default values."""
        parser = create_argument_parser()
        args = parser.parse_args([])
        assert args.host == "0.0.0.0"
        assert args.port == 5001

    def test_create_argument_parser_custom_args(self) -> None:
        """Test argument parser with custom arguments."""
        parser = create_argument_parser()
        args = parser.parse_args(["--host", "127.0.0.1", "--port", "8080", "--debug"])
        assert args.host == "127.0.0.1"
        assert args.port == 8080
        assert args.debug is True


class TestRunApp:
    """Test run_app function."""

    def test_run_app_dump_system(self) -> None:
        """Test run_app with dump system option."""
        args = Mock(spec=argparse.Namespace)
        args.dump_system = True

        with patch("blinkapp.services.debug_service.handle_dump_system") as mock_dump:
            run_app(args)
            mock_dump.assert_called_once()

    def test_run_app_normal_mode(self) -> None:
        """Test run_app in normal mode."""
        args = Mock(spec=argparse.Namespace)
        args.dump_system = False
        args.host = "127.0.0.1"
        args.port = 5001
        args.debug = False
        args.cache = None
        args.log_level = "INFO"

        with patch("blinkapp.app.run") as mock_run:
            run_app(args)
            mock_run.assert_called_once_with(
                host="127.0.0.1", port=5001, debug=False
            )


class TestLogging:
    """Test logging configuration."""

    def test_configure_logging_levels(self) -> None:
        """Test logging configuration."""
        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = Mock(spec=logging.Logger)
            mock_get_logger.return_value = mock_logger

            configure_logging("DEBUG")
            assert mock_logger.setLevel.called
