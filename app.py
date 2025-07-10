#!/usr/bin/env python3
"""Flask web server for Blink camera system.

This module provides a comprehensive web interface for managing Blink camera systems,
including live streaming, clip management, thumbnail caching, and real-time notifications.

Key Features:
    - Multi-system Blink camera management
    - Real-time camera thumbnails with intelligent caching
    - Live streaming via RTSP to HLS transcoding
    - Cloud and local storage clip management
    - Two-factor authentication support
    - RESTful API with 15+ endpoints
    - Polling-based thumbnail updates
    - Thread-safe operations with dedicated Blink connection

Architecture:
    - Flask web framework with responsive templates
    - Dedicated thread for all Blink API operations
    - FIFO caching with configurable limits
    - FFmpeg integration for video processing
    - Click-triggered polling for thumbnail updates
"""

import atexit
import os
import re
import signal
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    Tuple,
    TypedDict,
    Union,
)

# Add the blinkpy directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "blinkpy"))

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

if TYPE_CHECKING:
    from werkzeug.wrappers import Response
else:
    Response = Any

import logging
import traceback
from contextlib import contextmanager

import requests
from cachetools import LRUCache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from blink_connection import BlinkConnection
from blinkpy.auth import Auth  # type: ignore
from blinkpy.blinkpy import Blink  # type: ignore

# from flask_sse import sse  # No longer needed
from stream_manager import StreamConfig, StreamManager


# Centralized error handling
class BlinkError(Exception):
    """Base exception for Blink-related errors."""

    pass


class AuthenticationError(BlinkError):
    """Authentication-related errors."""

    pass


class CameraError(BlinkError):
    """Camera-related errors."""

    pass


class StreamError(BlinkError):
    """Streaming-related errors."""

    pass


class CacheError(BlinkError):
    """Cache-related errors."""

    pass


@contextmanager
def error_context(operation: str, reraise_as: type = BlinkError):
    """Context manager for consistent error handling."""
    try:
        yield
    except Exception as e:
        logger.error(f"Error during {operation}: {e}")
        logger.debug(f"Full traceback for {operation}: {traceback.format_exc()}")
        if isinstance(e, BlinkError):
            raise
        raise reraise_as(f"Failed to {operation}: {str(e)}") from e


def safe_execute(func, default: Any = None, log_error: bool = True) -> Any:
    """Execute function safely with error logging.

    Args:
        func: Function to execute safely
        default: Default value to return on exception
        log_error: Whether to log errors

    Returns:
        Function result or default value on exception
    """
    try:
        return func()
    except Exception as e:
        if log_error:
            logger.error(f"Safe execution failed: {e}")
            logger.debug(f"Full traceback: {traceback.format_exc()}")
        return default


# Base ID class with common functionality
class BaseId:
    """Base class for validated ID types.

    Provides common validation and comparison functionality for ID classes.
    Subclasses must implement _get_pattern() and _get_type_name().

    Attributes:
        value: The validated ID string value
    """

    def __init__(self, value: str) -> None:
        """Initialize and validate ID value.

        Args:
            value: String ID to validate

        Raises:
            ValueError: If value is empty or doesn't match pattern
        """
        self.value = self._validate(value)

    def _validate(self, value: str) -> str:
        """Validate ID value against pattern.

        Args:
            value: String to validate

        Returns:
            Validated and stripped string

        Raises:
            ValueError: If validation fails
        """
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{self._get_type_name()} cannot be empty")
        value = value.strip()
        if not re.match(self._get_pattern(), value):
            raise ValueError(f"Invalid {self._get_type_name()} format")
        return value

    def _get_pattern(self) -> str:
        """Get validation regex pattern.

        Returns:
            Regex pattern string for validation

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement _get_pattern")

    def _get_type_name(self) -> str:
        """Get human-readable type name.

        Returns:
            Type name for error messages

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement _get_type_name")

    def __str__(self) -> str:
        """Return string representation."""
        return self.value

    def __eq__(self, other) -> bool:
        """Check equality with another BaseId instance."""
        return isinstance(other, self.__class__) and self.value == other.value

    def __hash__(self) -> int:
        """Return hash for use in sets and dicts."""
        return hash(self.value)


# ID classes with validation
class CameraId(BaseId):
    """Validated camera identifier.

    Represents a unique camera ID with validation against the configured pattern.
    Used throughout the application to ensure type safety for camera operations.
    """

    def _get_pattern(self) -> str:
        """Get camera ID validation pattern."""
        return Config.VALID_CAMERA_ID_PATTERN

    def _get_type_name(self) -> str:
        """Get type name for error messages."""
        return "Camera ID"


class NetworkId(BaseId):
    """Validated network identifier.

    Represents a unique Blink network/system ID with validation.
    Used for system-level operations like arming/disarming.
    """

    def _get_pattern(self) -> str:
        """Get network ID validation pattern."""
        return Config.VALID_NETWORK_ID_PATTERN

    def _get_type_name(self) -> str:
        """Get type name for error messages."""
        return "Network ID"


class ClipId(BaseId):
    """Validated clip identifier.

    Represents a unique clip ID for both cloud and local storage clips.
    Local clips use format 'sync_name~item_id', cloud clips use numeric IDs.
    """

    def _get_pattern(self) -> str:
        """Get clip ID validation pattern."""
        return Config.VALID_CLIP_ID_PATTERN

    def _get_type_name(self) -> str:
        """Get type name for error messages."""
        return "Clip ID"

    @classmethod
    def from_local(cls, sync_name: str, item_id: int) -> "ClipId":
        """Create ClipId for local storage clip.

        Args:
            sync_name: Name of the sync module
            item_id: ID of the clip item

        Returns:
            ClipId instance for local clip
        """
        return cls(f"{sync_name}~{item_id}")

    def is_local(self) -> bool:
        """Check if this is a local storage clip.

        Returns:
            True if local storage clip, False if cloud clip
        """
        return "~" in self.value

    def get_local_parts(self) -> Tuple[str, int]:
        """Get sync name and item ID for local clips.

        Returns:
            Tuple of (sync_name, item_id)

        Raises:
            ValueError: If not a local clip
        """
        if not self.is_local():
            raise ValueError("Not a local storage clip")
        sync_name, item_id_str = self.value.split("~", 1)
        return sync_name, int(item_id_str)


# Thread-safe cache wrapper for cachetools
class ThreadSafeCache:
    """Thread-safe wrapper for cachetools caches."""

    def __init__(self, cache):
        self._cache = cache
        self._lock = threading.RLock()

    def get(self, key: Any, default: Any = None) -> Any:
        """Get value from cache."""
        with self._lock:
            return self._cache.get(key, default)

    def __setitem__(self, key: Any, value: Any) -> None:
        """Set value in cache."""
        with self._lock:
            self._cache[key] = value

    def __getitem__(self, key: Any) -> Any:
        """Get value from cache with KeyError if not found."""
        with self._lock:
            return self._cache[key]

    def __contains__(self, key: Any) -> bool:
        """Check if key exists in cache."""
        with self._lock:
            return key in self._cache

    def pop(self, key: Any, default: Any = None) -> Any:
        """Remove and return value from cache."""
        with self._lock:
            return self._cache.pop(key, default)

    def clear(self) -> None:
        """Clear all entries from cache."""
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)


