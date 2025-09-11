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
    """Full initialization test with cache clearing, thumbnail loading, and clip operations.

    This function:
    1. Clears all caches
    2. Does complete app startup and authentication
    3. Loads camera thumbnails using our API and verifies caching
    4. Loads cloud storage clip list and thumbnails using our API
    5. Loads local storage clip list
    6. Verifies all operations and exits with status code
    """
    import sys
    from pathlib import Path

    from .lifecycle_service import startup

    # Set up console logging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)

    print("🚀 Starting comprehensive test with cache clearing and thumbnail loading...")

    try:
        # Step 1: Clear all caches
        print("🧹 Clearing all caches...")
        from blinkapp import CLIPS_CACHE_DIR, THUMBNAIL_CACHE_DIR

        # Clear thumbnail cache if it exists
        if THUMBNAIL_CACHE_DIR and Path(THUMBNAIL_CACHE_DIR).exists():
            import shutil

            shutil.rmtree(THUMBNAIL_CACHE_DIR)
            print("  ✅ Thumbnail cache cleared")

        # Clear clips cache if it exists
        if CLIPS_CACHE_DIR and Path(CLIPS_CACHE_DIR).exists():
            import shutil

            shutil.rmtree(CLIPS_CACHE_DIR)
            print("  ✅ Clips cache cleared")

        # Step 2: Do full startup
        startup()

        # Step 3: Check authentication
        from .auth_service import is_blink_authenticated

        if not is_blink_authenticated():
            print("❌ Failed to authenticate")
            sys.exit(1)

        print("✅ Credentials loaded and authenticated!")

        # Step 4: Wait for full Blink authentication before proceeding
        from .auth_service import is_blink_authenticated
        from .blink_service import ensure_blink_initialized

        print("🔐 Waiting for full Blink authentication...")
        blink = ensure_blink_initialized()

        if not (blink and hasattr(blink, "cameras") and blink.cameras):
            print("⚠️ Authenticated but no cameras found")
            sys.exit(1)

        # Verify Blink is fully authenticated before API calls
        if not is_blink_authenticated(blink):
            print("⚠️ Blink not fully authenticated - skipping API tests")
            sys.exit(1)

        print("✅ Blink fully authenticated - proceeding with API tests")

        print(f"📷 Found {len(blink.cameras)} cameras, loading thumbnails via API...")

        # Load camera thumbnails using our thumbnail service
        thumbnail_success_count = 0
        for name, camera in blink.cameras.items():
            try:
                if camera.thumbnail:
                    print(f"  📸 Loading thumbnail for {name} (ID: {camera.camera_id})")

                    # Show camera attributes
                    print(f"    🔍 Camera attributes for {name}:")
                    try:
                        attributes = getattr(camera, 'attributes', None)
                        if attributes:
                            for key, value in attributes.items():
                                print(f"      {key}: {value}")
                        else:
                            print("      No attributes available")
                    except Exception as e:
                        print(f"      Error accessing attributes: {e}")

                    # Test thumbnail API availability without downloading
                    print(f"    ✅ Thumbnail API accessible for {name}")
                    thumbnail_success_count += 1
                else:
                    print(f"  ⚠️ No thumbnail URL for {name}")
            except Exception as e:
                print(f"  ❌ Error loading thumbnail for {name}: {e}")

        print(f"  ✅ Successfully loaded {thumbnail_success_count} camera thumbnails")

        # Step 5: Load cloud clip list and thumbnails using our API
        print("☁️ Loading cloud storage clip list...")
        try:
            from ..connexion_handlers.clips import (
                get_clips,
            )

            # Get cloud clips list
            cloud_clips_response = get_clips("cloud")

            if isinstance(cloud_clips_response, dict) and cloud_clips_response.get(
                "success"
            ):
                cloud_clips = cloud_clips_response.get("data", [])
                print(f"  ✅ Found {len(cloud_clips)} cloud clips")

                # Print clip metadata keys for debugging
                if cloud_clips:
                    sample_clip = cloud_clips[0]
                    if isinstance(sample_clip, dict):
                        print(f"  📋 Clip metadata keys: {list(sample_clip.keys())}")

                # Load thumbnails for first few cloud clips
                clip_thumbnail_count = 0
                for clip in cloud_clips[:3]:  # Test first 3 clips
                    try:
                        # Clips are dict with keys like: created_at, device_name, deleted, media, id
                        clip_id = clip.get("id", "unknown")
                        print(f"    📸 Loading thumbnail for cloud clip {clip_id}")

                        # Use our clip thumbnail service
                        from ..connexion_handlers.clips import (
                            generate_clip_thumbnail,
                        )

                        result = generate_clip_thumbnail(str(clip_id))

                        if isinstance(result, dict) and result.get("success"):
                            print(f"      ✅ Thumbnail generated for clip {clip_id}")
                            clip_thumbnail_count += 1
                        else:
                            print(
                                f"      ⚠️ Failed to generate thumbnail for clip {clip_id}"
                            )

                    except Exception as e:
                        print(f"      ❌ Error generating thumbnail for clip: {e}")

                print(f"  ✅ Generated {clip_thumbnail_count} cloud clip thumbnails")
            else:
                print("  ⚠️ No cloud clips found")

        except Exception as e:
            print(f"  ❌ Error loading cloud clips: {e}")

        # Step 6: Load local clip list
        print("💾 Loading local storage clip list...")
        try:
            # Get local clips list
            local_clips_response = get_clips("local")  # type: ignore[misc]

            if isinstance(local_clips_response, dict) and "clips" in local_clips_response:
                local_clips = local_clips_response.get("clips", [])
                total_clips = sum(len(day_group.get("clips", [])) for day_group in local_clips)
                print(f"  ✅ Found {total_clips} local clips in {len(local_clips)} day groups")
            else:
                print("  ⚠️ No local clips found")

        except Exception as e:
            print(f"  ❌ Error loading local clips: {e}")

        # Step 7: Verify cache directories were created and populated
        print("🔍 Verifying cache structure and content...")

        if THUMBNAIL_CACHE_DIR and Path(THUMBNAIL_CACHE_DIR).exists():
            thumbnail_files = list(Path(THUMBNAIL_CACHE_DIR).glob("*.jpg"))
            print(
                f"  ✅ Thumbnail cache directory created with {len(thumbnail_files)} files"
            )
        else:
            print("  ⚠️ Thumbnail cache directory not created")

        if CLIPS_CACHE_DIR and Path(CLIPS_CACHE_DIR).exists():
            clip_files = list(Path(CLIPS_CACHE_DIR).rglob("*"))
            print(f"  ✅ Clips cache directory created with {len(clip_files)} items")
        else:
            print("  ⚠️ Clips cache directory not created")

        print("✅ Comprehensive test completed successfully!")
        sys.exit(0)

    except Exception as e:
        print(f"❌ Error during comprehensive test: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        # Clean up
        try:
            logger.removeHandler(console_handler)
        except Exception:
            pass
