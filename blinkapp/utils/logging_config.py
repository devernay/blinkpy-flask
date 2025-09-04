"""
Logging configuration utilities for the Blink Camera Flask application.

This module provides centralized logging setup with rotating file handlers
and appropriate log levels for both development and production environments.
"""

import logging
import logging.handlers
from pathlib import Path

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
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)

    # Create formatters for different log types
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    simple_formatter = logging.Formatter("%(levelname)s: %(message)s")

    # File handler with rotation at each app launch
    log_file = cache_dir / "blink_app.log"

    # Rotate existing log file if it exists and has content
    if log_file.exists() and log_file.stat().st_size > 0:
        import time

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        rotated_file = cache_dir / f"blink_app.log.{timestamp}"
        log_file.rename(rotated_file)

        # Clean up old rotated files, keep only the most recent 9 (plus current = 10 total)
        rotated_files = sorted(
            cache_dir.glob("blink_app.log.*"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        for old_file in rotated_files[9:]:  # Keep 9 rotated + 1 current = 10 total
            old_file.unlink()

    file_handler = logging.FileHandler(log_file)
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
