#!/usr/bin/env python3
"""
Blink Camera Flask Web Interface

A comprehensive web application for managing Blink camera systems with features including:
- Multi-system support with real-time camera thumbnails
- Live streaming via TCP to HLS transcoding using Blink's init_livestream()
- Cloud and local clip management with thumbnail generation
- User settings (temperature units, clip retention, thumbnail sizes)
- Mobile-optimized responsive interface
- Background processing for clip downloads and thumbnail generation

Main components:
- Flask web server with RESTful API
- Async Blink connection management
- HLS stream manager for live video from TCP streams
- Intelligent caching with configurable retention
- Thread-safe operations with proper cleanup

Author: Fredderic Devernay
License: MIT
"""

import argparse
import asyncio
import atexit
import logging
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    ParamSpec,
    TypeVar,
    cast,
)

# Authentication and session management
from auth import (
    load_saved_blink,
    setup_auth_routes,
)

# Caching system for thumbnails, clips, and metadata
from cache import (
    clips_download_cache,
    clips_metadata_cache,
    thumbnail_cache,
)

# Camera operations and route handlers
from camera import (
    find_camera_by_id,
    require_camera,
    setup_camera_routes,
    update_camera_thumbnail,
)

# Route decorators and error handling
from decorators import error_context, requires_blink
from errors import (
    CacheError,
    ValidationError,
)

# ID validation and type safety
from ids import CameraId, ClipId, NetworkId

# Route decorators for API endpoints
from route_decorators import (
    api_route,
    api_route_with_validation,
    cached_api_route,
    file_response_route,
    method_dispatch_route,
    simple_success_response,
)

# Live streaming management
from stream_manager import StreamConfig, StreamManager

# Utility functions for data processing
from utils import (
    create_api_response,
    format_clips_by_day,
    format_time_ago,
    parse_clip_id,
)

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from blink_connection import BlinkConnection

# Third-party imports
import requests

# Flask framework components
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask import Response as FlaskResponse
from flask.typing import ResponseReturnValue

# Blink camera library
from blinkpy.blinkpy import Blink  # type: ignore
from blinkpy.camera import BlinkCamera
from blinkpy.sync_module import BlinkSyncModule

# Application configuration
from config import Config

# Type definitions for better code clarity
JsonDict = dict[str, object]
ApiResponse = tuple[JsonDict, int]
FlaskRouteResponse = ResponseReturnValue
CacheKey = str
SettingsDict = dict[str, str | int | bool]
DeviceDict = dict[str, object]
ClipDict = dict[str, object]
SystemDict = dict[str, object]

# Generic type variables for function signatures
T = TypeVar("T")
P = ParamSpec("P")

# ============================================================================
# Flask Application Setup
# ============================================================================

# Create Flask app instance with secure configuration
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-change-in-production")

# ============================================================================
# Global Application State
# ============================================================================

# Core Blink integration objects
blink: "Blink | None" = None  # Main Blink API client
blink_connection: "BlinkConnection | None" = None  # Async connection manager
executor: "ThreadPoolExecutor | None" = None  # Background task executor
http_session: "requests.Session | None" = None  # HTTP session for API calls
stream_manager: "StreamManager | None" = None  # Live streaming manager

# File system paths (initialized at startup)
CACHE_DIR: str | None = None  # Base cache directory
CREDENTIALS_FILE: str | None = None  # Encrypted credentials storage
THUMBNAIL_CACHE_DIR: str | None = None  # Camera thumbnail cache
CLIPS_CACHE_DIR: str | None = None  # Downloaded clips storage
SETTINGS_FILE: str | None = None  # User settings persistence

# ============================================================================
# Error Handling and API Response Utilities
# ============================================================================


def handle_api_error(
    error: Exception,
    operation: str,
    status_code: int = Config.HTTP_STATUS_INTERNAL_ERROR,
) -> tuple[ApiResponse, int]:
    """Handle API errors with user-friendly messages.

    Provides centralized error handling for all API endpoints with consistent
    error response format and appropriate HTTP status codes. This function
    translates technical exceptions into user-friendly messages while
    preserving the original error information in logs.

    Args:
        error: Exception that occurred during operation
        operation: Human-readable description of the failed operation
        status_code: HTTP status code to return (default: 500)

    Returns:
        Standardized error response tuple (response_dict, status_code)

    Example:
        >>> try:
        ...     # Some operation that might fail
        ...     pass
        ... except Exception as e:
        ...     return handle_api_error(e, "updating camera settings")
    """
    # Log the full technical error for debugging
    logger.error(f"Error {operation}: {error}")

    # Handle ValidationError with custom status code - these have specific
    # status codes that should be preserved (e.g., 400 for bad input)
    if isinstance(error, ValidationError):
        return create_api_response(
            success=False, error=str(error), status_code=error.status_code
        )

    # Map common exceptions to user-friendly messages that don't expose
    # internal implementation details to end users
    error_message = str(error)
    if isinstance(error, ConnectionError):
        error_message = "Unable to connect to your Blink system. Please check your internet connection and try again."
    elif isinstance(error, TimeoutError):
        error_message = "The request timed out. Please try again in a moment."
    elif isinstance(error, ValueError):
        error_message = "Invalid data provided. Please check your input and try again."
    elif "authentication" in str(error).lower() or "login" in str(error).lower():
        # Use predefined auth error message for consistency
        error_message = Config.ErrorMessages.AUTH_FAILED
    elif "not found" in str(error).lower():
        error_message = "The requested item could not be found."
    elif status_code >= 500:
        # For server errors, use generic message to avoid exposing internals
        error_message = Config.ErrorMessages.INTERNAL_ERROR

    return create_api_response(
        success=False, error=error_message, status_code=status_code
    )


# require_camera function moved to camera.py


def require_sync_module(
    network_id: NetworkId,
) -> tuple[BlinkSyncModule | None, tuple[ApiResponse, int] | None]:
    """Find sync module by network ID, return error response if not found.

    Searches through all available Blink sync modules to find one matching
    the provided network ID. This is used by API endpoints that need to
    operate on specific Blink systems.

    Args:
        network_id: Network ID to find (validated NetworkId instance)

    Returns:
        Tuple of (sync_module, error_response). Exactly one will be None:
        - If found: (BlinkSyncModule, None)
        - If not found: (None, error_response_tuple)

    Example:
        >>> sync, error = require_sync_module(NetworkId("12345"))
        >>> if error:
        ...     return error  # Return error response to client
        >>> # Use sync module for operations
        >>> sync.arm = True
    """
    # Ensure blink is initialized - this should be guaranteed by @requires_blink
    assert blink is not None

    # Search through all sync modules for matching network ID
    for name, sync in blink.sync.items():
        if str(sync.network_id) == str(network_id):
            return sync, None

    # Network ID not found - return standardized error response
    error_response = create_api_response(
        success=False, error=Config.ErrorMessages.SYSTEM_NOT_FOUND, status_code=404
    )
    return None, error_response