# Typed dictionaries for structured data
class ThumbnailCacheEntry(TypedDict):
    """Cache entry for camera thumbnails.

    Attributes:
        timestamp: Unix timestamp when thumbnail was captured
        filename: Cached thumbnail filename
    """

    timestamp: int
    filename: str


class ClipCacheEntry(TypedDict):
    """Cache entry for downloaded clips.

    Attributes:
        filepath: Path to cached video file
        thumbnail: Path to generated thumbnail image (optional)
    """

    filepath: Path
    thumbnail: Optional[Path]


# StreamInfo TypedDict removed - now handled by HLSStream class


class ApiResponse(TypedDict):
    """Standardized API response format.

    Attributes:
        success: Whether operation succeeded
        timestamp: ISO timestamp of response
        data: Response data (success only)
        error: Error message (failure only)
    """

    success: bool
    timestamp: str
    data: Optional[Any]
    error: Optional[str]


# Protocol for Blink objects
class BlinkCamera(Protocol):
    """Protocol for Blink camera objects from blinkpy library.

    Attributes:
        camera_id: Unique camera identifier
        name: Human-readable camera name
        thumbnail: URL to current thumbnail image
        motion_enabled: Whether motion detection is enabled
        battery: Battery level string (if applicable)
        temperature: Temperature reading string (if applicable)
        wifi_strength: WiFi signal strength (0-5)
        last_record: ISO timestamp of last recorded event
    """

    camera_id: str
    name: str
    thumbnail: Optional[str]
    motion_enabled: bool
    battery: Optional[str]
    temperature: Optional[str]
    wifi_strength: Optional[int]
    last_record: Optional[str]


class BlinkSync(Protocol):
    """Protocol for Blink sync module objects from blinkpy library.

    Attributes:
        network_id: Unique network identifier
        sync_id: Sync module identifier
        arm: Whether system is armed
        online: Whether sync module is online
        cameras: Dictionary of cameras by name
        local_storage: Local storage object (if available)
        local_storage_manifest_ready: Whether local storage manifest is ready
    """

    network_id: int
    sync_id: str
    arm: bool
    online: bool
    cameras: Dict[str, BlinkCamera]
    local_storage: Optional[Any]
    local_storage_manifest_ready: bool


# Configuration constants
class Config:
    """Application configuration constants.

    Centralizes all configuration values for the Blink Flask application.
    Includes cache settings, timeouts, validation patterns, and limits.
    """

    # Cache settings
    CLIPS_CACHE_SIZE = 100  # Maximum clips in cache
    CLIPS_METADATA_CACHE_SIZE = 1000  # Maximum clips metadata entries in cache
    THUMBNAIL_CACHE_SIZE = 100  # Maximum thumbnail entries in cache

    # FFmpeg settings
    FFMPEG_TIMEOUT = 30  # FFmpeg operation timeout
    FFPROBE_TIMEOUT = 10  # FFprobe operation timeout
    HLS_SEGMENT_TIME = 2  # HLS segment duration in seconds
    HLS_LIST_SIZE = 3  # Number of segments in HLS playlist
    STREAM_IDLE_TIMEOUT = 300  # 5 minutes before stream cleanup

    # Process settings
    PROCESS_TERMINATE_TIMEOUT = 5  # Graceful process termination timeout
    BLINK_OPERATION_TIMEOUT = 30  # Blink API operation timeout

    # API settings
    MAX_VIDEOS_METADATA = 50  # Maximum clips to fetch for metadata
    CLIPS_PER_STORAGE_TYPE = 5  # Clips to show per storage type

    # File settings
    LOG_FILE = "blink_app.log"  # Application log file (relative to cache dir)
    LOG_BACKUP_COUNT = 5  # Number of rotated log files to keep
    SECRET_KEY = "your-secret-key-here"  # Flask session secret

    # HTTP settings
    HTTP_TIMEOUT = 30  # HTTP request timeout
    DOWNLOAD_TIMEOUT = 60  # File download timeout

    # Polling settings
    THUMBNAIL_POLL_INTERVAL = 2  # Thumbnail polling interval in seconds
    THUMBNAIL_POLL_MAX_ATTEMPTS = 15  # Max polling attempts for thumbnail updates
    CACHE_CLEAR_TIMEOUT = 30  # Cache clearing operation timeout

    # Log settings
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB log file size limit

    # System name fallback
    DEFAULT_SYSTEM_NAME = "Blink System"  # Default system name for cloud clips

    # Validation settings
    MAX_USERNAME_LENGTH = 100  # Maximum username length
    MAX_PASSWORD_LENGTH = 100  # Maximum password length
    MAX_TFA_LENGTH = 10  # Maximum 2FA code length
    VALID_CAMERA_ID_PATTERN = r"^[a-zA-Z0-9_-]+$"  # Camera ID regex
    VALID_NETWORK_ID_PATTERN = r"^[0-9]+$"  # Network ID regex
    VALID_CLIP_ID_PATTERN = r"^[a-zA-Z0-9_~-]+$"  # Clip ID regex


