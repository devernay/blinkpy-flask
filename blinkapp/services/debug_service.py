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
    "handle_test_credentials",
    "handle_test_and_exit",
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
    """Check if credentials file exists.

    Args:
        credentials_path: Path to the credentials file to check.

    Returns:
        bool: True if credentials file exists, False otherwise.
    """
    return credentials_path.exists()


def dump_cloud_videos(videos: list[dict[str, object]]) -> None:
    """Dump cloud videos information to logger.

    Args:
        videos: List of video dictionaries containing cloud video metadata.
    """
    logger.info("=== CLOUD VIDEOS ===")
    for video in videos:
        logger.info(f"Video: {video}")


def handle_dump_system(
    credentials_checker: collections.abc.Callable[[Path], bool] | None = None,
) -> None:
    """Handle dump-system command line option.

    Args:
        credentials_checker: Optional function to check credentials file existence.
    """
    if credentials_checker is None:
        credentials_checker = check_credentials_file_exists

    import logging
    import sys

    from blinkapp import CREDENTIALS_FILE, Config, logger
    from blinkapp.services.blink_connection import get_blink_connection
    from blinkapp.services.blink_service import (
        cleanup_blink_session,
        ensure_blink_connection_initialized,
    )
    from blinkapp.services.cache_service import initialize_cache_paths

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

    blink_connection = get_blink_connection()
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


def handle_test_credentials() -> None:
    """Test credential loading and exit.

    This function initializes the app, tests credential loading,
    and exits with appropriate status code.
    """
    import sys

    from ..config import Config

    # Set up console logging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(levelname)s - %(name)s - %(message)s")
    console_handler.setFormatter(formatter)

    # Add handler to root logger to catch all debug messages
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.DEBUG)

    print("🔍 Testing credential loading...")

    try:
        # Check if credentials file exists first
        from pathlib import Path

        cred_file = Path(Config.DEFAULT_CACHE_DIR) / Config.CREDENTIALS_FILENAME
        print(f"📁 Checking credentials file: {cred_file}")
        print(f"📁 File exists: {cred_file.exists()}")

        if cred_file.exists():
            print(f"📁 File size: {cred_file.stat().st_size} bytes")

        # Test loading credentials directly
        print("🔑 Testing direct credential loading...")
        from .auth_service import load_saved_blink
        from .blink_service import (
            ensure_blink_connection_initialized,
            initialize_blink_objects,
        )

        # Initialize blink service first
        initialize_blink_objects()
        blink_connection = ensure_blink_connection_initialized()
        blink_connection.start()

        # Try to load credentials
        success = blink_connection.execute(load_saved_blink())

        if success:
            print("✅ Credentials loaded successfully!")

            # Check authentication status
            from .auth_service import is_blink_authenticated

            if is_blink_authenticated():
                print("✅ Blink authentication confirmed!")
                sys.exit(0)
            else:
                print("⚠️ Credentials loaded but authentication check failed")
                sys.exit(1)
        else:
            print("❌ Failed to load credentials")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error during credential test: {e}")
        logger.error(f"Credential test error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        # Clean up
        try:
            from .blink_service import ensure_blink_connection_initialized

            blink_connection = ensure_blink_connection_initialized()
            root_logger.removeHandler(console_handler)
            blink_connection.shutdown()
        except Exception:
            pass


def handle_test_and_exit() -> None:
    """Full initialization test with camera list and exit.

    This function does complete app startup, tests credentials,
    retrieves camera list, and exits with status code.
    """
    import sys

    from .lifecycle_service import startup

    # Set up console logging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)

    print("🚀 Starting full initialization test...")

    try:
        # Do full startup (this includes credential loading)
        startup()

        # Check if credentials were loaded successfully
        from .auth_service import is_blink_authenticated

        if is_blink_authenticated():
            print("✅ Credentials loaded and authenticated!")

            # Try to get camera list
            try:
                from .blink_service import ensure_blink_initialized

                blink = ensure_blink_initialized()

                if blink and hasattr(blink, "cameras") and blink.cameras:
                    print(f"📷 Found {len(blink.cameras)} cameras:")
                    for name, camera in blink.cameras.items():
                        status = "🟢 Armed" if camera.arm else "🔴 Disarmed"
                        print(f"  - {name}: {status}")
                    print("✅ Full initialization successful!")
                    sys.exit(0)
                else:
                    print("⚠️ Authenticated but no cameras found")
                    sys.exit(1)

            except Exception as e:
                print(f"❌ Error retrieving cameras: {e}")
                sys.exit(1)
        else:
            print("❌ Failed to authenticate")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        sys.exit(1)
    finally:
        # Clean up
        try:
            from .blink_service import ensure_blink_connection_initialized

            blink_connection = ensure_blink_connection_initialized()
            logger.removeHandler(console_handler)
            blink_connection.shutdown()
        except Exception:
            pass
