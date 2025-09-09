"""Debug service for Blink Camera Flask application.

This module provides debugging and diagnostic utilities for troubleshooting
Blink system connectivity, authentication, and data retrieval issues.

Key functions:
- System information dumping for diagnostics
- Credential file validation
- Cloud video enumeration
- Comprehensive logging of system state

Used primarily for:
- CLI debugging with --dump-system flag
- Troubleshooting authentication issues
- Verifying system connectivity and data access
"""

import collections.abc
import logging
from pathlib import Path

from .blink_service import ensure_blink_initialized

logger = logging.getLogger(__name__)

__all__ = [
    "dump_blink_system_info",
    "handle_dump_system",
    "check_credentials_file_exists",
    "dump_cloud_videos",
]


def dump_blink_system_info() -> None:
    """Dump comprehensive Blink system information for debugging.

    Outputs detailed system state including:
    - Account information and availability status
    - Network configurations and device counts
    - Camera details and capabilities
    - System homescreen data

    Used for troubleshooting connectivity and authentication issues.
    """
    import json

    from blinkapp import logger
    from blinkapp.services.blink_service import ensure_blink_initialized

    blink = ensure_blink_initialized()

    if not blink or not blink.available:
        logger.error("Blink system not available")
        return

    logger.info("=== BLINK SYSTEM DUMP ===")
    logger.info(f"Account ID: {blink.account_id}")
    logger.info(f"Available: {blink.available}")
    logger.info("Homescreen:")
    logger.info(json.dumps(blink.homescreen, indent=2))

    logger.info(f"=== SYNC MODULES ({len(blink.sync)}) ===")
    for sync_name, sync in blink.sync.items():
        logger.info(f"--- Sync Module: {sync_name} ---")
        logger.info(f"Status: {sync.status}")
        logger.info(f"Armed: {sync.arm}")

    logger.info(f"=== CAMERAS ({len(blink.cameras)}) ===")
    for camera_name, camera in blink.cameras.items():
        logger.info(f"--- Camera: {camera_name} ---")
        logger.info(f"Attributes: {camera.attributes}")

    logger.info("=== END DUMP ===")


def check_credentials_file_exists(credentials_path: Path) -> bool:
    """Check if credentials file exists."""
    return credentials_path.exists()


def dump_cloud_videos(videos: list[dict[str, object]]) -> None:
    """Dump cloud videos information."""
    logger.info("=== CLOUD VIDEOS ===")
    for video in videos:
        logger.info(f"Video: {video}")


def handle_dump_system(
    credentials_checker: collections.abc.Callable[[Path], bool] | None = None,
) -> None:
    """Handle dump-system command line option."""
    if credentials_checker is None:
        credentials_checker = check_credentials_file_exists

    import logging
    import sys

    from blinkapp import CREDENTIALS_FILE, Config, initialize_cache_paths, logger
    from blinkapp.services.blink_connection import blink_connection
    from blinkapp.services.blink_service import ensure_blink_connection_initialized
    from blinkapp.services.lifecycle_service import cleanup_blink_session

    initialize_cache_paths()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    assert CREDENTIALS_FILE is not None
    cred_file = Path(CREDENTIALS_FILE)
    if not credentials_checker(cred_file):
        logger.error("No saved credentials found.")
        sys.exit(1)

    assert blink_connection is not None
    blink_connection.start()
    blink = None
    try:
        blink = ensure_blink_initialized()
        if blink is not None:
            if blink.sync is not None:
                for _, sync in blink.sync.items():
                    if sync.local_storage:
                        assert blink_connection is not None
                        ensure_blink_connection_initialized().execute(
                            sync.update_local_storage_manifest()
                        )

            assert blink_connection is not None
            videos = ensure_blink_connection_initialized().execute(
                blink.get_videos_metadata(stop=Config.MAX_VIDEOS_METADATA)
            )

            dump_blink_system_info()
            dump_cloud_videos(videos)
            logger.info("System dump completed successfully.")
        else:
            logger.error("Failed to load Blink system from saved credentials.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"System dump error: {e}")
        sys.exit(1)
    finally:
        if blink is not None:
            assert blink_connection is not None
            ensure_blink_connection_initialized().execute(cleanup_blink_session())
        logger.removeHandler(console_handler)
        assert blink_connection is not None
        blink_connection.shutdown()
