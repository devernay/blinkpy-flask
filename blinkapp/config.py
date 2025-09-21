"""Configuration constants for the Blink Flask application.

This module centralizes all configuration values to avoid circular imports
between app.py and other modules that need configuration constants.
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable as CallableType

# Explicitly define what this module exports
__all__ = [
    "Config",
]


class Config:
    """Application configuration constants.

    Centralizes all configuration values for the Blink Flask application
    to avoid circular imports and provide a single source of truth for
    all settings. This includes cache settings, timeouts, validation
    patterns, limits, and UI timing constants.

    The configuration is organized into logical groups:
    - Server and networking settings
    - Cache and storage configuration
    - Media processing (FFmpeg) settings
    - API limits and timeouts
    - UI polling and timing
    - HTTP status codes and retry logic
    - File paths and naming conventions

    All timeout values are in seconds unless otherwise specified.
    All UI timing values are in milliseconds for JavaScript frontend.
    """

    # ========================================================================
    # Testing Configuration
    # ========================================================================
    TESTING_MODE: bool = False  # Enable testing mode (no external API calls)

    # ========================================================================
    # Server Configuration
    # ========================================================================
    DEFAULT_HOST = "0.0.0.0"  # Default host to bind to (all interfaces)
    DEFAULT_PORT = 5001  # Default port to bind to (avoid conflicts with 5000)
    DEFAULT_CACHE_DIR = "cache"  # Default cache directory name (relative to app)

    # ========================================================================
    # Cache Configuration
    # ========================================================================
    # Memory cache sizes (number of items before LRU eviction)
    CLIPS_CACHE_SIZE = 100  # Maximum downloaded clips in cache
    CLIPS_METADATA_CACHE_SIZE = 1000  # Maximum clips metadata entries in cache
    THUMBNAIL_CACHE_SIZE = 100  # Maximum camera thumbnail entries in cache

    # Cache file and directory names (relative to cache directory)
    CREDENTIALS_FILENAME = "blink.json"  # Encrypted credentials file
    SETTINGS_FILENAME = "settings.json"  # User settings persistence file
    THUMBNAILS_SUBDIR = "thumbnails"  # Camera thumbnail cache subdirectory
    CLIPS_SUBDIR = "clips"  # Downloaded clips cache subdirectory

    # ========================================================================
    # Media Processing Configuration (FFmpeg)
    # ========================================================================
    FFMPEG_TIMEOUT = 30  # FFmpeg operation timeout (seconds)
    FFPROBE_TIMEOUT = 10  # FFprobe metadata extraction timeout (seconds)
    HLS_SEGMENT_TIME = 0.5  # HLS segment duration in seconds (ultra low latency)
    HLS_LIST_SIZE = 1  # Number of segments in HLS playlist (minimal possible)
    STREAM_IDLE_TIMEOUT = 300  # 5 minutes before idle stream cleanup

    # ========================================================================
    # Process Management
    # ========================================================================
    PROCESS_TERMINATE_TIMEOUT = 5  # Graceful process termination timeout (seconds)
    PROCESS_WAIT_TIMEOUT = 5  # Process wait timeout in seconds
    BLINK_OPERATION_TIMEOUT = 60  # Blink API operation timeout (seconds)
    BLINK_CONNECTION_TIMEOUT = 60  # Blink connection timeout in seconds

    # ========================================================================
    # API Limits and Batch Sizes
    # ========================================================================
    MAX_VIDEOS_METADATA = 50  # Maximum clips to fetch from Blink API per request
    CLIPS_PER_STORAGE_TYPE = 5  # Clips to show per storage type in UI

    # ========================================================================
    # File System and Logging
    # ========================================================================
    LOG_FILE = "blink_app.log"  # Application log file (relative to cache dir)
    LOG_BACKUP_COUNT = 10  # Number of rotated log files to keep (total)
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB log file size limit before rotation

    @classmethod
    def get_log_file_path(cls) -> str:
        """Get the full path to the application log file.

        Returns:
            str: Full path to the log file
        """
        from pathlib import Path

        cache_dir = Path(cls.DEFAULT_CACHE_DIR)
        return str(cache_dir / cls.LOG_FILE)

    # ========================================================================
    # Network and HTTP Configuration
    # ========================================================================
    HTTP_TIMEOUT = 30  # General HTTP request timeout (seconds)
    DOWNLOAD_TIMEOUT = 60  # File download timeout (seconds, longer for large clips)
    HTTP_RETRY_TOTAL = 3  # Total number of HTTP retries on failure
    HTTP_RETRY_BACKOFF_FACTOR = 1  # Exponential backoff factor for retries

    # ========================================================================
    # Background Processing and Polling
    # ========================================================================
    THUMBNAIL_POLL_INTERVAL = 2  # Thumbnail polling interval in seconds
    THUMBNAIL_POLL_MAX_ATTEMPTS = 15  # Max polling attempts for camera updates
    CLIP_THUMBNAIL_POLL_MAX_ATTEMPTS = 15  # Max attempts for clip thumbnail polling
    CACHE_CLEAR_TIMEOUT = 30  # Cache clearing operation timeout (seconds)
    FUTURE_RESULT_TIMEOUT = 2  # Future result timeout in seconds

    # ========================================================================
    # UI Timing Constants (all in milliseconds for JavaScript)
    # ========================================================================
    HLS_STREAM_CHECK_INTERVAL = 1000  # HLS stream readiness check interval (ms)
    HLS_STREAM_CHECK_DELAY = 2000  # Initial delay before checking HLS stream (ms)
    HLS_STREAM_MAX_ATTEMPTS = 10  # Maximum attempts to check HLS stream readiness
    THUMBNAIL_UPDATE_POLL_INTERVAL = 2000  # Thumbnail update polling interval (ms)
    THUMBNAIL_SUCCESS_DISPLAY_TIME = 1000  # Time to show success message (ms)
    THUMBNAIL_PROCESSING_DISPLAY_TIME = 3000  # Time to show processing message (ms)
    THUMBNAIL_ERROR_DISPLAY_TIME = 3000  # Time to show error message (ms)
    CLIP_THUMBNAIL_CHECK_INTERVAL = (
        2000  # Clip thumbnail availability check interval (ms)
    )

    # ========================================================================
    # Conversion Constants
    # ========================================================================
    MILLISECONDS_TO_SECONDS = 1000  # Conversion factor from milliseconds to seconds

    # ========================================================================
    # Default Values and Fallbacks
    # ========================================================================
    DEFAULT_SYSTEM_NAME = "Blink System"  # Default system name for cloud clips

    # ========================================================================
    # HTTP Status Codes (centralized for consistency)
    # ========================================================================
    HTTP_STATUS_OK = 200  # Success status code
    HTTP_STATUS_BAD_REQUEST = 400  # Bad request status code (client error)
    HTTP_STATUS_UNAUTHORIZED = 401  # Unauthorized status code (auth required)
    HTTP_STATUS_NOT_FOUND = 404  # Not found status code (resource missing)
    HTTP_STATUS_INTERNAL_ERROR = 500  # Internal server error status code
    HTTP_STATUS_NOT_IMPLEMENTED = 501  # Not implemented status code
    HTTP_STATUS_SERVICE_UNAVAILABLE = 503  # Service unavailable status code

    # HTTP retry status codes
    HTTP_RETRY_STATUS_CODES = [429, 500, 502, 503, 504]  # Status codes to retry on

    # HTTP connection pool settings
    HTTP_POOL_CONNECTIONS = 10  # Number of connection pools to cache
    HTTP_POOL_MAXSIZE = 20  # Maximum number of connections in each pool

    # Thread pool settings
    THREAD_POOL_MAX_WORKERS = 4  # Maximum number of background worker threads

    # Validation settings
    MAX_USERNAME_LENGTH = 100  # Maximum username length
    MAX_PASSWORD_LENGTH = 100  # Maximum password length
    MAX_TFA_LENGTH = 10  # Maximum 2FA code length
    VALID_CAMERA_ID_PATTERN = r"^[a-zA-Z0-9_-]+$"  # Camera ID regex
    VALID_NETWORK_ID_PATTERN = r"^[0-9]+$"  # Network ID regex
    VALID_CLIP_ID_PATTERN = r"^[a-zA-Z0-9_~-]+$"  # Clip ID regex

    # User-friendly error messages
    class ErrorMessages:
        """User-friendly error messages for common scenarios."""

        # Authentication errors
        SYSTEM_NOT_INITIALIZED = "Unable to connect to your Blink system. Please try logging out and back in."
        AUTH_FAILED = "Your session has expired. Please log in again to continue."
        INVALID_CREDENTIALS = "The email or password you entered is incorrect. Please check and try again."
        INVALID_2FA_CODE = "The verification code you entered is incorrect. Please check your email or SMS and try again."
        TFA_VERIFICATION_FAILED = "We couldn't verify your code. Please request a new verification code and try again."
        LOGIN_FAILED = "We're having trouble logging you in. Please check your internet connection and try again."

        # Camera errors
        CAMERA_NOT_FOUND = (
            "We couldn't find that camera. It may have been removed or renamed."
        )
        CAMERA_THUMBNAIL_NOT_FOUND = "Unable to load camera image. The camera may be offline or experiencing connectivity issues."
        THUMBNAIL_FETCH_FAILED = "We couldn't update the camera image right now. Please try again in a moment."

        # System errors
        BLINK_NOT_AVAILABLE = "Your Blink system is not available right now. Please check your internet connection and try again."
        SYSTEM_NOT_FOUND = (
            "We couldn't find that Blink system. Please check your account settings."
        )
        SYSTEM_REFRESH_FAILED = "Unable to refresh your Blink system. Please check your internet connection and try again."

        # Clip errors
        CLIP_NOT_FOUND = (
            "We couldn't find that video clip. It may have been deleted or moved."
        )
        CLIP_NO_MEDIA_URL = "This video clip is not available for download right now. Please try again later."
        CLIP_DOWNLOAD_FAILED = "We couldn't download your video clip. Please check your internet connection and try again."
        CLIP_DOWNLOAD_TIMEOUT = (
            "The video download is taking longer than expected. Please try again."
        )
        LOCAL_CLIP_NOT_FOUND = "We couldn't find that local video clip. Please check that your sync module's USB storage is connected."
        LOCAL_STORAGE_NOT_AVAILABLE = "Local storage is not available. Please check that your sync module has a USB drive connected and is online."
        SYNC_MODULE_NOT_FOUND = "We couldn't find your sync module. Please check that it's online and connected to your network."

        # Live streaming errors
        LIVE_VIEW_FAILED = "Unable to start live view. Please check that your camera is online and try again."
        HLS_TRANSCODING_FAILED = "We're having trouble starting the video stream. Please try again in a moment."
        STREAM_MANAGER_UNAVAILABLE = (
            "Live streaming is temporarily unavailable. Please try again later."
        )
        STREAM_NOT_FOUND = "The video stream is no longer available. Please try starting live view again."

        # Data validation errors
        INVALID_JSON_DATA = (
            "The request contains invalid data. Please refresh the page and try again."
        )
        INVALID_REQUEST_DATA = (
            "We couldn't process your request. Please refresh the page and try again."
        )
        INVALID_STORAGE_TYPE = "Please select either cloud storage or local storage."
        INVALID_ARM_STATUS = "Please specify whether to arm or disarm the system."
        INVALID_FILE_TYPE = "The requested file type is not supported."

        # Generic errors
        FEATURE_NOT_AVAILABLE = (
            "This feature is coming soon! We're working hard to bring it to you."
        )
        INTERNAL_ERROR = (
            "Something went wrong on our end. Please try again in a few moments."
        )
        THUMBNAIL_NOT_FOUND = "Image not available. The camera may be offline or the image may have expired."


# ========================================================================
# Configuration Validation Functions
# ========================================================================


def validate_cache_directory(cache_dir: str) -> bool:
    """Validate cache directory - pure function for better testability.

    Args:
        cache_dir: Path to the cache directory to validate.

    Returns:
        True if directory exists or parent directory exists for creation.
    """
    cache_path = Path(cache_dir)
    return cache_path.exists() or cache_path.parent.exists()


def ensure_cache_directory(
    cache_dir: str, validator: "CallableType[[str], bool] | None" = None
) -> None:
    """Ensure cache directory exists with injectable validator for testing.

    Args:
        cache_dir: Path to the cache directory to create.
        validator: Optional validator function for testing. Defaults to validate_cache_directory.
    """
    if validator is None:
        validator = validate_cache_directory

    if not validator(cache_dir):
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