# Configure logging - will be reconfigured after cache paths are set
logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure logging with rotating file handler in cache directory.

    Sets up both console and file logging with consistent formatting.
    File logs are rotated to prevent disk space issues. This function
    must be called after cache paths are initialized via initialize_cache_paths().

    The logging configuration includes:
    - Console handler for immediate feedback during development
    - Rotating file handler for persistent logs with size limits
    - Consistent timestamp formatting across all handlers
    - Automatic log rotation on startup to ensure fresh logs

    Side Effects:
        - Clears existing handlers to prevent duplicates
        - Creates log file in cache directory
        - Configures root logger level and handlers
    """
    # Clear any existing handlers to avoid duplicates on app restart
    logger.handlers.clear()
    logging.getLogger().handlers.clear()

    # Create consistent formatter for all handlers with timestamp and level
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler for immediate feedback during development/debugging
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Rotating file handler in cache directory for persistent logs
    from logging.handlers import RotatingFileHandler

    # Ensure cache directory is initialized before creating log file
    assert CACHE_DIR is not None, (
        "Cache directory must be initialized before logging setup"
    )
    log_file_path = Path(CACHE_DIR) / Config.LOG_FILE

    # Configure file rotation to prevent disk space issues
    # maxBytes: Maximum size before rotation, backupCount: Number of old logs to keep
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=Config.LOG_MAX_BYTES,
        backupCount=Config.LOG_BACKUP_COUNT,
    )
    file_handler.setFormatter(formatter)

    # Configure root logger with both handlers for comprehensive logging
    root_logger = logging.getLogger()
    root_logger.setLevel(
        logging.INFO
    )  # Default level, will be overridden by command line arguments
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Force rotation on startup to ensure we start with a fresh log
    file_handler.doRollover()


# ============================================================================
# Cache and File System Management
# ============================================================================


def initialize_cache_paths() -> None:
    """Initialize cache directory paths from Flask config or defaults.

    Sets global path variables for cache directories and credential file.
    Uses Flask app config 'CACHE_DIR' or defaults to Config.DEFAULT_CACHE_DIR.
    This function must be called before any cache operations or logging setup.

    The cache directory structure created:
    - CACHE_DIR/: Base cache directory
    - CACHE_DIR/thumbnails/: Camera thumbnail cache
    - CACHE_DIR/clips/: Downloaded clips storage
    - CACHE_DIR/blink.json: Encrypted credentials
    - CACHE_DIR/settings.json: User preferences
    - CACHE_DIR/blink_app.log: Application logs

    Side Effects:
        Updates global variables: CACHE_DIR, CREDENTIALS_FILE,
        THUMBNAIL_CACHE_DIR, CLIPS_CACHE_DIR, SETTINGS_FILE

    Raises:
        OSError: If cache directory cannot be created or accessed
    """
    global \
        CACHE_DIR, \
        CREDENTIALS_FILE, \
        THUMBNAIL_CACHE_DIR, \
        CLIPS_CACHE_DIR, \
        SETTINGS_FILE

    # Get cache directory from Flask config or use sensible default
    cache_dir = Path(app.config.get("CACHE_DIR", Config.DEFAULT_CACHE_DIR))

    # Set all cache-related paths using the base cache directory
    CACHE_DIR = str(cache_dir)
    CREDENTIALS_FILE = str(cache_dir / Config.CREDENTIALS_FILENAME)
    THUMBNAIL_CACHE_DIR = str(cache_dir / Config.THUMBNAILS_SUBDIR)
    CLIPS_CACHE_DIR = str(cache_dir / Config.CLIPS_SUBDIR)
    SETTINGS_FILE = str(cache_dir / Config.SETTINGS_FILENAME)


# Cache configuration constants
CLIPS_CACHE_SIZE = Config.CLIPS_CACHE_SIZE  # Maximum number of clips to cache

# ============================================================================
# Utility Functions
# ============================================================================


def extract_thumbnail_timestamp(thumbnail_url: str | None) -> int:
    """Extract timestamp from thumbnail URL.

    Parses the 'ts' parameter from Blink thumbnail URLs to determine
    when the thumbnail was generated. This timestamp is used for
    cache invalidation and thumbnail freshness checks.

    The Blink API includes timestamps in thumbnail URLs like:
    "https://immedia-semi.s3.amazonaws.com/production/...?ts=1234567890"

    Args:
        thumbnail_url: URL containing ts parameter (e.g., "...?ts=1234567890")

    Returns:
        Timestamp as integer (Unix epoch), 0 if not found or invalid

    Example:
        >>> extract_thumbnail_timestamp("https://example.com/thumb.jpg?ts=1609459200")
        1609459200
        >>> extract_thumbnail_timestamp("https://example.com/thumb.jpg")
        0
    """
    if not thumbnail_url:
        return 0
    try:
        import re

        # Extract numeric timestamp from URL query parameter using regex
        # Pattern matches 'ts=' followed by one or more digits
        match = re.search(r"ts=([0-9]+)", thumbnail_url)
        return int(match.group(1)) if match else 0
    except (AttributeError, ValueError, TypeError) as e:
        # Log debug info for troubleshooting but don't fail the operation
        logger.debug(f"Failed to extract timestamp from URL '{thumbnail_url}': {e}")
        return 0


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
        >>> device = create_device_data(camera, CameraId("12345"), 1609459200, 1609459100)
        >>> device["last_updated"]
        "5m ago"
    """
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
            last_updated = (
                format_time_ago(camera.last_record) if camera.last_record else "Never"
            )

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


# update_camera_thumbnail function moved to camera.py


