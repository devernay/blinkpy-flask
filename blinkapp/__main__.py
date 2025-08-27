#!/usr/bin/env python3
"""Main entry point for running blinkapp as a module."""

import argparse
import atexit
import logging
import signal
import sys
from typing import Any

# This module is an entry point and doesn't export anything
__all__: list[str] = []

from blinkapp import app, cleanup_resources, startup
from blinkapp.models.responses import Config


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(description="Blink Camera Flask Web Interface")
    parser.add_argument(
        "--host",
        default=Config.DEFAULT_HOST,
        help=f"Host to bind to (default: {Config.DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=Config.DEFAULT_PORT,
        help=f"Port to bind to (default: {Config.DEFAULT_PORT})",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level (default: INFO)",
    )
    parser.add_argument(
        "--cache",
        default=Config.DEFAULT_CACHE_DIR,
        help=f"Cache directory (default: {Config.DEFAULT_CACHE_DIR})",
    )
    parser.add_argument(
        "--dump-system", action="store_true", help="Dump system info and exit"
    )
    return parser


def setup_signal_handlers() -> None:
    """Set up signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(cleanup_resources)


def run_app(args: argparse.Namespace) -> None:
    """Run the Flask application with given arguments."""
    if args.dump_system:
        from blinkapp.services.debug_service import handle_dump_system

        handle_dump_system()
        return

    if args.cache:
        app.config["CACHE_DIR"] = args.cache

    startup()
    app.run(host=args.host, port=args.port, debug=args.debug)


def signal_handler(signum: int, frame: Any) -> None:
    """Handle shutdown signals.

    Args:
        signum: Signal number received
        frame: Current stack frame (unused)

    Side Effects:
        Triggers cleanup and exits application
    """
    from blinkapp import logger

    logger.info(f"Received signal {signum}, shutting down...")
    cleanup_resources()
    sys.exit(0)


def configure_logging(log_level: str) -> None:
    """Configure logging levels for all loggers."""
    level = getattr(logging, log_level)
    logging.getLogger().setLevel(level)
    logging.getLogger("blinkpy").setLevel(level)
    logging.getLogger("werkzeug").setLevel(level)
    logging.getLogger("flask").setLevel(level)


def main() -> None:
    """Main entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()

    app.config["CACHE_DIR"] = args.cache
    configure_logging(args.log_level)
    setup_signal_handlers()

    try:
        run_app(args)
    except KeyboardInterrupt:
        from blinkapp import logger

        logger.info("Received keyboard interrupt")
    finally:
        cleanup_resources()


if __name__ == "__main__":
    main()