# Configure logging - will be reconfigured after cache paths are set
logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure logging with rotating file handler in cache directory.

    Sets up console and rotating file logging with proper formatting.
    Must be called after cache paths are initialized.
    """
    # Clear any existing handlers
    logger.handlers.clear()
    logging.getLogger().handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Rotating file handler in cache directory
    from logging.handlers import RotatingFileHandler

    log_file_path = Path(CACHE_DIR) / Config.LOG_FILE
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=Config.LOG_MAX_BYTES,
        backupCount=Config.LOG_BACKUP_COUNT,
    )
    file_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(
        logging.INFO
    )  # Default level, will be overridden by command line
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Force rotation on startup
    file_handler.doRollover()


def validate_string_input(value: str, max_length: int, field_name: str) -> str:
    """Validate string input for length and basic safety.

    Args:
        value: Input string to validate
        max_length: Maximum allowed length
        field_name: Name of field for error messages

    Returns:
        Validated and stripped string

    Raises:
        ValueError: If validation fails
    """
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} cannot be empty")

    if len(value) > max_length:
        raise ValueError(f"{field_name} too long (max {max_length} characters)")

    # Basic XSS prevention
    if "<" in value or ">" in value or "&" in value:
        raise ValueError(f"{field_name} contains invalid characters")

    return value


def create_api_response(
    success: bool = True,
    data: Any = None,
    error: Optional[str] = None,
    status_code: int = 200,
) -> Tuple[ApiResponse, int]:
    """Create standardized API response format.

    Args:
        success: Whether the operation was successful
        data: Response data (for successful operations)
        error: Error message (for failed operations)
        status_code: HTTP status code

    Returns:
        Tuple of (response_dict, status_code)
    """
    response: ApiResponse = {
        "success": success,
        "timestamp": datetime.now().isoformat(),
        "data": data if success else None,
        "error": error if not success else None,
    }

    return response, status_code


def find_camera_by_id(camera_id: CameraId) -> Optional[BlinkCamera]:
    """Find camera by ID across all sync modules.

    Args:
        camera_id: Camera ID to search for

    Returns:
        Camera object if found, None otherwise
    """
    if blink is None or not blink.available:
        return None

    for sync_name, sync in blink.sync.items():
        for cam_name, cam in sync.cameras.items():
            if str(cam.camera_id) == str(camera_id):
                return cam
    return None


def handle_api_error(
    error: Exception, operation: str, status_code: int = 500
) -> Tuple[ApiResponse, int]:
    """Handle API errors consistently.

    Args:
        error: Exception that occurred
        operation: Description of operation that failed
        status_code: HTTP status code to return

    Returns:
        Standardized error response tuple
    """
    logger.error(f"Error {operation}: {error}")
    return create_api_response(success=False, error=str(error), status_code=status_code)


def require_blink() -> Optional[Tuple[ApiResponse, int]]:
    """Check if Blink is available, return error response if not.

    Returns:
        None if Blink is available, error response tuple if not
    """
    if blink is None or not blink.available:
        return create_api_response(
            success=False, error="Blink not available", status_code=500
        )
    return None


def require_camera(
    camera_id: CameraId,
) -> Tuple[Optional[BlinkCamera], Optional[Tuple[ApiResponse, int]]]:
    """Find camera by ID, return error response if not found.

    Args:
        camera_id: Camera ID to find

    Returns:
        Tuple of (camera, error_response). One will be None.
    """
    camera = find_camera_by_id(camera_id)
    if camera is None:
        error_response = create_api_response(
            success=False, error="Camera not found", status_code=404
        )
        return None, error_response
    return camera, None


def require_sync_module(
    network_id: NetworkId,
) -> Tuple[Optional[BlinkSync], Optional[Tuple[ApiResponse, int]]]:
    """Find sync module by network ID, return error response if not found.

    Args:
        network_id: Network ID to find

    Returns:
        Tuple of (sync_module, error_response). One will be None.
    """
    for name, sync in blink.sync.items():
        if str(sync.network_id) == str(network_id):
            return sync, None

    error_response = create_api_response(
        success=False, error="System not found", status_code=404
    )
    return None, error_response


def parse_clip_id(
    clip_id_str: str,
) -> Tuple[Optional[ClipId], Optional[Tuple[ApiResponse, int]]]:
    """Parse and validate clip ID from URL parameter.

    Args:
        clip_id_str: URL-encoded clip ID string

    Returns:
        Tuple of (clip_id, error_response). One will be None.
    """
    try:
        from urllib.parse import unquote

        clip_id_str = unquote(clip_id_str)
        clip_id = ClipId(clip_id_str)
        return clip_id, None
    except ValueError as e:
        error_response = create_api_response(
            success=False, error=str(e), status_code=400
        )
        return None, error_response


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", Config.SECRET_KEY)
# app.config["REDIS_URL"] = "redis://localhost:6379"  # No longer needed

# HTTP session with connection pooling
http_session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)
adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
http_session.mount("http://", adapter)
http_session.mount("https://", adapter)

# Standard thread management
executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="blink-bg-")

# Stream management
stream_config = StreamConfig(
    segment_time=Config.HLS_SEGMENT_TIME,
    list_size=Config.HLS_LIST_SIZE,
    timeout=Config.FFMPEG_TIMEOUT,
    idle_timeout=Config.STREAM_IDLE_TIMEOUT,
)
stream_manager = StreamManager(stream_config)

# Blink connection and SSE imports moved to top
blink_connection = BlinkConnection(Config.BLINK_OPERATION_TIMEOUT)
blink: Optional[Blink] = None
# Cache configuration - will be set from command line
CACHE_DIR = "cache"  # Default cache directory, overridden by Flask config
CREDENTIALS_FILE = None  # Path to encrypted credentials file, set in get_cache_paths()
THUMBNAIL_CACHE_DIR = None  # Directory for cached thumbnails, set in get_cache_paths()
CLIPS_CACHE_DIR = None  # Directory for cached clips, set in get_cache_paths()

# Standard cache instances using cachetools
thumbnail_cache = ThreadSafeCache(LRUCache(maxsize=Config.THUMBNAIL_CACHE_SIZE))
clips_metadata_cache = ThreadSafeCache(
    LRUCache(maxsize=Config.CLIPS_METADATA_CACHE_SIZE)
)
clips_download_cache = ThreadSafeCache(LRUCache(maxsize=Config.CLIPS_CACHE_SIZE))


def initialize_cache_paths() -> None:
    """Initialize cache directory paths from Flask config or defaults.

    Sets global path variables for cache directories and credential file.
    Uses Flask app config 'CACHE_DIR' or defaults to 'cache'.

    Side Effects:
        Updates global variables: CACHE_DIR, CREDENTIALS_FILE,
        THUMBNAIL_CACHE_DIR, CLIPS_CACHE_DIR
    """
    global CACHE_DIR, CREDENTIALS_FILE, THUMBNAIL_CACHE_DIR, CLIPS_CACHE_DIR
    cache_dir = Path(app.config.get("CACHE_DIR", "cache"))
    CACHE_DIR = str(cache_dir)
    CREDENTIALS_FILE = str(cache_dir / "blink.json")
    THUMBNAIL_CACHE_DIR = str(cache_dir / "thumbnails")
    CLIPS_CACHE_DIR = str(cache_dir / "clips")


# Legacy cache size constant for reference
CLIPS_CACHE_SIZE = Config.CLIPS_CACHE_SIZE  # Maximum number of clips to cache

# Legacy stream variables removed - now handled by StreamManager

# Blink operations delegated to blink_thread module


async def initialize_blink(
    username: str, password: str
) -> Union[bool, Literal["2fa_required"]]:
    """Initialize Blink system following blinkpy README.

    Args:
        username: Blink account username/email
        password: Blink account password

    Returns:
        True if successful, '2fa_required' if 2FA needed, False if failed
    """
    global blink
    with error_context("initialize Blink system", AuthenticationError):
        blink = Blink()
        blink_connection.blink = blink  # Set reference in connection
        auth = Auth({"username": username, "password": password}, no_prompt=True)
        blink.auth = auth
        await blink.start()

        # Check if 2FA is required
        if blink.key_required:
            logger.info("2FA key required - check your email or SMS")
            return "2fa_required"

        logger.info("Blink system initialized successfully")
        return True


async def verify_2fa_and_save(username: str, password: str, tfa_key: str) -> bool:
    """Verify 2FA code and save credentials in same thread as Blink creation.

    Args:
        username: Blink account username (unused but kept for consistency)
        password: Blink account password (unused but kept for consistency)
        tfa_key: 2FA verification code from email/SMS

    Returns:
        True if verification successful, False otherwise
    """
    global blink
    with error_context("verify 2FA and save credentials", AuthenticationError):
        logger.debug(f"Starting 2FA verification with key: {tfa_key[:2]}***")

        # Send 2FA key using same session/thread
        logger.debug("Sending 2FA key...")
        await blink.auth.send_auth_key(blink, tfa_key)

        logger.debug("Setting up post verification...")
        await blink.setup_post_verify()

        logger.debug("Saving credentials...")
        await blink.save(CREDENTIALS_FILE)

        logger.info("2FA verification and save completed successfully")
        return True


def extract_thumbnail_timestamp(thumbnail_url: Optional[str]) -> int:
    """Extract timestamp from thumbnail URL.

    Args:
        thumbnail_url: URL containing ts parameter

    Returns:
        Timestamp as integer, 0 if not found
    """
    if not thumbnail_url:
        return 0
    try:
        import re

        match = re.search(r"ts=([0-9]+)", thumbnail_url)
        return int(match.group(1)) if match else 0
    except Exception:
        return 0


def create_device_data(
    camera: BlinkCamera, cache_key: CameraId, current_ts: int, cached_ts: int
) -> Dict[str, Any]:
    """Create device data dictionary for camera.

    Args:
        camera: Camera object from blinkpy
        cache_key: Validated camera ID
        current_ts: Current thumbnail timestamp
        cached_ts: Cached thumbnail timestamp

    Returns:
        Device data dictionary for API response
    """
    # Format last updated time
    display_ts = max(cached_ts, current_ts)
    last_updated = "Never"
    if display_ts > 0:
        try:
            thumbnail_time = datetime.fromtimestamp(display_ts)
            now = datetime.now()
            diff = now - thumbnail_time
            days = diff.days
            if days == 0:
                hours = diff.seconds // 3600
                if hours == 0:
                    minutes = diff.seconds // 60
                    last_updated = f"{minutes}m ago"
                else:
                    last_updated = f"{hours}h ago"
            else:
                last_updated = f"{days}d ago"
        except Exception:
            last_updated = (
                format_time_ago(camera.last_record) if camera.last_record else "Never"
            )

    return {
        "type": "camera",
        "name": camera.name,
        "id": camera.camera_id,
        "thumbnail": f"/api/media/thumbnail/{camera.camera_id}",
        "last_updated": last_updated,
        "motion_enabled": camera.motion_enabled,
        "battery": camera.battery,
        "temperature": camera.temperature,
        "wifi_strength": camera.wifi_strength,
    }


def update_camera_thumbnail(
    camera: BlinkCamera, cache_key: CameraId, current_ts: int, cached_ts: int
) -> None:
    """Update camera thumbnail in background if needed.

    Args:
        camera: Camera object from blinkpy
        cache_key: Validated camera ID
        current_ts: Current thumbnail timestamp
        cached_ts: Cached thumbnail timestamp
    """
    if current_ts <= cached_ts:
        return

    logger.debug(
        f"Updating thumbnail cache for {camera.name} (ts: {current_ts} > {cached_ts})"
    )

    def update_thumbnail():
        # Double-check timestamp to prevent race condition
        current_entry = thumbnail_cache.get(cache_key)
        current_cached_ts = current_entry.get("timestamp", 0) if current_entry else 0
        if current_ts <= current_cached_ts:
            logger.debug(f"Thumbnail already updated for {camera.name}, skipping")
            return

        # Remove old cached file if exists
        old_entry = thumbnail_cache.get(cache_key)
        if old_entry:
            old_filename = old_entry.get("filename")
            if old_filename:
                old_filepath = Path(THUMBNAIL_CACHE_DIR) / old_filename
                try:
                    if old_filepath.exists():
                        old_filepath.unlink()
                        logger.debug(f"Removed old thumbnail file: {old_filename}")
                except OSError as e:
                    logger.debug(f"Could not remove old thumbnail: {e}")

        thumbnail_response = blink_connection.execute(camera.get_thumbnail())
        if thumbnail_response and thumbnail_response.status == 200:
            image_data = blink_connection.execute(thumbnail_response.read())

            # Save to file with new timestamp
            filename = f"{cache_key}_{current_ts}.jpg"
            filepath = Path(THUMBNAIL_CACHE_DIR) / filename
            try:
                filepath.write_bytes(image_data)
                # Update cache info atomically
                thumbnail_cache[cache_key] = {
                    "timestamp": current_ts,
                    "filename": filename,
                }
                logger.debug(
                    f"Cached thumbnail for {camera.name} with timestamp {current_ts}"
                )
            except OSError as e:
                logger.error(f"Failed to write thumbnail file {filepath}: {e}")

    executor.submit(update_thumbnail)


def process_cloud_clips(videos_metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process cloud storage clips into day-grouped format.

    Args:
        videos_metadata: Raw video metadata from Blink API

    Returns:
        List of day groups with clips
    """
    clips_by_day = {}
    for video in videos_metadata:
        try:
            created_at = datetime.fromisoformat(
                video["created_at"].replace("Z", "+00:00")
            )
            day_key = created_at.strftime("%Y-%m-%d")

            if day_key not in clips_by_day:
                clips_by_day[day_key] = {
                    "date": created_at.strftime("%B %d, %Y"),
                    "clips": [],
                }

            clip_id = ClipId(str(video.get("id")))
            thumbnail_url = video.get("thumbnail")

            # Check if we have a cached thumbnail for cloud clips
            cached_clip = clips_download_cache.get(clip_id)
            if cached_clip is not None:
                cached_thumbnail = cached_clip.get("thumbnail")
                if cached_thumbnail and cached_thumbnail.exists():
                    thumbnail_url = f"/api/clip/{clip_id}/thumbnail"

            clips_by_day[day_key]["clips"].append(
                {
                    "id": str(clip_id),
                    "camera_name": video.get("device_name", "Unknown"),
                    "system_name": Config.DEFAULT_SYSTEM_NAME,
                    "time": created_at.astimezone().strftime("%I:%M %p"),
                    "event_type": "Motion",
                    "thumbnail": thumbnail_url,
                    "media_url": video.get("media"),
                }
            )
        except Exception as e:
            logger.warning(f"Skipping invalid video metadata: {e}")
            continue

    return format_clips_by_day(clips_by_day)