def process_cloud_clips(
    videos_metadata: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Process cloud storage clips into day-grouped format.

    Takes raw video metadata from the Blink API and organizes it into
    day-based groups for easier browsing in the web interface. This function
    handles thumbnail caching, timestamp parsing, and creates a standardized
    format for both cloud and local clips.

    The function prioritizes local thumbnails over Blink's CDN thumbnails
    when available, as local thumbnails are faster to load and don't count
    against API rate limits.

    Args:
        videos_metadata: Raw video metadata from Blink API, each containing:
            - id: Unique clip identifier
            - created_at: ISO timestamp string
            - device_name: Camera name
            - thumbnail: CDN thumbnail URL
            - media: Video file URL

    Returns:
        List of day groups with clips sorted by date, each containing:
        - date: Human-readable date string
        - clips: List of clip objects with standardized fields

    Example:
        >>> metadata = [{"id": "123", "created_at": "2023-01-01T12:00:00Z", ...}]
        >>> result = process_cloud_clips(metadata)
        >>> result[0]["date"]
        "January 01, 2023"
    """
    clips_by_day: dict[str, dict[str, object]] = {}

    for video in videos_metadata:
        try:
            # Parse ISO timestamp from Blink API (handles Z timezone suffix)
            created_at = datetime.fromisoformat(
                video["created_at"].replace("Z", "+00:00")
            )
            day_key = created_at.strftime("%Y-%m-%d")

            # Create day group if it doesn't exist
            if day_key not in clips_by_day:
                clips_by_day[day_key] = {
                    "date": created_at.strftime("%B %d, %Y"),
                    "clips": [],
                }

            clip_id = ClipId(str(video.get("id")))
            thumbnail_url = video.get("thumbnail")

            # Check if we have a cached thumbnail for cloud clips
            # This avoids using Blink's CDN thumbnail if we have a local one
            # which is faster and doesn't count against API limits
            cached_clip = clips_download_cache.get(clip_id)
            if cached_clip is not None:
                cached_thumbnail = cached_clip.get("thumbnail")
                if cached_thumbnail and cached_thumbnail.exists():
                    # Use our local thumbnail endpoint instead of Blink's CDN
                    thumbnail_url = f"/api/clip/{clip_id}/thumbnail"

            # Build standardized clip object for UI consumption
            clips_by_day[day_key]["clips"].append(
                {
                    "id": str(clip_id),
                    "camera_name": video.get("device_name", "Unknown"),
                    "system_name": Config.DEFAULT_SYSTEM_NAME,
                    "time": created_at.astimezone().strftime("%I:%M %p"),
                    "event_type": "Motion",  # Cloud clips are always motion events
                    "thumbnail": thumbnail_url,
                    "media_url": video.get("media"),
                }
            )
        except Exception as e:
            # Skip malformed video entries but continue processing others
            # This ensures one bad clip doesn't break the entire list
            logger.warning(f"Skipping invalid video metadata: {e}")
            continue

    return format_clips_by_day(clips_by_day)


def process_local_clips() -> list[dict[str, object]]:
    """Process local storage clips into day-grouped format.

    Retrieves clips from USB storage connected to Blink sync modules.
    Local clips require the sync module to have local storage enabled
    and the manifest to be ready. Each clip gets a composite ID that
    includes the sync module name for proper identification.

    Returns:
        List of day groups with clips sorted by date, or empty list if
        no local storage is available or manifest isn't ready
    """
    clips_by_day: dict[str, dict[str, object]] = {}

    assert blink is not None
    for sync_name, sync_module in blink.sync.items():
        try:
            # Refresh sync module to update local storage manifest
            # This ensures we have the latest clip information
            blink_connection.execute(sync_module.refresh())

            # Get clips from local storage manifest if ready
            if sync_module.local_storage and sync_module.local_storage_manifest_ready:
                manifest = sync_module._local_storage["manifest"]
                for item in manifest:
                    try:
                        created_at = item.created_at
                        day_key = created_at.strftime("%Y-%m-%d")

                        # Create day group if it doesn't exist
                        if day_key not in clips_by_day:
                            clips_by_day[day_key] = {
                                "date": created_at.strftime("%B %d, %Y"),
                                "clips": [],
                            }

                        # Create composite clip ID for local clips (sync_name:item_id)
                        clip_id = ClipId.from_local(sync_name, item.id)
                        logger.debug(
                            f"Created local clip ID: {clip_id} from sync: {sync_name}, item: {item.id}"
                        )

                        # Check for existing thumbnail only (no auto-generation for local)
                        thumbnail_url = None
                        cached_clip = clips_download_cache.get(clip_id)
                        if cached_clip is not None:
                            cached_thumbnail = cached_clip.get("thumbnail")
                            if cached_thumbnail and cached_thumbnail.exists():
                                thumbnail_url = f"/api/clip/{clip_id}/thumbnail"

                        # Build standardized clip object for UI
                        clips_by_day[day_key]["clips"].append(
                            {
                                "id": str(clip_id),
                                "camera_name": item.name,
                                "system_name": sync_name,
                                "time": created_at.astimezone().strftime("%I:%M %p"),
                                "event_type": "Motion",
                                "thumbnail": thumbnail_url,
                                "media_url": item.url(
                                    sync_module._local_storage["last_manifest_id"]
                                ),
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Skipping invalid local clip metadata: {e}")
                        continue
        except Exception as e:
            logger.warning(f"Could not get local storage manifest for {sync_name}: {e}")
            continue

    return format_clips_by_day(clips_by_day)


@app.route("/")
def index() -> ResponseReturnValue:
    """Main page - redirect to login if not authenticated.

    Returns:
        Redirect to login page or rendered index template
    """
    if "authenticated" not in session:
        # Check if Blink is available from saved credentials
        if blink and blink.available:
            session["authenticated"] = True
            return render_template("index.html")
        else:
            return redirect(url_for("login"))
    # Clear initializing flag if set
    session.pop("initializing", None)
    return render_template("index.html")


def clear_all_caches() -> dict[str, object]:
    """Clear all caches except credentials (background operation)."""
    with error_context("clear cache", CacheError):
        # Clear memory caches first (fast operation) using OO cache methods
        thumbnail_cache.clear_cache()
        clips_download_cache.clear_cache()
        clips_metadata_cache.clear_cache()

        # Clear file caches (slow I/O operations)
        def clear_file_cache(cache_dir: str, cache_name: str) -> None:
            try:
                if os.path.exists(cache_dir):
                    import shutil

                    shutil.rmtree(cache_dir)
                    os.makedirs(cache_dir, exist_ok=True)
                    logger.debug(f"Cleared {cache_name} directory")
            except OSError as e:
                logger.warning(f"Could not clear {cache_name} directory: {e}")

        # Execute file operations in parallel
        assert THUMBNAIL_CACHE_DIR is not None
        thumbnail_future = executor.submit(
            clear_file_cache, THUMBNAIL_CACHE_DIR, "thumbnail"
        )
        assert CLIPS_CACHE_DIR is not None
        clips_future = executor.submit(clear_file_cache, CLIPS_CACHE_DIR, "clips")

        # Wait for completion with timeout
        try:
            thumbnail_future.result(timeout=Config.CACHE_CLEAR_TIMEOUT)
            clips_future.result(timeout=Config.CACHE_CLEAR_TIMEOUT)
            logger.info("All caches cleared successfully")
            return {"status": "success", "message": "All caches cleared successfully"}
        except Exception as e:
            logger.warning(f"Cache clearing completed with errors: {e}")
            return {
                "status": "warning",
                "message": f"Cache clearing completed with errors: {e}",
            }


@app.route("/api/clear-cache", methods=["POST"])
@simple_success_response("Cache clearing initiated")
def clear_cache() -> JsonDict:
    """Clear all caches except credentials.

    Returns:
        JSON response with success status
    """
    # Submit cache clearing task to background executor
    executor.submit(clear_all_caches)


# ============================================================================
# API Routes - System Management
# ============================================================================


@app.route("/api/system/list")
@requires_blink
@api_route("get systems")
def get_systems() -> JsonDict:
    """Get list of available Blink systems.

    Retrieves all configured Blink sync modules and their associated
    network information. Each system represents a separate Blink hub
    with its own set of cameras.

    Returns:
        JSON response with list of systems or error message
    """
    assert blink is not None  # Guaranteed by @requires_blink decorator

    logger.debug(f"Getting systems - sync count: {len(blink.sync)}")
    systems = []
    for name, sync in blink.sync.items():
        logger.debug(f"Processing sync: {name}, network_id: {sync.network_id}")
        systems.append(
            {
                "name": name,
                "network_id": sync.network_id,
                "armed": sync.arm,
                "online": sync.online,
            }
        )

    return {"systems": systems}


@app.route("/api/system/<network_id_str>/devices")
@requires_blink
@api_route_with_validation("get devices", validate_params={"network_id_str": NetworkId})
def get_devices(network_id: NetworkId) -> JsonDict:
    """Get devices for a specific Blink system.

    Args:
        network_id: Validated NetworkId object (converted from network_id_str by decorator)

    Returns:
        JSON response with list of devices or error message
    """
    # network_id is now validated and converted by the decorator
    devices = []

    # Find the sync module for this network
    sync_module, error_response = require_sync_module(network_id)
    if error_response is not None:
        raise ValidationError(error_response[0]["error"], error_response[1])

    assert sync_module is not None
    # Add sync module
    devices.append(
        {
            "type": "sync_module",
            "name": "Sync Module",
            "online": sync_module.online,
            "id": sync_module.sync_id,
        }
    )

    # Add cameras - refresh thumbnails in Blink thread
    for camera_name, camera in sync_module.cameras.items():
        logger.debug(
            f"Processing camera: {camera.name}, current thumbnail: {camera.thumbnail}"
        )

        cache_key = CameraId(camera.camera_id)
        current_ts = extract_thumbnail_timestamp(camera.thumbnail)
        cached_entry = thumbnail_cache.get(cache_key)
        cached_ts = cached_entry.get("timestamp", 0) if cached_entry else 0

        # Update thumbnail if needed
        update_camera_thumbnail(camera, cache_key, current_ts, cached_ts)

        # Create device data
        device_data = create_device_data(camera, cache_key, current_ts, cached_ts)
        logger.debug(f"Camera device data for {camera.name}: {device_data}")
        devices.append(device_data)

    return {"devices": devices}


@app.route("/api/system/<network_id_str>/arm", methods=["POST"])
@requires_blink
@api_route_with_validation(
    "arm/disarm system",
    validate_params={"network_id_str": NetworkId},
    validate_json=True,
    required_fields=["armed"],
)
def arm_system(network_id: NetworkId) -> JsonDict:
    """Arm or disarm a Blink system.

    Args:
        network_id: Validated NetworkId object (converted from network_id_str by decorator)

    Returns:
        JSON response with success status or error message
    """
    # network_id and armed are now validated and converted by the decorator
    data = request.get_json()
    armed = data["armed"]

    # Find the sync module
    sync_module, error_response = require_sync_module(network_id)
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code

    with error_context("arm/disarm system"):
        if sync_module is not None:
            blink_connection.execute(sync_module.async_arm(armed))
        return {"armed": armed}


# ============================================================================
# API Routes - Clip Management
# ============================================================================


@app.route("/api/clips")
@requires_blink
@cached_api_route(
    "get clips",
    cache_dict=clips_metadata_cache,
    cache_key_func=lambda: request.args.get("storage", "cloud"),
)
def get_clips() -> JsonDict:
    """Get clips from cloud or local storage.

    Retrieves video clips from either Blink's cloud storage or local
    USB storage connected to sync modules. Results are cached and
    organized by date for efficient browsing.

    Query Parameters:
        storage: 'cloud' or 'local' (default: 'cloud')

    Returns:
        JSON response with list of clips organized by date
    """
    assert blink is not None
    storage_type = request.args.get("storage", "cloud")
    if storage_type not in ["cloud", "local"]:
        raise ValidationError(Config.ErrorMessages.INVALID_STORAGE_TYPE, 400)

    with error_context(f"get {storage_type} clips"):
        if storage_type == "cloud":
            # Get cloud clips via blink operation
            videos_metadata = blink_connection.execute(
                blink.get_videos_metadata(stop=Config.CLIPS_PER_STORAGE_TYPE)
            )
            clips = process_cloud_clips(videos_metadata)
        else:
            clips = process_local_clips()

    return {"clips": clips}


@app.route("/api/system/refresh", methods=["POST"])
@requires_blink
@simple_success_response("System refreshed successfully")
def refresh_system() -> JsonDict:
    """Manually refresh the Blink system.

    Returns:
        JSON response with success status or error message
    """
    assert blink is not None
    success = blink_connection.execute(blink.refresh(force=True))

    if success is not True:
        response, status_code = create_api_response(
            success=False,
            error=Config.ErrorMessages.SYSTEM_REFRESH_FAILED,
            status_code=500,
        )
        return jsonify(response), status_code


@app.route("/api/clip/<clip_id_str>/process", methods=["POST"])
@requires_blink
@simple_success_response("Clip processing initiated")
def process_clip(clip_id_str: str) -> JsonDict:
    """Process clip on server (download and generate thumbnail) without sending to client.

    Initiates background processing of clip for thumbnail generation.
    Used by "Update All" functionality to process clips sequentially.

    Args:
        clip_id_str: String representation of clip ID (cloud ID or local sync~item format)

    Returns:
        JSON response indicating processing has started
    """
    clip_id, error_response = parse_clip_id(clip_id_str)
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code

    assert clip_id is not None
    if clip_id.is_local():
        sync_name, item_id = clip_id.get_local_parts()
        process_local_clip_background(clip_id, sync_name, item_id)
    else:
        process_cloud_clip_background(clip_id)


@app.route("/api/clip/<clip_id_str>/download")
@requires_blink
@api_route("download clip")
def download_clip(clip_id_str: str) -> FlaskResponse:
    """Download a specific clip.

    Args:
        clip_id_str: String representation of clip ID

    Returns:
        Flask Response with clip file or error message
    """
    clip_id, error_response = parse_clip_id(clip_id_str)
    if error_response is not None:
        # Re-raise as exception to be handled by decorator
        raise ValueError(error_response[0]["error"])

    assert clip_id is not None
    logger.debug(
        f"Attempting to download clip with ID: {clip_id} (is_local: {clip_id.is_local()})"
    )
    if clip_id.is_local():
        sync_name, item_id = clip_id.get_local_parts()
        logger.debug(f"Local clip - sync_name: {sync_name}, item_id: {item_id}")
        return download_local_clip(clip_id, sync_name, item_id)
    else:
        logger.debug(f"Cloud clip - ID: {clip_id}")
        return download_cloud_clip(clip_id)


def _download_clip_common(
    clip_id: ClipId, filepath: Path, filename: str, middle_frame: bool = False
) -> ResponseReturnValue:
    """Common clip download logic after file is downloaded.

    Args:
        clip_id: Unique identifier for the clip
        filepath: Path to the downloaded clip file
        filename: Original filename for the clip
        middle_frame: Whether to extract middle frame as thumbnail

    Returns:
        Flask response with clip file or error message
    """
    # Cache the clip first (without thumbnail)
    clips_download_cache[clip_id] = {
        "filepath": filepath,
        "thumbnail": None,
    }

    # Generate thumbnail in background
    def generate_thumbnail_bg() -> None:
        thumbnail_path = generate_clip_thumbnail(
            filepath, filename, middle_frame=middle_frame
        )
        if thumbnail_path is not None:
            # Update cache with thumbnail atomically
            cached_clip = clips_download_cache.get(clip_id)
            if cached_clip is not None:
                # Create new dict to avoid race conditions
                updated_clip = cached_clip.copy()
                updated_clip["thumbnail"] = thumbnail_path
                clips_download_cache[clip_id] = updated_clip
            # Notify clients that thumbnail is ready
            notify_thumbnail_ready(clip_id)

    executor.submit(generate_thumbnail_bg)
    response = send_file(str(filepath), as_attachment=True, download_name=filename)
    return response, 200
    return response, 200


@requires_blink
def download_cloud_clip(clip_id: ClipId) -> ResponseReturnValue:
    """Download cloud storage clip."""
    assert blink is not None
    # Check if already cached
    cached_clip = clips_download_cache.get(clip_id)
    if cached_clip is not None:
        try:
            # Quick existence check - if it fails, we'll re-download
            if cached_clip["filepath"].exists():
                response = send_file(str(cached_clip["filepath"]), as_attachment=True)
                return response, 200
        except (OSError, AttributeError):
            # File doesn't exist or path is invalid, continue to download
            pass

    # Get clip metadata
    videos_metadata = blink_connection.execute(
        blink.get_videos_metadata(stop=Config.MAX_VIDEOS_METADATA)
    )
    clip_info = next(
        (v for v in videos_metadata if str(v.get("id")) == str(clip_id)), None
    )
    if clip_info is None:
        api_response, status_code = create_api_response(
            success=False, error=Config.ErrorMessages.CLIP_NOT_FOUND, status_code=404
        )
        return jsonify(api_response), status_code

    # Generate filename
    created_at = datetime.fromisoformat(clip_info["created_at"].replace("Z", "+00:00"))
    camera_name = clip_info.get("device_name", "unknown")
    iso_date = created_at.strftime("%Y-%m-%dT%H-%M-%S")
    filename = f"{clip_id}_{camera_name}_{iso_date}.mp4"
    assert CLIPS_CACHE_DIR is not None
    filepath = Path(cast(str, CLIPS_CACHE_DIR)) / filename

    # Download if not cached
    if not filepath.exists():
        media_url = clip_info.get("media")
        if media_url is None:
            api_response, status_code = create_api_response(
                success=False,
                error=Config.ErrorMessages.CLIP_NO_MEDIA_URL,
                status_code=404,
            )
            return jsonify(api_response), status_code

        # Download in executor to avoid blocking
        def download_file() -> bool:
            try:
                response = http_session.get(media_url, timeout=Config.HTTP_TIMEOUT)
                if response.status_code == Config.HTTP_STATUS_OK:
                    filepath.write_bytes(response.content)
                    return True
                else:
                    logger.error(
                        f"HTTP {response.status_code} downloading clip {clip_id}"
                    )
                    return False
            except (requests.RequestException, OSError) as e:
                logger.error(f"Error downloading clip {clip_id}: {e}")
                return False

        # Execute download synchronously since we need the file immediately
        future = executor.submit(download_file)
        try:
            success = future.result(timeout=Config.DOWNLOAD_TIMEOUT)
            if not success:
                api_response, status_code = create_api_response(
                    success=False,
                    error=Config.ErrorMessages.CLIP_DOWNLOAD_FAILED,
                    status_code=500,
                )
                return jsonify(api_response), status_code
        except Exception as e:
            logger.error(f"Download timeout or error for clip {clip_id}: {e}")
            api_response, status_code = create_api_response(
                success=False,
                error=Config.ErrorMessages.CLIP_DOWNLOAD_TIMEOUT,
                status_code=500,
            )
            return jsonify(api_response), status_code

    return _download_clip_common(clip_id, filepath, filename, middle_frame=False)


@requires_blink
def download_local_clip(
    clip_id: ClipId, sync_name: str, item_id: int
) -> ResponseReturnValue:
    """Download local storage clip using blinkpy methods."""
    assert blink is not None
    # Check if already cached
    cached_clip = clips_download_cache.get(clip_id)
    if cached_clip is not None:
        try:
            # Quick existence check - if it fails, we'll re-download
            if cached_clip["filepath"].exists():
                response = send_file(str(cached_clip["filepath"]), as_attachment=True)
                return response, 200
        except (OSError, AttributeError):
            # File doesn't exist or path is invalid, continue to download
            pass

    # Find sync module and clip item
    sync_module = blink.sync.get(sync_name)
    if sync_module is None:
        api_response, status_code = create_api_response(
            success=False,
            error=Config.ErrorMessages.SYNC_MODULE_NOT_FOUND,
            status_code=404,
        )
        return jsonify(api_response), status_code

    if not sync_module.local_storage or not sync_module.local_storage_manifest_ready:
        api_response, status_code = create_api_response(
            success=False,
            error=Config.ErrorMessages.LOCAL_STORAGE_NOT_AVAILABLE,
            status_code=404,
        )
        return jsonify(api_response), status_code

    manifest = sync_module._local_storage["manifest"]
    item = next((i for i in manifest if i.id == item_id), None)
    if item is None:
        api_response, status_code = create_api_response(
            success=False,
            error=Config.ErrorMessages.LOCAL_CLIP_NOT_FOUND,
            status_code=404,
        )
        return jsonify(api_response), status_code

    # Generate filename
    iso_date = item.created_at.strftime("%Y-%m-%dT%H-%M-%S")
    filename = f"{clip_id}_{item.name}_{iso_date}.mp4"
    assert CLIPS_CACHE_DIR is not None
    filepath = Path(cast(str, CLIPS_CACHE_DIR)) / filename

    # Download if not cached
    if not filepath.exists():
        try:
            blink_connection.execute(item.prepare_download(blink))
            success = blink_connection.execute(
                item.download_video(blink, str(filepath))
            )
            if success is not True:
                api_response, status_code = create_api_response(
                    success=False,
                    error=Config.ErrorMessages.CLIP_DOWNLOAD_FAILED,
                    status_code=500,
                )
                return jsonify(api_response), status_code
        except Exception as e:
            logger.error(f"Error downloading local clip: {e}")
            api_response, status_code = create_api_response(
                success=False,
                error=Config.ErrorMessages.CLIP_DOWNLOAD_FAILED,
                status_code=500,
            )
            return jsonify(api_response), status_code

    return _download_clip_common(clip_id, filepath, filename, middle_frame=True)


def process_local_clip_background(
    clip_id: ClipId, sync_name: str, item_id: int
) -> None:
    """Process local clip in background (download and generate thumbnail).

    Downloads clip from USB storage and generates thumbnail for web interface.
    Runs in background thread to avoid blocking API responses.

    Args:
        clip_id: Unique identifier for the clip
        sync_name: Name of the sync module containing the clip
        item_id: Local storage item ID
    """

    def process() -> None:
        try:
            # Check if already cached
            cached_clip = clips_download_cache.get(clip_id)
            if cached_clip is not None and cached_clip["filepath"].exists():
                return

            assert blink is not None
            # Find sync module and clip item
            sync_module = blink.sync.get(sync_name)
            if (
                sync_module is None
                or not sync_module.local_storage
                or not sync_module.local_storage_manifest_ready
            ):
                return

            manifest = sync_module._local_storage["manifest"]
            item = next((i for i in manifest if i.id == item_id), None)
            if not item:
                return

            # Generate filename and download
            iso_date = item.created_at.strftime("%Y-%m-%dT%H-%M-%S")
            filename = f"{clip_id}_{item.name}_{iso_date}.mp4"
            assert CLIPS_CACHE_DIR is not None
            filepath = Path(cast(str, CLIPS_CACHE_DIR)) / filename

            if not filepath.exists():
                blink_connection.execute(item.prepare_download(blink))
                success = blink_connection.execute(
                    item.download_video(blink, str(filepath))
                )
                if success is not True:
                    return

            # Cache the clip and generate thumbnail
            clips_download_cache[clip_id] = {"filepath": filepath, "thumbnail": None}
            thumbnail_path = generate_clip_thumbnail(
                filepath, filename, middle_frame=True
            )
            if thumbnail_path is not None:
                cached_clip = clips_download_cache.get(clip_id)
                if cached_clip is not None:
                    updated_clip = cached_clip.copy()
                    updated_clip["thumbnail"] = thumbnail_path
                    clips_download_cache[clip_id] = updated_clip
        except Exception as e:
            logger.error(f"Error processing local clip {clip_id}: {e}")

    executor.submit(process)


def process_cloud_clip_background(clip_id: ClipId) -> None:
    """Process cloud clip in background (download and generate thumbnail).

    Downloads clip from Blink cloud storage and generates thumbnail for web interface.
    Runs in background thread to avoid blocking API responses.

    Args:
        clip_id: Unique identifier for the cloud clip
    """

    def process() -> None:
        assert blink is not None
        try:
            # Check if already cached
            cached_clip = clips_download_cache.get(clip_id)
            if cached_clip is not None and cached_clip["filepath"].exists():
                return

            # Get clip metadata
            videos_metadata = blink_connection.execute(
                blink.get_videos_metadata(stop=Config.MAX_VIDEOS_METADATA)
            )
            clip_info = next(
                (v for v in videos_metadata if str(v.get("id")) == str(clip_id)), None
            )
            if not clip_info:
                return

            # Generate filename and download
            created_at = datetime.fromisoformat(
                clip_info["created_at"].replace("Z", "+00:00")
            )
            camera_name = clip_info.get("device_name", "unknown")
            iso_date = created_at.strftime("%Y-%m-%dT%H-%M-%S")
            filename = f"{clip_id}_{camera_name}_{iso_date}.mp4"
            assert CLIPS_CACHE_DIR is not None
            filepath = Path(cast(str, CLIPS_CACHE_DIR)) / filename

            if not filepath.exists():
                media_url = clip_info.get("media")
                if not media_url:
                    return
                try:
                    response = http_session.get(media_url, timeout=Config.HTTP_TIMEOUT)
                    if response.status_code == Config.HTTP_STATUS_OK:
                        filepath.write_bytes(response.content)
                    else:
                        logger.error(
                            f"HTTP {response.status_code} downloading clip for processing"
                        )
                        return
                except (requests.RequestException, OSError) as e:
                    logger.error(f"Error downloading clip for processing: {e}")
                    return

            # Cache the clip and generate thumbnail
            clips_download_cache[clip_id] = {"filepath": filepath, "thumbnail": None}
            thumbnail_path = generate_clip_thumbnail(
                filepath, filename, middle_frame=False
            )
            if thumbnail_path is not None:
                cached_clip = clips_download_cache.get(clip_id)
                if cached_clip is not None:
                    updated_clip = cached_clip.copy()
                    updated_clip["thumbnail"] = thumbnail_path
                    clips_download_cache[clip_id] = updated_clip
        except Exception as e:
            logger.error(f"Error processing cloud clip {clip_id}: {e}")

    executor.submit(process)


# Stream management functions moved to StreamManager class


# @app.route("/api/camera/<camera_id_str>/liveview")
@requires_blink
@api_route_with_validation(
    "start camera liveview", validate_params={"camera_id_str": CameraId}
)
def get_camera_liveview(camera_id: CameraId) -> JsonDict:
    """Get live view stream for camera using init_livestream() as specified in IMPLEMENTATION.md.

    Args:
        camera_id: Validated CameraId object (converted from camera_id_str by decorator)

    Returns:
        JSON response with stream URLs (TCP and HLS) or error message

    Raises:
        ValueError: If camera_id_str is invalid
    """
    # camera_id is now validated and converted by the decorator

    camera, error_response = require_camera(camera_id)
    if error_response is not None:
        # Re-raise as exception to be handled by decorator
        raise ValidationError(error_response[0]["error"], error_response[1])

    assert camera is not None

    # Use init_livestream() as specified in IMPLEMENTATION.md
    async def init_stream() -> object:
        stream = await camera.init_livestream()
        if stream is not None and hasattr(stream, "start") and hasattr(stream, "feed"):
            await stream.start()
            # Start feeding the stream in the background
            asyncio.create_task(stream.feed())
        return stream

    # Execute the async livestream initialization
    stream = blink_connection.execute(init_stream())

    if stream is not None:
        # Get the TCP URL from the stream
        tcp_url = stream.url
        logger.info(f"Livestream TCP URL for camera {camera_id}: {tcp_url}")

        # Start HLS transcoding from the TCP stream
        if stream_manager is not None:
            hls_url, error_msg = stream_manager.start_stream(str(camera_id), tcp_url)
        else:
            hls_url = None

        if hls_url is not None:
            # Store the stream object for later cleanup
            if not hasattr(blink_connection, "_active_streams"):
                blink_connection._active_streams = {}
            active_streams = getattr(blink_connection, "_active_streams", {})
            active_streams[str(camera_id)] = stream

            return {
                "tcp_url": tcp_url,
                "hls_url": hls_url,
                "stream_id": str(camera_id),
            }
        else:
            # Clean up the stream if HLS transcoding failed
            if hasattr(stream, "stop"):
                try:
                    stream.stop()
                except Exception as e:
                    logger.warning(f"Error stopping stream during cleanup: {e}")

            raise RuntimeError(Config.ErrorMessages.HLS_TRANSCODING_FAILED)
    else:
        raise RuntimeError(Config.ErrorMessages.LIVE_VIEW_FAILED)


# @app.route("/api/camera/<camera_id_str>/liveview/stop", methods=["POST"])
@api_route_with_validation(
    "stop camera liveview", validate_params={"camera_id_str": CameraId}
)
def stop_camera_liveview(camera_id: CameraId) -> JsonDict:
    """Stop live view stream for camera.

    Args:
        camera_id: Validated CameraId object (converted from camera_id_str by decorator)

    Returns:
        JSON response with success status or error message
    """

    # Stop the HLS stream
    if stream_manager is not None:
        stream_manager.stop_stream(str(camera_id))

    # Stop the TCP livestream if it exists
    if hasattr(blink_connection, "_active_streams"):
        stream = blink_connection._active_streams.get(str(camera_id))
        if stream and hasattr(stream, "stop"):
            try:
                stream.stop()
                logger.info(f"Stopped livestream for camera {camera_id}")
            except Exception as e:
                logger.warning(f"Error stopping livestream for camera {camera_id}: {e}")
            finally:
                # Remove from active streams
                del blink_connection._active_streams[str(camera_id)]

    return {"message": "Livestream stopped successfully"}


# @app.route("/api/hls/<camera_id_str>/<path:filename>")
@file_response_route("serve HLS file", validate_params={"camera_id_str": CameraId})
def serve_hls_file(camera_id: CameraId, filename: str) -> FlaskResponse:
    """Serve HLS playlist and segment files.

    Args:
        camera_id: Validated CameraId object (converted from camera_id_str by decorator)
        filename: Name of the HLS file to serve

    Returns:
        Flask response with HLS file content or error message
    """
    if not stream_manager:
        raise RuntimeError(Config.ErrorMessages.STREAM_MANAGER_UNAVAILABLE)

    file_path = stream_manager.get_stream_file(str(camera_id), filename)

    if file_path is None:
        raise FileNotFoundError(Config.ErrorMessages.STREAM_NOT_FOUND)

    if filename.endswith(".m3u8"):
        file_response = send_file(
            str(file_path), mimetype="application/vnd.apple.mpegurl"
        )
        return file_response
    elif filename.endswith(".ts"):
        file_response = send_file(str(file_path), mimetype="video/mp2t")
        return file_response
    else:
        raise ValueError(Config.ErrorMessages.INVALID_FILE_TYPE)


@app.route("/api/clip/<clip_id_str>/thumbnail")
@file_response_route("get clip thumbnail", validate_params={"clip_id_str": ClipId})
def get_clip_thumbnail(clip_id) -> ResponseReturnValue:
    """Serve clip thumbnail."""

    cached_clip = clips_download_cache.get(clip_id)
    if cached_clip is not None:
        thumbnail_path = cached_clip.get("thumbnail")
        if thumbnail_path is not None and thumbnail_path.exists():
            response = send_file(str(thumbnail_path), mimetype="image/jpeg")
            return response, 200

    raise ValidationError(Config.ErrorMessages.THUMBNAIL_NOT_FOUND, 404)


# @app.route("/api/camera/<camera_id_str>/thumbnail/timestamp")
@requires_blink
@api_route_with_validation(
    "get camera thumbnail timestamp", validate_params={"camera_id_str": CameraId}
)
def get_camera_thumbnail_timestamp(camera_id: CameraId) -> JsonDict:
    """Get camera thumbnail timestamp for polling.

    Args:
        camera_id: Validated CameraId object (converted from camera_id_str by decorator)

    Returns:
        JSON response with timestamp or error message

    Raises:
        ValueError: If camera_id_str is invalid
    """
    # camera_id is now validated and converted by the decorator

    camera = find_camera_by_id(camera_id)
    if camera is None:
        raise ValidationError(Config.ErrorMessages.CAMERA_NOT_FOUND, 404)

    timestamp = extract_thumbnail_timestamp(camera.thumbnail)
    logger.info(
        f"Camera {camera_id} thumbnail timestamp: {timestamp}, URL: {camera.thumbnail}"
    )
    return {"timestamp": timestamp}


# @app.route("/api/camera/<camera_id_str>/thumbnail")
@requires_blink
@api_route_with_validation(
    "get camera thumbnail", validate_params={"camera_id_str": CameraId}
)
def get_camera_thumbnail(camera_id: CameraId) -> FlaskResponse:
    """Proxy camera thumbnail with authentication.

    Args:
        camera_id: Validated CameraId object (converted from camera_id_str by decorator)

    Returns:
        Flask Response with image data or error message

    Returns:
        JPEG image file or JSON error response

    Raises:
        ValueError: If camera_id_str is invalid
    """
    # camera_id is now validated and converted by the decorator

    camera = find_camera_by_id(camera_id)
    if camera is None or camera.thumbnail is None:
        raise ValidationError(Config.ErrorMessages.CAMERA_THUMBNAIL_NOT_FOUND, 404)

    # Check cache first
    cached_thumbnail = thumbnail_cache.get(camera_id)
    if cached_thumbnail is not None:
        logger.debug(f"Serving cached thumbnail for camera {camera_id}")
        filename = cached_thumbnail["filename"]
        assert THUMBNAIL_CACHE_DIR is not None
        filepath = Path(cast(str, THUMBNAIL_CACHE_DIR)) / filename
        if filepath.exists():
            file_response = send_file(str(filepath), mimetype="image/jpeg")
            file_response.headers["Cache-Control"] = (
                "no-cache, no-store, must-revalidate"
            )
            return file_response

    # If not cached, fetch via blink operation
    response = blink_connection.execute(camera.thumbnail)
    if response is not None and response.status == Config.HTTP_STATUS_OK:
        image_data = blink_connection.execute(response.read())
        return FlaskResponse(image_data, mimetype="image/jpeg")
    else:
        raise RuntimeError(Config.ErrorMessages.THUMBNAIL_FETCH_FAILED)


def notify_thumbnail_ready(clip_id: ClipId) -> None:
    """Thumbnail ready notification (no longer needed with polling approach)."""
    logger.debug(f"Thumbnail ready for clip: {clip_id}")


# ============================================================================
# API Routes - Configuration and Settings
# ============================================================================


@app.route("/api/config")
@api_route("get config")
def get_config() -> JsonDict:
    """Get client-side configuration constants.

    Provides configuration values needed by the web interface for
    timing intervals, polling frequencies, and display durations.
    This centralizes all client-side configuration in the Config class.

    Returns:
        JSON response with configuration values for the client
    """
    config_data = {
        "hls_stream_check_interval": Config.HLS_STREAM_CHECK_INTERVAL,
        "hls_stream_check_delay": Config.HLS_STREAM_CHECK_DELAY,
        "hls_stream_max_attempts": Config.HLS_STREAM_MAX_ATTEMPTS,
        "thumbnail_update_poll_interval": Config.THUMBNAIL_UPDATE_POLL_INTERVAL,
        "thumbnail_success_display_time": Config.THUMBNAIL_SUCCESS_DISPLAY_TIME,
        "thumbnail_processing_display_time": Config.THUMBNAIL_PROCESSING_DISPLAY_TIME,
        "clip_thumbnail_check_interval": Config.CLIP_THUMBNAIL_CHECK_INTERVAL,
        "clip_thumbnail_poll_max_attempts": Config.CLIP_THUMBNAIL_POLL_MAX_ATTEMPTS,
        "thumbnail_error_display_time": Config.THUMBNAIL_ERROR_DISPLAY_TIME,
        "milliseconds_to_seconds": Config.MILLISECONDS_TO_SECONDS,
        # User-friendly error messages for frontend
        "error_messages": {
            "live_stream_failed": "Unable to start live video. Please check your camera connection and try again.",
            "live_stream_connection_failed": "Unable to start live video. Please check your internet connection and try again.",
            "live_view_failed": "Unable to start live view. Please check that your camera is online and try again.",
            "connection_error": "Unable to connect. Please check your internet connection and try again.",
            "arm_state_failed": "Unable to change system status. Please check your connection and try again.",
            "clip_download_failed": "Unable to download video. Please try again later.",
            "clip_play_failed": "Unable to play video. Please check your connection and try again.",
            "cache_clear_success": "Cache cleared successfully! Your storage space has been freed up.",
            "cache_clear_failed": "Unable to clear cache. Please check your connection and try again.",
            "logout_failed": "Unable to log out. Please try again.",
            "clips_updated": "All your local video clips are already up to date!",
            "feature_coming_soon": "This feature is coming soon! We're working hard to bring it to you.",
        },
    }

    return config_data


@app.route("/placeholder")
@api_route("placeholder")
def placeholder() -> JsonDict:
    """Show placeholder message.

    Returns:
        JSON response with placeholder message
    """
    from flask import jsonify

    response, status_code = create_api_response(
        success=False,
        error=Config.ErrorMessages.FEATURE_NOT_AVAILABLE,
        status_code=Config.HTTP_STATUS_NOT_IMPLEMENTED,
    )
    return jsonify(response), status_code


def dump_cloud_videos(videos: list[dict[str, object]]) -> None:
    """Dump cloud videos information."""
    logger.info("=== CLOUD VIDEOS ===")
    try:
        logger.info(f"Found {len(videos)} cloud videos:")
        for video in videos:
            logger.info(f"  - {video}")
    except Exception as e:
        logger.error(f"Error processing cloud videos: {e}")


def dump_blink_system_info() -> None:
    """Dump comprehensive Blink system information."""
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
    import json

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
        logger.info(f"--- Camera: {camera_name} ---")
        logger.info(f"Attributes: {camera.attributes}")

    logger.info("=== CLOUD VIDEOS (see separate dump) ===")

    logger.info("=== END DUMP ===")


def startup() -> None:
    """Initialize application on startup.

    Performs complete application initialization including:
    1. Cache directory setup and path initialization
    2. Logging configuration with file rotation
    3. Existing cache scanning and validation
    4. Blink connection thread startup
    5. Saved credentials loading and validation

    Error Handling:
        - Invalid cache directories: Creates new ones
        - Corrupted credentials: Removes and logs warning
        - Blink connection failures: Logs error, continues startup
        - File system errors: Graceful degradation

    Side Effects:
        - Creates cache directories if missing
        - Starts background thread pool
        - Initializes global Blink connection
        - Sets up rotating log files

    Note:
        If no valid credentials found, user must login via web interface.
        All errors are logged but don't prevent application startup.
    """
    global stream_manager, blink_connection, executor

    # Import here to avoid circular imports
    from concurrent.futures import ThreadPoolExecutor

    from blink_connection import BlinkConnection

    try:
        # Initialize executor for background tasks
        executor = ThreadPoolExecutor(max_workers=Config.THREAD_POOL_MAX_WORKERS)

        # Initialize Blink connection
        blink_connection = BlinkConnection(timeout=Config.BLINK_CONNECTION_TIMEOUT)
        # Initialize cache paths
        initialize_cache_paths()

        # Create cache directories if they don't exist
        assert CACHE_DIR is not None
        Path(CACHE_DIR).mkdir(exist_ok=True)
        assert THUMBNAIL_CACHE_DIR is not None
        assert CLIPS_CACHE_DIR is not None
        Path(cast(str, THUMBNAIL_CACHE_DIR)).mkdir(exist_ok=True)
        Path(cast(str, CLIPS_CACHE_DIR)).mkdir(exist_ok=True)

        # Setup logging with rotation in cache directory
        setup_logging()

        # Initialize stream manager for server mode
        stream_config = StreamConfig(
            segment_time=Config.HLS_SEGMENT_TIME,
            list_size=Config.HLS_LIST_SIZE,
            timeout=Config.FFMPEG_TIMEOUT,
            idle_timeout=Config.STREAM_IDLE_TIMEOUT,
        )
        stream_manager = StreamManager(stream_config)

        # Load existing thumbnails from cache
        load_thumbnail_cache()

        # Load existing clips from cache
        load_clips_cache()

        # Initialize Blink thread for startup
        blink_connection.start()

        try:
            success = blink_connection.execute(load_saved_blink())
            if success is not True:
                logger.info(
                    "No valid saved credentials found - user will need to login"
                )
            elif logger.isEnabledFor(logging.INFO):
                # Dump system info if info logging is enabled
                dump_blink_system_info()
        except Exception as e:
            logger.error(f"Error loading saved Blink credentials: {e}")
            logger.info("Credentials preserved - log out if error persists")
    except Exception as e:
        logger.warning(f"Could not initialize Blink system on startup: {e}")


def generate_clip_thumbnail(
    video_path: Path, filename: str, middle_frame: bool = False
) -> Path | None:
    """Generate thumbnail image from video clip using FFmpeg.

    Extracts a single frame from video file and saves as JPEG thumbnail.
    Uses different extraction strategies based on clip type:
    - Cloud clips: First frame (fast, consistent)
    - Local clips: Middle frame (better representation)

    Args:
        video_path: Path to source video file (must exist)
        filename: Original video filename for thumbnail naming
        middle_frame: If True, extract middle frame; if False, first frame

    Returns:
        Path to generated thumbnail file, or None if generation failed

    Process:
        1. Check if thumbnail already exists (skip if found)
        2. For middle frame: Use ffprobe to get duration, calculate midpoint
        3. For first frame: Extract frame at 1 second mark
        4. Use FFmpeg to extract frame as JPEG
        5. Save with same base name as video but .jpg extension

    FFmpeg Commands:
        - First frame: ffmpeg -i video.mp4 -ss 00:00:01 -vframes 1 -f image2 thumb.jpg
        - Middle frame: ffmpeg -i video.mp4 -ss {duration/2} -vframes 1 -f image2 thumb.jpg

    Error Handling:
        - Missing FFmpeg: Returns None, logs error
        - Corrupted video: Returns None, logs error
        - Timeout: Returns None after configured timeout
        - File system errors: Returns None, logs error

    Performance:
        - Respects configured timeouts (FFmpeg: 30s, FFprobe: 10s)
        - Skips generation if thumbnail exists
        - Runs in background thread to avoid blocking
    """
    thumbnail_filename = filename.replace(".mp4", ".jpg")
    assert CLIPS_CACHE_DIR is not None
    thumbnail_path = Path(cast(str, CLIPS_CACHE_DIR)) / thumbnail_filename

    if thumbnail_path.exists():
        return thumbnail_path

    import subprocess

    try:
        # Use ffmpeg to extract frame (middle frame for local clips, first frame for cloud)
        if middle_frame:
            # Get video duration and extract middle frame
            duration_cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                str(video_path),
            ]
            duration_result = subprocess.run(
                duration_cmd,
                capture_output=True,
                text=True,
                timeout=Config.FFPROBE_TIMEOUT,
                check=True,
            )
            duration = float(duration_result.stdout.strip()) / 2  # Middle timestamp
            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-ss",
                str(duration),
                "-vframes",
                "1",
                "-f",
                "image2",
                str(thumbnail_path),
            ]
        else:
            # Extract first frame
            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-ss",
                "00:00:01",
                "-vframes",
                "1",
                "-f",
                "image2",
                str(thumbnail_path),
            ]

        subprocess.run(
            cmd, capture_output=True, check=True, timeout=Config.FFMPEG_TIMEOUT
        )
        return thumbnail_path
    except subprocess.TimeoutExpired:
        logger.error(f"Thumbnail generation timed out for {video_path}")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(
            f"FFmpeg error generating thumbnail: {e.stderr.decode() if e.stderr else str(e)}"
        )
        return None
    except Exception as e:
        logger.error(f"Error generating thumbnail: {e}")
        return None


def load_thumbnail_cache() -> None:
    """Load and validate thumbnail cache from disk.

    Scans thumbnail cache directory for existing files and populates
    the in-memory cache with validated entries. Performs cleanup of
    invalid, duplicate, and orphaned thumbnail files.

    Process:
        1. Scans cache directory for .jpg files
        2. Parses filenames (format: camera_id_timestamp.jpg)
        3. Validates camera IDs against current Blink system
        4. Keeps only newest thumbnail per camera
        5. Removes invalid/old files in background

    File Format:
        - Valid: "camera123_1642459551.jpg"
        - Invalid: "invalid_format.jpg" (removed)

    Thread Safety:
        - Uses thread-safe cache operations
        - File removal happens in background thread
        - Race conditions prevented with proper error handling

    Error Handling:
        - Invalid filenames: Logged and removed
        - Missing cameras: Files removed if system available
        - File system errors: Logged, operation continues
    """
    assert THUMBNAIL_CACHE_DIR is not None
    cache_dir = Path(cast(str, THUMBNAIL_CACHE_DIR))
    if not cache_dir.exists():
        logger.warning(f"Thumbnail cache directory does not exist: {cache_dir}")
        return

    try:
        # Get valid camera IDs from current system
        valid_camera_ids = set()
        if blink and blink.available:
            for sync_name, sync in blink.sync.items():
                for cam_name, cam in sync.cameras.items():
                    valid_camera_ids.add(cam.camera_id)

        # Group thumbnails by camera ID
        camera_thumbnails: dict[str, list[tuple[int, str, Path]]] = {}
        files_to_remove = []

        for file_path in cache_dir.glob("*.jpg"):
            filename = file_path.name
            # Parse filename format: camera_id_timestamp.jpg
            parts = filename.replace(".jpg", "").split("_")
            if len(parts) >= 2:
                try:
                    camera_id = "_".join(
                        parts[:-1]
                    )  # Handle camera IDs with underscores
                    timestamp = int(parts[-1])

                    # Check if camera ID is valid for current system
                    if valid_camera_ids and camera_id not in valid_camera_ids:
                        logger.debug(
                            f"Removing thumbnail for invalid camera {camera_id}"
                        )
                        files_to_remove.append(file_path)
                        continue

                    # Group by camera ID
                    if camera_id not in camera_thumbnails:
                        camera_thumbnails[camera_id] = []
                    camera_thumbnails[camera_id].append(
                        (timestamp, filename, file_path)
                    )

                except (ValueError, IndexError) as e:
                    logger.warning(
                        f"Could not parse thumbnail filename {filename}: {e}"
                    )
                    files_to_remove.append(file_path)

        # Keep only the newest thumbnail per camera
        for camera_id, thumbnails in camera_thumbnails.items():
            # Sort by timestamp (newest first)
            thumbnails.sort(key=lambda x: x[0], reverse=True)

            # Keep the newest, mark others for removal
            if thumbnails:
                newest_ts, newest_filename, newest_path = thumbnails[0]
                thumbnail_cache[CameraId(camera_id)] = {
                    "timestamp": newest_ts,
                    "filename": newest_filename,
                }
                logger.debug(
                    f"Loaded cached thumbnail for camera {camera_id} with timestamp {newest_ts}"
                )

                # Mark older thumbnails for removal
                for old_ts, old_filename, old_path in thumbnails[1:]:
                    logger.debug(
                        f"Removing old thumbnail {old_filename} for camera {camera_id}"
                    )
                    files_to_remove.append(old_path)

        # Remove invalid/old files in background
        def remove_files(files_list: list[Path]) -> None:
            for file_path in files_list:
                try:
                    file_path.unlink()
                    logger.debug(f"Removed invalid thumbnail: {file_path.name}")
                except (OSError, PermissionError) as e:
                    logger.warning(f"Could not remove thumbnail file {file_path}: {e}")

        if files_to_remove:
            executor.submit(remove_files, files_to_remove)

    except Exception as e:
        logger.error(f"Error scanning thumbnail cache: {e}")


def load_clips_cache() -> None:
    """Load clips cache directory and populate memory cache.

    Parses cached clip files with ClipId_camera_date.mp4 format,
    validates against Blink system, and removes invalid files.
    Thread-safe operation.
    """
    assert CLIPS_CACHE_DIR is not None
    cache_dir = Path(cast(str, CLIPS_CACHE_DIR))
    if not cache_dir.exists():
        logger.warning(f"Clips cache directory does not exist: {cache_dir}")
        return

    try:
        files_to_remove = []

        for video_file in cache_dir.glob("*.mp4"):
            try:
                filename = video_file.name
                # Parse filename format: clipid_camera_date.mp4
                parts = filename.replace(".mp4", "").split("_", 1)
                if len(parts) < 2:
                    logger.debug(f"Invalid filename format: {filename}")
                    files_to_remove.append(video_file)
                    continue

                clip_id_str = parts[0]
                try:
                    clip_id = ClipId(clip_id_str)
                except ValueError:
                    logger.debug(f"Invalid clip ID in filename: {filename}")
                    files_to_remove.append(video_file)
                    continue

                # Check corresponding thumbnail
                thumbnail_name = filename.replace(".mp4", ".jpg")
                thumbnail_path = cache_dir / thumbnail_name

                # Validate clip exists in Blink system
                if blink and blink.available:
                    clip_valid = False
                    try:
                        if clip_id.is_local():
                            # Validate local clip
                            sync_name, item_id = clip_id.get_local_parts()
                            if sync_name in blink.sync:
                                sync_module = blink.sync[sync_name]
                                if (
                                    sync_module.local_storage
                                    and sync_module.local_storage_manifest_ready
                                ):
                                    manifest = sync_module._local_storage["manifest"]
                                    for item in manifest:
                                        if item.id == item_id:
                                            clip_valid = True
                                            break
                        else:
                            # Validate cloud clip (simplified check)
                            videos_metadata = blink_connection.execute(
                                blink.get_videos_metadata(
                                    stop=Config.MAX_VIDEOS_METADATA
                                )
                            )
                            for video in videos_metadata:
                                if str(video.get("id")) == str(clip_id):
                                    clip_valid = True
                                    break
                    except Exception as e:
                        logger.debug(f"Error validating clip {clip_id}: {e}")

                    if not clip_valid:
                        logger.debug(
                            f"Clip {clip_id} no longer exists, removing cached files"
                        )
                        files_to_remove.append(video_file)
                        if thumbnail_path.exists():
                            files_to_remove.append(thumbnail_path)
                        continue

                # Add to cache
                clips_download_cache[clip_id] = {
                    "filepath": video_file,
                    "thumbnail": thumbnail_path if thumbnail_path.exists() else None,
                }
                logger.debug(f"Loaded cached clip {clip_id}")

            except Exception as e:
                logger.debug(f"Could not process cached clip {video_file}: {e}")
                files_to_remove.append(video_file)

        # Remove invalid files in background
        def remove_files(files_list: list[Path]) -> None:
            for file_path in files_list:
                try:
                    file_path.unlink()
                    logger.debug(f"Removed invalid cached file: {file_path.name}")
                except (OSError, PermissionError) as e:
                    logger.warning(f"Could not remove file {file_path}: {e}")

        if files_to_remove:
            executor.submit(remove_files, files_to_remove)

    except (OSError, PermissionError) as e:
        logger.error(f"Error scanning clips cache: {e}")


# Removed generate_thumbnail_async - thumbnails only generated on clip download


@app.route("/api/settings", methods=["GET", "POST"])
@method_dispatch_route("settings")
def settings() -> ResponseReturnValue:
    """Get or save application settings.

    GET: Returns current user settings (temperature units, clip retention, etc.)
    POST: Updates settings with provided JSON data

    Settings are persisted to cache/settings.json and survive logout/restart.
    """
    if request.method == "GET":
        # Load existing settings from file
        assert SETTINGS_FILE is not None
        settings_file = Path(cast(str, SETTINGS_FILE))

        if settings_file.exists():
            import json

            # Read saved settings from JSON file
            with open(settings_file) as f:
                settings_data = json.load(f)
        else:
            # Return default settings if no file exists
            settings_data = {
                "temperatureUnits": "celsius",
                "cloudClipRetention": "30",
                "localClipRetention": "never",
                "clipThumbnailSize": "medium",
            }

        response, status_code = create_api_response(success=True, data=settings_data)
        return jsonify(response), status_code

    else:  # POST - Save new settings
        # Validate incoming JSON data
        data = request.get_json()
        if not isinstance(data, dict):
            response, status_code = create_api_response(
                success=False,
                error=Config.ErrorMessages.INVALID_JSON_DATA,
                status_code=400,
            )
            return jsonify(response), status_code

        # Load existing settings to merge with new data
        assert SETTINGS_FILE is not None
        settings_file = Path(cast(str, SETTINGS_FILE))

        if settings_file.exists():
            import json

            # Load current settings from file
            with open(settings_file) as f:
                settings_data = json.load(f)
        else:
            # Start with empty settings if no file exists
            settings_data = {}

        # Merge new settings with existing ones
        settings_data.update(data)

        # Persist updated settings to file
        import json

        with open(settings_file, "w") as f:
            json.dump(settings_data, f, indent=2)

        response, status_code = create_api_response(
            success=True, data={"message": "Settings saved"}
        )
        return jsonify(response), status_code


@app.route("/api/clip/<clip_id_str>/thumbnail/check")
@api_route_with_validation(
    "check clip thumbnail", validate_params={"clip_id_str": ClipId}
)
def check_clip_thumbnail(clip_id: ClipId) -> JsonDict:
    """Check if thumbnail is available for clip.

    Args:
        clip_id: Validated ClipId object (converted from clip_id_str by decorator)

    Returns:
        JSON response with thumbnail availability status
    """
    # clip_id is now validated and converted by the decorator

    cached_clip = clips_download_cache.get(clip_id)
    if cached_clip is not None:
        thumbnail_path = cached_clip.get("thumbnail")
        if thumbnail_path is not None and thumbnail_path.exists():
            return {"available": True, "url": f"/api/clip/{clip_id}/thumbnail"}

    return {"available": False}


# Stream cleanup functions moved to StreamManager class


async def cleanup_blink_session() -> None:
    """Clean up Blink aiohttp session."""
    global blink
    if blink and hasattr(blink, "auth") and hasattr(blink.auth, "session"):
        try:
            await blink.auth.session.close()
        except Exception as e:
            logger.debug(f"Error closing Blink session: {e}")


def cleanup_resources() -> None:
    """Clean up all resources on application shutdown.

    Stops all active HLS streams and their FFmpeg processes.
    Terminates the Blink event loop gracefully.
    Called automatically on exit via atexit handler and signal handlers.
    """
    try:
        logger.info("Cleaning up resources...")

        # Shutdown executor
        if executor is not None:
            executor.shutdown(wait=False)

        # Shutdown stream manager if initialized
        if stream_manager is not None:
            stream_manager.shutdown()

        # Clean up active livestreams
        if blink_connection is not None and hasattr(
            blink_connection, "_active_streams"
        ):
            for stream_id, stream in blink_connection._active_streams.items():
                try:
                    if hasattr(stream, "stop"):
                        stream.stop()
                        logger.info(f"Stopped active livestream {stream_id}")
                except (AttributeError, RuntimeError, OSError) as e:
                    logger.warning(f"Error stopping livestream {stream_id}: {e}")
            blink_connection._active_streams.clear()

        # Clean up Blink session only if connection is active
        if (
            blink
            and blink_connection is not None
            and blink_connection.loop
            and blink_connection.loop.is_running()
        ):
            try:
                blink_connection.execute(cleanup_blink_session())
            except (RuntimeError, ConnectionError, TimeoutError) as e:
                logger.debug(f"Error during Blink session cleanup: {e}")

        # Shutdown Blink connection
        if blink_connection is not None:
            blink_connection.shutdown()

        # Close HTTP session
        if http_session is not None:
            try:
                http_session.close()
            except (AttributeError, RuntimeError) as e:
                logger.debug(f"Error closing HTTP session: {e}")

        logger.info("Resource cleanup completed")
    except (AttributeError, RuntimeError) as e:
        logger.warning(f"Error during resource cleanup: {e}")


def handle_dump_system() -> None:
    """Handle dump-system command line option."""
    initialize_cache_paths()

    # Add console handler for CLI output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    assert CREDENTIALS_FILE is not None
    cred_file = Path(cast(str, CREDENTIALS_FILE))
    if not cred_file.exists():
        logger.error("No saved credentials found.")
        logger.error("Please start the server and login first to save credentials.")
        sys.exit(1)

    blink_connection.start()
    try:
        success = blink_connection.execute(load_saved_blink())
        if success:
            # Update local storage manifests first
            assert blink is not None
            for sync_name, sync in blink.sync.items():
                if sync.local_storage:
                    blink_connection.execute(sync.update_local_storage_manifest())

            # Get cloud videos in blink thread
            assert blink is not None
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
            blink_connection.execute(cleanup_blink_session())

        # Remove console handler
        logger.removeHandler(console_handler)
        blink_connection.shutdown()


def signal_handler(signum: int, frame: Any) -> None:
    """Handle shutdown signals.

    Args:
        signum: Signal number received
        frame: Current stack frame (unused)

    Side Effects:
        Triggers cleanup and exits application
    """
    logger.info(f"Received signal {signum}, shutting down...")
    cleanup_resources()
    sys.exit(0)


# LRUCache automatically handles eviction, no manual cleanup needed


# ============================================================================
# Application Entry Point and CLI
# ============================================================================


def main() -> None:
    """Main entry point with command line argument parsing.

    Parses command line arguments and starts the Flask development server
    or handles special commands like system dumps. Supports configuration
    of host, port, debug mode, and cache directory.
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
        help=f"Cache directory for credentials, thumbnails, and clips (default: {Config.DEFAULT_CACHE_DIR})",
    )
    parser.add_argument(
        "--dump-system",
        action="store_true",
        help="Dump Blink system information and exit (requires saved credentials)",
    )

    args = parser.parse_args()

    # Set cache directory in app config
    app.config["CACHE_DIR"] = args.cache

    # Set logging level for all loggers
    log_level = getattr(logging, args.log_level)
    logging.getLogger().setLevel(log_level)
    logging.getLogger("blinkpy").setLevel(log_level)
    logging.getLogger("werkzeug").setLevel(log_level)
    logging.getLogger("flask").setLevel(log_level)

    # Handle dump-system option
    if args.dump_system:
        handle_dump_system()
        sys.exit(0)

    # Register cleanup handlers and initialize for server mode
    atexit.register(cleanup_resources)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    startup()

    try:
        app.run(debug=args.debug, host=args.host, port=args.port)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        cleanup_resources()


# Set up authentication routes
setup_auth_routes(app)

# Set up camera routes
setup_camera_routes(app)


if __name__ == "__main__":
    main()
