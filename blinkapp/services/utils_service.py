"""Utils service for Blink Camera Flask application.

This module handles utility functions and common operations
that are used across multiple parts of the application.
"""

from __future__ import annotations

__all__ = [
    "create_device_data",
    "dump_blink_system_info",
    "handle_dump_system",
]

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blinkpy.camera import BlinkCamera

    from blinkapp.models.ids import CameraId

logger = logging.getLogger(__name__)


def create_device_data(
    camera: BlinkCamera, cache_key: CameraId, current_ts: int, cached_ts: int
) -> dict[str, object]:
    """Create device data dictionary for camera.

    Builds a standardized device object for API responses, including
    camera status, thumbnail information, and human-readable timestamps.
    This function handles the complex logic of determining the most
    recent thumbnail timestamp and formatting it for display.

    Args:
        camera: Camera object from blinkpy library with device properties
        cache_key: Validated camera ID for API endpoints
        current_ts: Current thumbnail timestamp from Blink API
        cached_ts: Cached thumbnail timestamp from local storage

    Returns:
        Device data dictionary for API response with standardized fields:
        - type: Always "camera"
        - name: Camera display name
        - id: Camera ID for API calls
        - thumbnail: Thumbnail endpoint URL
        - last_updated: Human-readable time since last update
        - motion_enabled: Boolean motion detection status
        - battery: Battery level (if available)
        - temperature: Temperature reading (if available)
        - wifi_strength: WiFi signal strength (if available)

    Example:
        >>> device = create_device_data(
        ...     camera, CameraId("12345"), 1609459200, 1609459100
        ... )
        >>> device["last_updated"]
        "5m ago"
    """
    from datetime import datetime

    from blinkapp import logger
    from blinkapp.utils.validators import format_time_ago

    # Use the most recent timestamp between current and cached
    # This ensures we show the latest available thumbnail information
    display_ts = max(cached_ts, current_ts)
    last_updated = "Never"

    if display_ts > 0:
        try:
            # Calculate human-readable time difference
            thumbnail_time = datetime.fromtimestamp(display_ts)
            now = datetime.now()
            diff = now - thumbnail_time
            days = diff.days

            # Format time difference in most appropriate unit
            if days == 0:
                hours = diff.seconds // 3600
                if hours == 0:
                    minutes = diff.seconds // 60
                    last_updated = f"{minutes}m ago"
                else:
                    last_updated = f"{hours}h ago"
            else:
                last_updated = f"{days}d ago"
        except (ValueError, TypeError, AttributeError) as e:
            # Fallback to camera's last record time if timestamp calculation fails
            logger.debug(
                f"Failed to calculate time difference for camera {camera.name}: {e}"
            )
            if camera.last_record:
                # Extract timestamp from last_record dict (common keys: 'created_at', 'updated_at', 'time')
                timestamp = (
                    camera.last_record.get("created_at")
                    or camera.last_record.get("updated_at")
                    or camera.last_record.get("time")
                )
                last_updated = format_time_ago(timestamp) if timestamp else "Never"
            else:
                last_updated = "Never"

    # Return standardized device object for consistent API responses
    return {
        "type": "camera",
        "name": camera.name,
        "id": camera.camera_id,
        "thumbnail": f"/api/camera/{camera.camera_id}/thumbnail",
        "last_updated": last_updated,
        "motion_enabled": camera.motion_enabled,
        "battery": camera.battery,
        "temperature": camera.temperature,
        "wifi_strength": camera.wifi_strength,
    }