def process_local_clips() -> List[Dict[str, Any]]:
    """Process local storage clips into day-grouped format.

    Returns:
        List of day groups with clips
    """
    clips_by_day = {}

    for sync_name, sync_module in blink.sync.items():
        try:
            # Refresh sync module to update local storage manifest
            blink_connection.execute(sync_module.refresh())

            # Get clips from local storage manifest if ready
            if sync_module.local_storage and sync_module.local_storage_manifest_ready:
                manifest = sync_module._local_storage["manifest"]
                for item in manifest:
                    try:
                        created_at = item.created_at
                        day_key = created_at.strftime("%Y-%m-%d")

                        if day_key not in clips_by_day:
                            clips_by_day[day_key] = {
                                "date": created_at.strftime("%B %d, %Y"),
                                "clips": [],
                            }

                        clip_id = ClipId.from_local(sync_name, item.id)
                        logger.debug(
                            f"Created local clip ID: {clip_id} from sync: {sync_name}, item: {item.id}"
                        )

                        # Check for existing thumbnail only
                        thumbnail_url = None
                        cached_clip = clips_download_cache.get(clip_id)
                        if cached_clip is not None:
                            cached_thumbnail = cached_clip.get("thumbnail")
                            if cached_thumbnail and cached_thumbnail.exists():
                                thumbnail_url = f"/api/clip/{clip_id}/thumbnail"

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


