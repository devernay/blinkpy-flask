"""Working tests for __main__.py to reach 70% coverage."""

from unittest.mock import Mock, patch

from blinkapp.__main__ import (
    configure_logging,
    create_argument_parser,
    run_app,
)


def test_create_argument_parser_defaults():
    """Test argument parser with default values."""
    parser = create_argument_parser()
    args = parser.parse_args([])
    assert args.host == "0.0.0.0"
    assert args.port == 5001


def test_run_app_dump_system():
    """Test run_app with dump system option."""
    args = Mock()
    args.dump_system = True

    with patch("blinkapp.services.utils_service.handle_dump_system") as mock_dump:
        run_app(args)
        mock_dump.assert_called_once()


def test_run_app_normal():
    """Test run_app normal execution."""
    args = Mock()
    args.dump_system = False
    args.cache = "/test"

    with (
        patch("blinkapp.__main__.app") as mock_app,
        patch("blinkapp.__main__.startup") as mock_startup,
    ):
        mock_app.run = Mock()

        run_app(args)

        mock_startup.assert_called_once()


def test_configure_logging_levels():
    """Test logging configuration."""
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        configure_logging("DEBUG")
        assert mock_logger.setLevel.called
