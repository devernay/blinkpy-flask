#!/usr/bin/env python3
"""Main entry point for running blinkapp as a module."""

import argparse
import atexit
import logging
import signal
import sys
from typing import Any

# This module is an entry point and exports the app for testing
__all__: list[str] = ["app"]

from blinkapp import app
from blinkapp.models.responses import Config
from blinkapp.services.lifecycle_service import cleanup_resources, startup


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser for command line options.

    Returns:
        argparse.ArgumentParser: Configured argument parser with all CLI options.
    """
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
    """Set up signal handlers for graceful shutdown.

    Registers SIGINT and SIGTERM handlers for clean application shutdown,
    and ensures cleanup_resources is called on exit.
    """
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(cleanup_resources)


def run_app(args: argparse.Namespace) -> None:
    """Run the Flask application with given arguments.

    Args:
        args: Parsed command line arguments containing host, port, debug settings, etc.

    Side Effects:
        Starts Flask development server or dumps system info and exits.
    """
    if args.dump_system:
        from blinkapp.services.debug_service import handle_dump_system

        handle_dump_system()
        return

    if args.cache:
        app.config["CACHE_DIR"] = args.cache

    startup()

    # Display user-friendly startup message
    print("\n🏠 Blink Camera Web Interface")
    print(f"📱 Access your cameras at: http://{args.host}:{args.port}")
    if args.host == "0.0.0.0":
        print(f"   Or locally at: http://localhost:{args.port}")
    print("🔐 You will need to enter your Blink credentials on first visit\n")

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
    """Configure logging levels for all loggers.

    Args:
        log_level: Logging level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Side Effects:
        Sets logging level for root, blinkpy, werkzeug, and flask loggers.
    """
    level = getattr(
        logging, log_level
    )  # Dynamic access to logging level constants (DEBUG, INFO, etc.)
    logging.getLogger().setLevel(level)
    logging.getLogger("blinkpy").setLevel(level)
    logging.getLogger("werkzeug").setLevel(level)
    logging.getLogger("flask").setLevel(level)


def main() -> None:
    """Main entry point for the blinkapp module.

    Parses command line arguments, configures the application,
    sets up signal handlers, and starts the Flask server.
    """
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