def format_clips_by_day(
    clips_by_day: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Format clips by day into sorted list.

    Args:
        clips_by_day: Dictionary of clips grouped by day

    Returns:
        Sorted list of day groups
    """
    clips = []
    for day_key in sorted(clips_by_day.keys(), reverse=True):
        day_data = clips_by_day[day_key]
        day_data["clips"].sort(key=lambda x: x["time"], reverse=True)
        day_data["count"] = len(day_data["clips"])
        clips.append(day_data)
    return clips


def format_time_ago(timestamp_str: Optional[Union[str, int]]) -> str:
    """Format timestamp as 'Xd ago' format.

    Args:
        timestamp_str: ISO format timestamp string or None

    Returns:
        Formatted time string like '5d ago', '2h ago', '30m ago', or 'Unknown'
    """
    try:
        if timestamp_str is None:
            return "Unknown"
        # Parse the timestamp
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(timestamp.tzinfo)
        diff = now - timestamp
        days = diff.days
        if days == 0:
            hours = diff.seconds // 3600
            if hours == 0:
                minutes = diff.seconds // 60
                return f"{minutes}m ago"
            return f"{hours}h ago"
        return f"{days}d ago"
    except Exception:
        return "Unknown"


@app.route("/")
def index() -> Response:
    """Main page - redirect to login if not authenticated.

    Returns:
        Redirect to login page or rendered index template
    """
    if "authenticated" not in session:
        # Check if Blink is available from saved credentials
        if blink and blink.available:
            session["authenticated"] = True
        else:
            return redirect(url_for("login"))
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login() -> Response:
    """Handle login page GET/POST requests.

    Returns:
        Login form template or redirect based on authentication result
    """
    if request.method == "POST":
        try:
            username = validate_string_input(
                request.form.get("username", ""), Config.MAX_USERNAME_LENGTH, "Username"
            )
            password = validate_string_input(
                request.form.get("password", ""), Config.MAX_PASSWORD_LENGTH, "Password"
            )
        except ValueError as e:
            return render_template("login.html", error=str(e))

        # Initialize Blink thread if needed
        blink_connection.start()

        try:
            success = blink_connection.execute(initialize_blink(username, password))

            if success == "2fa_required":
                session["temp_username"] = username
                session["temp_password"] = password
                return redirect(url_for("two_factor"))
            elif success:
                blink_connection.execute(blink.save(CREDENTIALS_FILE))
                session["authenticated"] = True
                return redirect(url_for("index"))
            else:
                return render_template("login.html", error="Invalid credentials")
        except AuthenticationError as e:
            return render_template("login.html", error=str(e))
        except Exception as e:
            logger.error(f"Unexpected login error: {e}")
            return render_template(
                "login.html", error="Login failed. Please try again."
            )

    return render_template("login.html")


@app.route("/2fa", methods=["GET", "POST"])
def two_factor() -> Response:
    """Handle 2FA verification page GET/POST requests.

    Returns:
        2FA form template or redirect based on verification result
    """
    if "temp_username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        try:
            key = validate_string_input(
                request.form.get("key", ""), Config.MAX_TFA_LENGTH, "2FA code"
            )
            username = session["temp_username"]
            password = session["temp_password"]
        except ValueError as e:
            return render_template(
                "2fa.html", error=str(e), email=session.get("temp_username", "")
            )

        try:
            logger.debug("Running 2FA verification in Blink thread")
            success = blink_connection.execute(
                verify_2fa_and_save(username, password, key)
            )

            if success:
                logger.debug("2FA successful, clearing session and redirecting")
                session.pop("temp_username", None)
                session.pop("temp_password", None)
                session["authenticated"] = True
                return redirect(url_for("index"))
            else:
                logger.debug("2FA failed, showing error")
                return render_template("2fa.html", error="Invalid 2FA code")
        except AuthenticationError as e:
            return render_template("2fa.html", error=str(e))
        except Exception as e:
            logger.error(f"Unexpected 2FA error: {e}")
            return render_template("2fa.html", error="2FA verification failed")

    return render_template("2fa.html", email=session.get("temp_username", ""))


def clear_all_caches():
    """Clear all caches except credentials (background operation)."""
    with error_context("clear cache", CacheError):
        # Clear memory caches first (fast operation)
        thumbnail_cache.clear()
        clips_download_cache.clear()
        clips_metadata_cache.clear()

        # Clear file caches (slow I/O operations)
        def clear_file_cache(cache_dir, cache_name):
            try:
                if os.path.exists(cache_dir):
                    import shutil

                    shutil.rmtree(cache_dir)
                    os.makedirs(cache_dir, exist_ok=True)
                    logger.debug(f"Cleared {cache_name} directory")
            except OSError as e:
                logger.warning(f"Could not clear {cache_name} directory: {e}")

        # Execute file operations in parallel
        thumbnail_future = executor.submit(
            clear_file_cache, THUMBNAIL_CACHE_DIR, "thumbnail"
        )
        clips_future = executor.submit(clear_file_cache, CLIPS_CACHE_DIR, "clips")

        # Wait for completion with timeout
        try:
            thumbnail_future.result(timeout=Config.CACHE_CLEAR_TIMEOUT)
            clips_future.result(timeout=Config.CACHE_CLEAR_TIMEOUT)
            logger.info("All caches cleared successfully")
        except Exception as e:
            logger.warning(f"Cache clearing completed with errors: {e}")


@app.route("/api/clear-cache", methods=["POST"])
def clear_cache():
    """Clear all caches except credentials."""
    executor.submit(clear_all_caches)
    response, status_code = create_api_response(
        success=True, data={"message": "Cache clearing initiated"}
    )
    return jsonify(response), status_code


@app.route("/logout", methods=["POST"])
def logout() -> Response:
    """Logout user and clear all credentials and caches.

    Returns:
        JSON response indicating success
    """
    global blink

    # Clear caches first in background
    executor.submit(clear_all_caches)

    # Clear session and credentials
    session.clear()
    blink = None
    cred_file = Path(CREDENTIALS_FILE)
    if cred_file.exists():
        cred_file.unlink()

    response, status_code = create_api_response(
        success=True, data={"message": "Logged out successfully"}
    )
    return jsonify(response), status_code


@app.route("/api/systems")
def get_systems() -> Response:
    """Get list of available Blink systems.

    Returns:
        JSON response with list of systems or error message
    """
    error_response = require_blink()
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code

    with error_context("get systems"):
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

        response, status_code = create_api_response(success=True, data=systems)
        return jsonify(response), status_code


@app.route("/api/devices/<network_id_str>")
def get_devices(network_id_str: str) -> Response:
    try:
        network_id = NetworkId(network_id_str)
    except ValueError as e:
        response, status_code = create_api_response(
            success=False, error=str(e), status_code=400
        )
        return jsonify(response), status_code
    """Get devices for a specific Blink system.

    Args:
        network_id: Network ID of the Blink system

    Returns:
        JSON response with list of devices or error message
    """
    error_response = require_blink()
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code

    devices = []

    # Find the sync module for this network
    sync_module, error_response = require_sync_module(network_id)
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code

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

    response, status_code = create_api_response(success=True, data=devices)
    return jsonify(response), status_code


@app.route("/api/system/<network_id_str>/arm", methods=["POST"])
def arm_system(network_id_str: str) -> Response:
    try:
        network_id = NetworkId(network_id_str)
    except ValueError as e:
        response, status_code = create_api_response(
            success=False, error=str(e), status_code=400
        )
        return jsonify(response), status_code
    """Arm or disarm a Blink system.

    Args:
        network_id: Network ID of the system to arm/disarm

    Returns:
        JSON response with success status or error message
    """
    error_response = require_blink()
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code

    try:
        data = request.get_json()
        if not isinstance(data, dict):
            response, status_code = create_api_response(
                success=False, error="Invalid JSON data", status_code=400
            )
            return jsonify(response), status_code

        armed = data.get("armed")
        if not isinstance(armed, bool):
            response, status_code = create_api_response(
                success=False, error="Armed status must be boolean", status_code=400
            )
            return jsonify(response), status_code
    except Exception:
        response, status_code = create_api_response(
            success=False, error="Invalid request data", status_code=400
        )
        return jsonify(response), status_code

    # Find the sync module
    sync_module, error_response = require_sync_module(network_id)
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code

    with error_context("arm/disarm system"):
        blink_connection.execute(sync_module.async_arm(armed))
        response, status_code = create_api_response(success=True, data={"armed": armed})
        return jsonify(response), status_code


@app.route("/api/camera/<camera_id_str>/refresh", methods=["POST"])
def refresh_camera(camera_id_str: str):
    try:
        camera_id = CameraId(camera_id_str)
    except ValueError as e:
        response, status_code = create_api_response(
            success=False, error=str(e), status_code=400
        )
        return jsonify(response), status_code

    """Refresh camera thumbnail."""
    error_response = require_blink()
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code

    camera, error_response = require_camera(camera_id)
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code

    with error_context("refresh camera thumbnail", CameraError):
        # Remove camera thumbnail from cache in background
        def remove_thumbnail_cache():
            cache_key = CameraId(camera.camera_id)
            cached_info = thumbnail_cache.get(cache_key)
            if cached_info is not None:
                # Remove cached file
                if "filename" in cached_info:
                    cached_file = Path(THUMBNAIL_CACHE_DIR) / cached_info["filename"]
                    try:
                        if cached_file.exists():
                            cached_file.unlink()
                    except OSError as e:
                        logger.debug(f"Could not remove cached thumbnail: {e}")
                # Remove from cache
                thumbnail_cache.pop(cache_key, None)

        executor.submit(remove_thumbnail_cache)

        blink_connection.execute(camera.snap_picture())
        response, status_code = create_api_response(
            success=True, data={"message": "Thumbnail refresh initiated"}
        )
        return jsonify(response), status_code


@app.route("/api/clips")
def get_clips():
    """Get clips from cloud or local storage."""
    error_response = require_blink()
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code

    storage_type = request.args.get("storage", "cloud")
    if storage_type not in ["cloud", "local"]:
        response, status_code = create_api_response(
            success=False,
            error='Invalid storage type. Must be "cloud" or "local"',
            status_code=400,
        )
        return jsonify(response), status_code

    # Check cache first for performance
    cache_key = storage_type
    cached_clips = clips_metadata_cache.get(cache_key)
    if cached_clips is not None:
        response, status_code = create_api_response(success=True, data=cached_clips)
        return jsonify(response), status_code

    with error_context(f"get {storage_type} clips"):
        if storage_type == "cloud":
            # Get cloud clips via blink operation
            videos_metadata = blink_connection.execute(
                blink.get_videos_metadata(stop=Config.CLIPS_PER_STORAGE_TYPE)
            )
            clips = process_cloud_clips(videos_metadata)
        else:
            clips = process_local_clips()

    # Cache the results
    clips_metadata_cache[storage_type] = clips

    response, status_code = create_api_response(success=True, data=clips)
    return jsonify(response), status_code


@app.route("/api/refresh", methods=["POST"])
def refresh_system():
    """Manually refresh the Blink system."""
    error_response = require_blink()
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code

    try:
        success = blink_connection.execute(blink.refresh(force=True))

        if success is True:
            response, status_code = create_api_response(
                success=True, data={"message": "System refreshed successfully"}
            )
            return jsonify(response), status_code
        else:
            response, status_code = create_api_response(
                success=False, error="Failed to refresh system", status_code=500
            )
            return jsonify(response), status_code
    except Exception as e:
        logger.error(f"Error refreshing system: {e}")
        response, status_code = create_api_response(
            success=False, error=str(e), status_code=500
        )
        return jsonify(response), status_code


@app.route("/api/clip/<clip_id_str>/download")
def download_clip(clip_id_str: str):
    clip_id, error_response = parse_clip_id(clip_id_str)
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code
    """Download a specific clip."""
    error_response = require_blink()
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code

    try:
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
    except Exception as e:
        logger.error(f"Error downloading clip {clip_id}: {e}")
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        response, status_code = create_api_response(
            success=False, error=str(e), status_code=500
        )
        return jsonify(response), status_code


def _download_clip_common(
    clip_id: ClipId, filepath: Path, filename: str, middle_frame: bool = False
) -> Response:
    """Common clip download logic after file is downloaded."""
    # Cache the clip first (without thumbnail)
    clips_download_cache[clip_id] = {
        "filepath": filepath,
        "thumbnail": None,
    }

    # Generate thumbnail in background
    def generate_thumbnail_bg():
        thumbnail_path = generate_clip_thumbnail(
            filepath, filename, middle_frame=middle_frame
        )
        if thumbnail_path:
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
    return send_file(str(filepath), as_attachment=True, download_name=filename)


def download_cloud_clip(clip_id: ClipId) -> Response:
    """Download cloud storage clip."""
    # Check if already cached
    cached_clip = clips_download_cache.get(clip_id)
    if cached_clip is not None:
        try:
            # Quick existence check - if it fails, we'll re-download
            if cached_clip["filepath"].exists():
                return send_file(str(cached_clip["filepath"]), as_attachment=True)
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
        response, status_code = create_api_response(
            success=False, error="Clip not found", status_code=404
        )
        return jsonify(response), status_code

    # Generate filename
    created_at = datetime.fromisoformat(clip_info["created_at"].replace("Z", "+00:00"))
    camera_name = clip_info.get("device_name", "unknown")
    iso_date = created_at.strftime("%Y-%m-%dT%H-%M-%S")
    filename = f"{clip_id}_{camera_name}_{iso_date}.mp4"
    filepath = Path(CLIPS_CACHE_DIR) / filename

    # Download if not cached
    if not filepath.exists():
        media_url = clip_info.get("media")
        if media_url is None:
            response, status_code = create_api_response(
                success=False, error="No media URL found", status_code=404
            )
            return jsonify(response), status_code

        # Download in executor to avoid blocking
        def download_file():
            try:
                response = http_session.get(media_url, timeout=Config.HTTP_TIMEOUT)
                if response.status_code == 200:
                    filepath.write_bytes(response.content)
                    return True
                else:
                    logger.error(
                        f"HTTP {response.status_code} downloading clip {clip_id}"
                    )
                    return False
            except Exception as e:
                logger.error(f"Error downloading clip {clip_id}: {e}")
                return False

        # Execute download synchronously since we need the file immediately
        future = executor.submit(download_file)
        try:
            success = future.result(timeout=Config.DOWNLOAD_TIMEOUT)
            if not success:
                response, status_code = create_api_response(
                    success=False, error="Failed to download clip", status_code=500
                )
                return jsonify(response), status_code
        except Exception as e:
            logger.error(f"Download timeout or error for clip {clip_id}: {e}")
            response, status_code = create_api_response(
                success=False, error="Download failed or timed out", status_code=500
            )
            return jsonify(response), status_code

    return _download_clip_common(clip_id, filepath, filename, middle_frame=False)


def download_local_clip(clip_id: ClipId, sync_name: str, item_id: int) -> Response:
    """Download local storage clip using blinkpy methods."""
    # Check if already cached
    cached_clip = clips_download_cache.get(clip_id)
    if cached_clip is not None:
        try:
            # Quick existence check - if it fails, we'll re-download
            if cached_clip["filepath"].exists():
                return send_file(str(cached_clip["filepath"]), as_attachment=True)
        except (OSError, AttributeError):
            # File doesn't exist or path is invalid, continue to download
            pass

    # Find sync module and clip item
    sync_module = blink.sync.get(sync_name)
    if sync_module is None:
        response, status_code = create_api_response(
            success=False, error="Sync module not found", status_code=404
        )
        return jsonify(response), status_code

    if not sync_module.local_storage or not sync_module.local_storage_manifest_ready:
        response, status_code = create_api_response(
            success=False, error="Local storage not available", status_code=404
        )
        return jsonify(response), status_code

    manifest = sync_module._local_storage["manifest"]
    item = next((i for i in manifest if i.id == item_id), None)
    if item is None:
        response, status_code = create_api_response(
            success=False, error="Local clip not found", status_code=404
        )
        return jsonify(response), status_code

    # Generate filename
    iso_date = item.created_at.strftime("%Y-%m-%dT%H-%M-%S")
    filename = f"{clip_id}_{item.name}_{iso_date}.mp4"
    filepath = Path(CLIPS_CACHE_DIR) / filename

    # Download if not cached
    if not filepath.exists():
        try:
            blink_connection.execute(item.prepare_download(blink))
            success = blink_connection.execute(
                item.download_video(blink, str(filepath))
            )
            if success is not True:
                response, status_code = create_api_response(
                    success=False,
                    error="Failed to download local clip",
                    status_code=500,
                )
                return jsonify(response), status_code
        except Exception as e:
            logger.error(f"Error downloading local clip: {e}")
            response, status_code = create_api_response(
                success=False, error=f"Download failed: {str(e)}", status_code=500
            )
            return jsonify(response), status_code

    return _download_clip_common(clip_id, filepath, filename, middle_frame=True)


# Stream management functions moved to StreamManager class


@app.route("/api/camera/<camera_id_str>/liveview")
def get_camera_liveview(camera_id_str: str):
    try:
        camera_id = CameraId(camera_id_str)
    except ValueError as e:
        response, status_code = create_api_response(
            success=False, error=str(e), status_code=400
        )
        return jsonify(response), status_code

    """Get live view stream for camera."""
    error_response = require_blink()
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code

    camera, error_response = require_camera(camera_id)
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code

    try:
        # Get RTSP stream URL via blink operation
        rtsp_url = blink_connection.execute(camera.get_liveview())

        if rtsp_url is not None:
            # Start HLS transcoding
            hls_url, error_msg = stream_manager.start_stream(str(camera_id), rtsp_url)
            if hls_url is not None:
                response, status_code = create_api_response(
                    success=True, data={"rtsp_url": rtsp_url, "hls_url": hls_url}
                )
                return jsonify(response), status_code
            else:
                response, status_code = create_api_response(
                    success=False,
                    error=f"Failed to start HLS transcoding: {error_msg}",
                    status_code=500,
                )
                return jsonify(response), status_code
        else:
            response, status_code = create_api_response(
                success=False, error="Failed to get live view URL", status_code=500
            )
            return jsonify(response), status_code
    except Exception as e:
        response, status_code = handle_api_error(
            e, f"getting live view for camera {camera_id}"
        )
        return jsonify(response), status_code


@app.route("/api/hls/<camera_id_str>/<path:filename>")
def serve_hls_file(camera_id_str: str, filename: str):
    """Serve HLS playlist and segment files."""
    file_path = stream_manager.get_stream_file(camera_id_str, filename)

    if file_path is None:
        response, status_code = create_api_response(
            success=False, error="Stream or file not found", status_code=404
        )
        return jsonify(response), status_code

    if filename.endswith(".m3u8"):
        return send_file(str(file_path), mimetype="application/vnd.apple.mpegurl")
    elif filename.endswith(".ts"):
        return send_file(str(file_path), mimetype="video/mp2t")
    else:
        response, status_code = create_api_response(
            success=False, error="Invalid file type", status_code=400
        )
        return jsonify(response), status_code


@app.route("/api/clip/<clip_id_str>/thumbnail")
def get_clip_thumbnail(clip_id_str: str):
    clip_id, error_response = parse_clip_id(clip_id_str)
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code
    """Serve clip thumbnail."""
    cached_clip = clips_download_cache.get(clip_id)
    if cached_clip is not None:
        thumbnail_path = cached_clip.get("thumbnail")
        if thumbnail_path is not None and thumbnail_path.exists():
            return send_file(str(thumbnail_path), mimetype="image/jpeg")

    response, status_code = create_api_response(
        success=False, error="Thumbnail not found", status_code=404
    )
    return jsonify(response), status_code


@app.route("/api/media/thumbnail/<camera_id_str>")
def get_camera_thumbnail(camera_id_str: str):
    try:
        camera_id = CameraId(camera_id_str)
    except ValueError as e:
        response, status_code = create_api_response(
            success=False, error=str(e), status_code=400
        )
        return jsonify(response), status_code

    """Proxy camera thumbnail with authentication."""
    error_response = require_blink()
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code

    camera = find_camera_by_id(camera_id)
    if camera is None or camera.thumbnail is None:
        response, status_code = create_api_response(
            success=False, error="Camera or thumbnail not found", status_code=404
        )
        return jsonify(response), status_code

    try:
        # Check cache first
        cached_thumbnail = thumbnail_cache.get(camera_id)
        if cached_thumbnail is not None:
            logger.debug(f"Serving cached thumbnail for camera {camera_id}")
            filename = cached_thumbnail["filename"]
            filepath = Path(THUMBNAIL_CACHE_DIR) / filename
            if filepath.exists():
                response = send_file(str(filepath), mimetype="image/jpeg")
                response.headers["Cache-Control"] = (
                    "no-cache, no-store, must-revalidate"
                )
                return response

        # If not cached, fetch via blink operation
        response = blink_connection.execute(camera.get_thumbnail())
        if response is not None and response.status == 200:
            image_data = blink_connection.execute(response.read())
            return FlaskResponse(image_data, mimetype="image/jpeg")
        else:
            response, status_code = create_api_response(
                success=False, error="Failed to fetch thumbnail", status_code=500
            )
            return jsonify(response), status_code
    except Exception as e:
        response, status_code = handle_api_error(
            e, f"fetching thumbnail for camera {camera_id}"
        )
        return jsonify(response), status_code


# SSE blueprint removed - using polling approach instead


def notify_thumbnail_ready(clip_id: ClipId) -> None:
    """Thumbnail ready notification (no longer needed with polling approach)."""
    logger.debug(f"Thumbnail ready for clip: {clip_id}")


@app.route("/placeholder")
def placeholder():
    """Show placeholder message."""
    response, status_code = create_api_response(
        success=False, error="This feature is not yet available", status_code=501
    )
    return jsonify(response), status_code


async def load_saved_blink():
    """Load Blink system from saved credentials file."""
    global blink
    cred_file = Path(CREDENTIALS_FILE)
    if cred_file.exists():
        try:
            from blinkpy.helpers.util import json_load

            auth_data = await json_load(CREDENTIALS_FILE)
            auth = Auth(auth_data)
            blink = Blink(session=None)
            blink.auth = auth
            success = await blink.start()
            if success is True:
                logger.info("Blink system loaded from saved credentials")
                return True
            else:
                logger.warning(
                    "Failed to load Blink system from saved credentials - removing invalid file"
                )
                cred_file.unlink()
                return False
        except Exception as e:
            logger.warning(
                f"Could not load Blink system from saved credentials: {e} - removing invalid file"
            )
            if cred_file.exists():
                cred_file.unlink()
            return False
    return False


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
    try:
        # Initialize cache paths
        initialize_cache_paths()

        # Create cache directories if they don't exist
        Path(CACHE_DIR).mkdir(exist_ok=True)
        Path(THUMBNAIL_CACHE_DIR).mkdir(exist_ok=True)
        Path(CLIPS_CACHE_DIR).mkdir(exist_ok=True)

        # Setup logging with rotation in cache directory
        setup_logging()

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
        except Exception as e:
            logger.error(f"Error loading saved Blink credentials: {e}")
            # Clear invalid credentials file
            cred_file = Path(CREDENTIALS_FILE)
            if cred_file.exists():
                cred_file.unlink()
                logger.info("Removed invalid credentials file")
    except Exception as e:
        logger.warning(f"Could not initialize Blink system on startup: {e}")


def generate_clip_thumbnail(
    video_path: Path, filename: str, middle_frame: bool = False
) -> Optional[Path]:
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
    thumbnail_path = Path(CLIPS_CACHE_DIR) / thumbnail_filename

    if thumbnail_path.exists():
        return thumbnail_path

    try:
        import subprocess

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
    cache_dir = Path(THUMBNAIL_CACHE_DIR)
    if not cache_dir.exists():
        return

    try:
        # Get valid camera IDs from current system
        valid_camera_ids = set()
        if blink and blink.available:
            for sync_name, sync in blink.sync.items():
                for cam_name, cam in sync.cameras.items():
                    valid_camera_ids.add(cam.camera_id)

        # Group thumbnails by camera ID
        camera_thumbnails = {}
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
        def remove_files(files_list):
            for file_path in files_list:
                try:
                    file_path.unlink()
                    logger.debug(f"Removed invalid thumbnail: {file_path.name}")
                except Exception as e:
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
    cache_dir = Path(CLIPS_CACHE_DIR)
    if not cache_dir.exists():
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
                                blink.get_videos_metadata(stop=50)
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
        def remove_files(files_list):
            for file_path in files_list:
                try:
                    file_path.unlink()
                    logger.debug(f"Removed invalid cached file: {file_path.name}")
                except Exception as e:
                    logger.warning(f"Could not remove file {file_path}: {e}")

        if files_to_remove:
            executor.submit(remove_files, files_to_remove)

    except Exception as e:
        logger.error(f"Error scanning clips cache: {e}")


# Removed generate_thumbnail_async - thumbnails only generated on clip download


@app.route("/api/clip/<clip_id_str>/thumbnail/check")
def check_clip_thumbnail(clip_id_str: str):
    """Check if thumbnail is available for clip."""
    clip_id, error_response = parse_clip_id(clip_id_str)
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code

    cached_clip = clips_download_cache.get(clip_id)
    if cached_clip is not None:
        thumbnail_path = cached_clip.get("thumbnail")
        if thumbnail_path is not None and thumbnail_path.exists():
            response, status_code = create_api_response(
                success=True,
                data={"available": True, "url": f"/api/clip/{clip_id}/thumbnail"},
            )
            return jsonify(response), status_code

    response, status_code = create_api_response(success=True, data={"available": False})
    return jsonify(response), status_code


# Stream cleanup functions moved to StreamManager class


def cleanup_resources() -> None:
    """Clean up all resources on application shutdown.

    Stops all active HLS streams and their FFmpeg processes.
    Terminates the Blink event loop gracefully.
    Called automatically on exit via atexit handler and signal handlers.
    """
    logger.info("Cleaning up resources...")

    # Shutdown executor
    executor.shutdown(wait=False)

    # Shutdown stream manager
    stream_manager.shutdown()

    # Shutdown Blink connection
    blink_connection.shutdown()

    # Close HTTP session
    http_session.close()

    logger.info("Resource cleanup completed")


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


# Register cleanup handlers
atexit.register(cleanup_resources)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# LRUCache automatically handles eviction, no manual cleanup needed

# Initialize on startup
startup()


def main() -> None:
    """Main entry point with command line argument parsing."""
    import argparse

    parser = argparse.ArgumentParser(description="Blink Camera Flask Web Interface")
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=5000, help="Port to bind to (default: 5000)"
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
        default="cache",
        help="Cache directory for credentials, thumbnails, and clips (default: cache)",
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

    try:
        app.run(debug=args.debug, host=args.host, port=args.port)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        cleanup_resources()


if __name__ == "__main__":
    main()
