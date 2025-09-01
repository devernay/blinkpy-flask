"""Working tests for __main__.py to reach 70% coverage."""

import argparse
import logging
from unittest.mock import Mock, patch

from blinkapp.__main__ import (
    configure_logging,
    create_argument_parser,
    run_app,
)


def test_create_argument_parser_defaults() -> None:
    """Test argument parser with default values."""
    parser = create_argument_parser()
    args = parser.parse_args([])
    assert args.host == "0.0.0.0"
    assert args.port == 5001


def test_run_app_dump_system() -> None:
    """Test run_app with dump system option."""
    args = Mock(spec=argparse.Namespace)
    args.dump_system = True

    with patch("blinkapp.services.debug_service.handle_dump_system") as mock_dump:
        run_app(args)
        mock_dump.assert_called_once()


def test_configure_logging_levels() -> None:
    """Test logging configuration."""
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = Mock(spec=logging.Logger)
        mock_get_logger.return_value = mock_logger

        configure_logging("DEBUG")
        assert mock_logger.setLevel.called