def dump_blink_system_info() -> None:
    """Dump comprehensive Blink system information."""
    import json

    from blinkapp import logger
    from blinkapp.services.blink_service import blink

    if not blink or not blink.available:
        logger.error("Blink system not available")
        return

    logger.info("=== BLINK SYSTEM DUMP ===")

    # Basic system info
    logger.info(f"Account ID: {blink.account_id}")
    logger.info(f"Client ID: {blink.client_id}")
    logger.info(f"Available: {blink.available}")
    logger.info(f"Auth data: {blink.auth.data}")
    logger.info(f"Last refresh: {blink.last_refresh}")
    logger.info(f"Refresh rate: {blink.refresh_rate}")
    logger.info(f"Motion interval: {blink.motion_interval}")
    logger.info(f"Key required: {blink.key_required}")
    logger.info(f"Network IDs: {blink.network_ids}")
    logger.info(f"Networks: {blink.networks}")
    logger.info(f"Version: {blink.version}")
    logger.info("Homescreen:")

    logger.info(json.dumps(blink.homescreen, indent=2))

    # Sync modules
    logger.info(f"=== SYNC MODULES ({len(blink.sync)}) ===")
    for sync_name, sync in blink.sync.items():
        logger.info(f"--- Sync Module: {sync_name} ---")
        logger.info(f"Attributes: {sync.attributes}")
        logger.info(f"Network Info: {sync.network_info}")
        logger.info(f"Summary: {sync.summary}")
        logger.info(f"Status: {sync.status}")
        logger.info(f"Online: {sync.online}")
        logger.info(f"Armed: {sync.arm}")
        logger.info(f"Cameras: {list(sync.cameras.keys())}")

        # Local storage info
        logger.info(f"Local storage enabled: {sync._local_storage['enabled']}")
        logger.info(f"Local storage compatible: {sync._local_storage['compatible']}")
        logger.info(f"Local storage status: {sync._local_storage['status']}")
        logger.info(
            f"Local storage manifest ready: {sync.local_storage_manifest_ready}"
        )

        if sync.local_storage and sync.local_storage_manifest_ready:
            manifest = sync._local_storage.get("manifest", [])
            logger.info(f"Local storage clips ({len(manifest)}):")
            for item in manifest:
                logger.info(
                    f"  - ID: {item.id}, Camera: {item.name}, Created: {item.created_at}, Size: {item.size}"
                )

    # All cameras
    logger.info(f"=== CAMERAS ({len(blink.cameras)}) ===")
    for camera_name, camera in blink.cameras.items():
        from blinkpy.camera import BlinkCamera

        if isinstance(camera, BlinkCamera):
            logger.info(f"--- Camera: {camera_name} ---")
            logger.info(f"Attributes: {camera.attributes}")

    logger.info("=== CLOUD VIDEOS (see separate dump) ===")

    logger.info("=== END DUMP ===")


def handle_dump_system() -> None:
    """Handle dump-system command line option."""
    import logging
    import sys
    from pathlib import Path

    from blinkapp import (
        CREDENTIALS_FILE,
        Config,
        cleanup_blink_session,
        dump_cloud_videos,
        initialize_cache_paths,
        logger,
    )
    from blinkapp.services.auth_service import load_saved_blink
    from blinkapp.services.blink_service import blink
    from blinkapp.services.connection_service import blink_connection

    initialize_cache_paths()

    # Add console handler for CLI output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    assert CREDENTIALS_FILE is not None
    cred_file = Path(CREDENTIALS_FILE)
    if not cred_file.exists():
        logger.error("No saved credentials found.")
        logger.error("Please start the server and login first to save credentials.")
        sys.exit(1)

    assert blink_connection is not None
    blink_connection.start()
    try:
        success = blink_connection.execute(load_saved_blink())
        if success:
            # Update local storage manifests first
            assert blink is not None
            for _, sync in blink.sync.items():
                if sync.local_storage:
                    assert blink_connection is not None
                    blink_connection.execute(sync.update_local_storage_manifest())

            # Get cloud videos in blink thread
            assert blink is not None
            assert blink_connection is not None
            videos = blink_connection.execute(
                blink.get_videos_metadata(stop=Config.MAX_VIDEOS_METADATA)
            )

            # Dump system info (non-async)
            dump_blink_system_info()

            # Dump cloud videos
            dump_cloud_videos(videos)

            logger.info("System dump completed successfully.")
        else:
            logger.error("Failed to load Blink system from saved credentials.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"System dump error: {e}")
        sys.exit(1)
    finally:
        # Clean up Blink session and shutdown connection
        if blink is not None:
            assert blink_connection is not None
            blink_connection.execute(cleanup_blink_session())

        # Remove console handler
        logger.removeHandler(console_handler)
        assert blink_connection is not None
        blink_connection.shutdown()
