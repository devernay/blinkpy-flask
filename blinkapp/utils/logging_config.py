"""
Logging configuration utilities for the Blink Camera Flask application.

This module provides centralized logging setup with rotating file handlers
and appropriate log levels for both development and production environments.
"""

import logging
import logging.handlers
from pathlib import Path

from blinkapp.config import Config

__all__ = [
    "setup_logging",
]


def setup_logging() -> None:
    """Configure logging with rotating file handler in cache directory.

    Sets up application logging with:
    - Rotating file handler to prevent log files from growing too large
    - Console handler for development debugging
    - Appropriate log levels and formatting
    - Error-specific log file for critical issues

    The logging configuration uses the cache directory for log file storage
    and implements rotation to manage disk space usage effectively.
    """
    # Ensure cache directory exists for log files
    cache_dir = Path("cache")  # Use default cache directory
    cache_dir.mkdir(exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Clear any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create formatters for different log types
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    simple_formatter = logging.Formatter("%(levelname)s: %(message)s")

    # File handler with rotation for main application logs
    log_file = cache_dir / "blink_app.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=Config.LOG_MAX_BYTES, backupCount=Config.LOG_BACKUP_COUNT
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    # Console handler for development and debugging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(
        logging.WARNING
    )  # Only show warnings and errors in console
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # Configure third-party library logging levels to reduce noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

    # Log successful configuration
    logger = logging.getLogger(__name__)
    logger.info("Logging configuration completed successfully")
