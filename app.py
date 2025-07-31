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
import functools
import logging
import os
import re
import signal
import sys
import threading
import traceback
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    ParamSpec,
    TypedDict,
    cast,
)

if TYPE_CHECKING:
    from concurrent.futures import ThreadPoolExecutor

    from blink_connection import BlinkConnection

import requests
from cachetools import LRUCache, cachedmethod
from cachetools.keys import hashkey
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

from blinkpy.auth import Auth  # type: ignore
from blinkpy.blinkpy import Blink  # type: ignore
from blinkpy.camera import BlinkCamera
from blinkpy.sync_module import BlinkSyncModule
from config import Config

# from flask_sse import sse  # No longer needed
from stream_manager import StreamConfig, StreamManager

# Global variables
app: "Flask | None" = None
blink: "Blink | None" = None
blink_connection: "BlinkConnection | None" = None
executor: "ThreadPoolExecutor | None" = None
http_session: "requests.Session | None" = None
stream_manager: "StreamManager | None" = None

# Global cache directory variables
CACHE_DIR: str | None = None
CREDENTIALS_FILE: str | None = None
THUMBNAIL_CACHE_DIR: str | None = None
CLIPS_CACHE_DIR: str | None = None
SETTINGS_FILE: str | None = None

# Type variables for generic functions
P = ParamSpec("P")


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
def error_context(
    operation: str, reraise_as: type = BlinkError
) -> Generator[None, None, None]:
    """Context manager for consistent error handling.

    Args:
        operation: Description of the operation being performed
        reraise_as: Exception type to reraise as (default: BlinkError)

    Yields:
        None: Context for the operation

    Raises:
        BlinkError: If the operation fails (or the specified reraise_as type)
    """
    try:
        yield
    except Exception as e:
        logger.error(f"Error during {operation}: {e}")
        logger.debug(f"Full traceback for {operation}: {traceback.format_exc()}")
        if isinstance(e, BlinkError):
            raise
        raise reraise_as(f"Failed to {operation}: {str(e)}") from e


def safe_execute(
    func: Callable[[], Any], default: Any = None, log_error: bool = True
) -> Any:
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

    def __init__(self, value: str | int | float) -> None:
        """Initialize and validate ID value.

        Args:
            value: String or numeric ID to validate

        Raises:
            ValueError: If value is empty or doesn't match pattern
        """
        # Convert to string if needed
        if isinstance(value, int | float):
            value = str(value)

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
        if not isinstance(value, str):
            raise ValueError(f"{self._get_type_name()} must be a string")

        value = value.strip()
        if not value:
            raise ValueError(f"{self._get_type_name()} cannot be empty")

        # Allow numeric strings and basic alphanumeric patterns
        if not re.match(r"^[a-zA-Z0-9_~-]+$", value):
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

    def __int__(self) -> int:
        """Convert to integer if possible."""
        try:
            return int(self.value)
        except ValueError as e:
            raise ValueError(
                f"Cannot convert {self._get_type_name()} '{self.value}' to integer"
            ) from e


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

    def get_local_parts(self) -> tuple[str, int]:
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

    @classmethod
    def from_cloud(cls, clip_id: int | str) -> "ClipId":
        """Create ClipId for cloud storage clip.

        Args:
            clip_id: Numeric ID of the cloud clip

        Returns:
            ClipId instance for cloud clip
        """
        return cls(str(clip_id))


# Standard thread-safe decorator using functools.wraps
def synchronized(func):
    """Decorator to make cache methods thread-safe using the instance's _lock.

    This follows the standard Python pattern for creating decorators that
    preserve function metadata using functools.wraps.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return func(self, *args, **kwargs)

    return wrapper


# Simplified cache implementation inheriting from LRUCache


class ThumbnailCache(LRUCache):
    """
    Thumbnail cache inheriting from LRUCache with thread-safe methods.

    Combines the simplicity of direct LRUCache inheritance with thread-safe
    operations using both decorators and cachetools @cachedmethod decorators.
    """

    def __init__(self, maxsize: int = 100):
        super().__init__(maxsize=maxsize)
        self._lock = threading.RLock()

    # Thread-safe overrides for LRUCache methods using decorator
    @synchronized
    def get(self, key: Any, default: Any = None) -> Any:
        """Thread-safe get method."""
        return super().get(key, default)

    @synchronized
    def __getitem__(self, key: Any) -> Any:
        """Thread-safe getitem method."""
        return super().__getitem__(key)

    @synchronized
    def __setitem__(self, key: Any, value: Any) -> None:
        """Thread-safe setitem method."""
        super().__setitem__(key, value)

    @synchronized
    def __delitem__(self, key: Any) -> None:
        """Thread-safe delitem method."""
        super().__delitem__(key)

    @synchronized
    def __contains__(self, key: Any) -> bool:
        """Thread-safe contains method."""
        return super().__contains__(key)

    @synchronized
    def __len__(self) -> int:
        """Thread-safe len method."""
        return super().__len__()

    @synchronized
    def pop(self, key: Any, default: Any = None) -> Any:
        """Thread-safe pop method."""
        return super().pop(key, default)

    @synchronized
    def popitem(self) -> tuple[Any, Any]:
        """Thread-safe popitem method."""
        return super().popitem()

    @synchronized
    def clear(self) -> None:
        """Thread-safe clear method."""
        super().clear()

    @synchronized
    def setdefault(self, key: Any, default: Any = None) -> Any:
        """Thread-safe setdefault method."""
        return super().setdefault(key, default)

    @synchronized
    def update(self, *args: Any, **kwargs: Any) -> None:
        """Thread-safe update method."""
        super().update(*args, **kwargs)

    @synchronized
    def keys(self) -> Any:
        """Thread-safe keys method."""
        return list(super().keys())

    @synchronized
    def values(self) -> Any:
        """Thread-safe values method."""
        return list(super().values())

    @synchronized
    def items(self) -> Any:
        """Thread-safe items method."""
        return list(super().items())

    # Custom methods using @cachedmethod decorator
    @cachedmethod(lambda self: self, lock=lambda self: self._lock)
    def get_thumbnail_data(self, camera_id: str, timestamp: int) -> dict[str, Any]:
        """
        Get thumbnail data - automatically cached and thread-safe.

        This method uses @cachedmethod decorator as recommended by cachetools.
        Only called once per unique (camera_id, timestamp) combination.
        """
        return {
            "camera_id": camera_id,
            "timestamp": timestamp,
            "filename": f"thumb_{camera_id}_{timestamp}.jpg",
        }

    @synchronized
    def update_thumbnail_if_newer(
        self, camera_id: str, timestamp: int, filename: str
    ) -> bool:
        """
        Update thumbnail if timestamp is newer.

        For conditional caching logic where decorators aren't suitable.
        """
        # Check for existing entries for this camera
        cache_key = f"{camera_id}_current"
        current_entry = self.get(cache_key)
        current_ts = current_entry.get("timestamp", 0) if current_entry else 0

        if timestamp > current_ts:
            self[cache_key] = {
                "camera_id": camera_id,
                "timestamp": timestamp,
                "filename": filename,
            }
            return True
        return False

    @synchronized
    def get_current_thumbnail(self, camera_id: str) -> dict[str, Any] | None:
        """Get current thumbnail info for camera."""
        return self.get(f"{camera_id}_current")

    def clear_cache(self) -> None:
        """Clear all cached thumbnails."""
        self.clear()

    @synchronized
    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {"size": len(self), "maxsize": self.maxsize}


class ClipsMetadataCache(LRUCache):
    """
    Clips metadata cache inheriting from LRUCache with thread-safe methods.
    """

    def __init__(self, maxsize: int = 1000):
        super().__init__(maxsize=maxsize)
        self._lock = threading.RLock()

    @cachedmethod(lambda self: self, lock=lambda self: self._lock)
    def get_clips_metadata(self, storage_type: str) -> list[dict[str, Any]]:
        """
        Get clips metadata - automatically cached and thread-safe.

        Uses @cachedmethod decorator as recommended by cachetools.
        """
        # This would normally fetch from Blink API
        return []

    @cachedmethod(
        lambda self: self,
        lock=lambda self: self._lock,
        key=lambda self, storage, filters: hashkey(
            storage, tuple(sorted(filters.items()))
        ),
    )
    def get_filtered_clips(
        self, storage_type: str, filters: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Get filtered clips with custom key function.

        Uses custom key function to handle dict parameters properly.
        """
        base_clips = self.get_clips_metadata(storage_type)
        # Apply filters here
        return base_clips

    @synchronized
    def cache_clips_manually(
        self, storage_type: str, clips: list[dict[str, Any]]
    ) -> None:
        """Manually cache clips list (for cases where decorator isn't suitable)."""
        # Manually add to cache using the same key pattern as the decorator
        cache_key = (self.get_clips_metadata, storage_type)
        self[cache_key] = clips

    @synchronized
    def clear_cache(self) -> None:
        """Clear all cached clips metadata."""
        self.clear()

    @synchronized
    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {"size": len(self), "maxsize": self.maxsize}

    # Thread-safe overrides for LRUCache methods
    @synchronized
    def get(self, key: Any, default: Any = None) -> Any:
        """Thread-safe get method."""
        return super().get(key, default)

    @synchronized
    def __getitem__(self, key: Any) -> Any:
        """Thread-safe getitem method."""
        return super().__getitem__(key)

    @synchronized
    def __setitem__(self, key: Any, value: Any) -> None:
        """Thread-safe setitem method."""
        super().__setitem__(key, value)

    @synchronized
    def __delitem__(self, key: Any) -> None:
        """Thread-safe delitem method."""
        super().__delitem__(key)

    @synchronized
    def __contains__(self, key: Any) -> bool:
        """Thread-safe contains method."""
        return super().__contains__(key)

    @synchronized
    def __len__(self) -> int:
        """Thread-safe len method."""
        return super().__len__()

    @synchronized
    def pop(self, key: Any, default: Any = None) -> Any:
        """Thread-safe pop method."""
        return super().pop(key, default)

    @synchronized
    def popitem(self) -> tuple[Any, Any]:
        """Thread-safe popitem method."""
        return super().popitem()

    @synchronized
    def clear(self) -> None:
        """Thread-safe clear method."""
        super().clear()

    @synchronized
    def setdefault(self, key: Any, default: Any = None) -> Any:
        """Thread-safe setdefault method."""
        return super().setdefault(key, default)

    @synchronized
    def update(self, *args: Any, **kwargs: Any) -> None:
        """Thread-safe update method."""
        super().update(*args, **kwargs)

    @synchronized
    def keys(self) -> Any:
        """Thread-safe keys method."""
        return list(super().keys())

    @synchronized
    def values(self) -> Any:
        """Thread-safe values method."""
        return list(super().values())

    @synchronized
    def items(self) -> Any:
        """Thread-safe items method."""
        return list(super().items())

    @property
    def maxsize(self) -> int:
        """Get maximum cache size."""
        return self._cache.maxsize


class ClipsDownloadCache(LRUCache):
    """
    Clips download cache inheriting from LRUCache with thread-safe methods.
    """

    def __init__(self, maxsize: int = 100):
        super().__init__(maxsize=maxsize)
        self._lock = threading.RLock()

    @cachedmethod(lambda self: self, lock=lambda self: self._lock)
    def get_clip_download_info(self, clip_id: str) -> dict[str, Any]:
        """
        Get clip download info - automatically cached and thread-safe.

        Uses @cachedmethod decorator as recommended by cachetools.
        """
        return {
            "clip_id": clip_id,
            "filepath": f"/downloads/{clip_id}.mp4",
            "thumbnail": None,
        }

    @synchronized
    def cache_clip_manually(
        self, clip_id: str, filepath: str, thumbnail_path: str | None = None
    ) -> None:
        """Manually cache clip info (for cases where decorator isn't suitable)."""
        cache_key = (self.get_clip_download_info, clip_id)
        self[cache_key] = {
            "clip_id": clip_id,
            "filepath": filepath,
            "thumbnail": thumbnail_path,
        }

    @synchronized
    def clear_cache(self) -> None:
        """Clear all cached clip downloads."""
        self.clear()

    @synchronized
    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {"size": len(self), "maxsize": self.maxsize}

    # Thread-safe overrides for LRUCache methods
    @synchronized
    def get(self, key: Any, default: Any = None) -> Any:
        """Thread-safe get method."""
        return super().get(key, default)

    @synchronized
    def __getitem__(self, key: Any) -> Any:
        """Thread-safe getitem method."""
        return super().__getitem__(key)

    @synchronized
    def __setitem__(self, key: Any, value: Any) -> None:
        """Thread-safe setitem method."""
        super().__setitem__(key, value)

    @synchronized
    def __delitem__(self, key: Any) -> None:
        """Thread-safe delitem method."""
        super().__delitem__(key)

    @synchronized
    def __contains__(self, key: Any) -> bool:
        """Thread-safe contains method."""
        return super().__contains__(key)

    @synchronized
    def __len__(self) -> int:
        """Thread-safe len method."""
        return super().__len__()

    @synchronized
    def pop(self, key: Any, default: Any = None) -> Any:
        """Thread-safe pop method."""
        return super().pop(key, default)

    @synchronized
    def popitem(self) -> tuple[Any, Any]:
        """Thread-safe popitem method."""
        return super().popitem()

    @synchronized
    def clear(self) -> None:
        """Thread-safe clear method."""
        super().clear()

    @synchronized
    def setdefault(self, key: Any, default: Any = None) -> Any:
        """Thread-safe setdefault method."""
        return super().setdefault(key, default)

    @synchronized
    def update(self, *args: Any, **kwargs: Any) -> None:
        """Thread-safe update method."""
        super().update(*args, **kwargs)

    @synchronized
    def keys(self) -> Any:
        """Thread-safe keys method."""
        return list(super().keys())

    @synchronized
    def values(self) -> Any:
        """Thread-safe values method."""
        return list(super().values())

    @synchronized
    def items(self) -> Any:
        """Thread-safe items method."""
        return list(super().items())

    @property
    def maxsize(self) -> int:
        """Get maximum cache size."""
        return self._cache.maxsize


# Cache instances using object-oriented memoizing decorators
thumbnail_cache_oo = ThumbnailCache(maxsize=Config.THUMBNAIL_CACHE_SIZE)
clips_metadata_cache_oo = ClipsMetadataCache(maxsize=Config.CLIPS_METADATA_CACHE_SIZE)
clips_download_cache_oo = ClipsDownloadCache(maxsize=Config.CLIPS_CACHE_SIZE)

# Hybrid approach: Keep both implementations for compatibility
# Object-oriented cache instances (new approach)
thumbnail_cache = thumbnail_cache_oo
clips_metadata_cache = clips_metadata_cache_oo
clips_download_cache = clips_download_cache_oo

# Alias for backward compatibility with tests
clips_cache = clips_download_cache


def is_authenticated() -> bool:
    """Check if user is authenticated with Blink.

    Returns:
        True if authenticated, False otherwise
    """
    global blink
    return blink is not None and hasattr(blink, "auth") and blink.auth.startup_complete


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        args: Optional list of arguments to parse (for testing)

    Returns:
        Parsed arguments namespace
    """
    import argparse

    parser = argparse.ArgumentParser(description="Blink Camera Flask Web Interface")
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=5000, help="Port to bind to (default: 5000)"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "--cache", default=Config.DEFAULT_CACHE_DIR, help="Cache directory path"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level",
    )
    parser.add_argument(
        "--dump-system",
        action="store_true",
        help="Dump Blink system information and exit (requires saved credentials)",
    )

    return parser.parse_args(args)


def get_cache_stats() -> dict[str, dict[str, Any]]:
    """Get statistics for all caches using OO implementation."""
    return {
        "thumbnail_cache": thumbnail_cache.get_cache_stats(),
        "clips_metadata_cache": clips_metadata_cache.get_cache_stats(),
        "clips_download_cache": clips_download_cache.get_cache_stats(),
    }

    def __init__(self, cache: Any) -> None:
        self._cache = cache
        self._lock = threading.RLock()

    @synchronized
    def get(self, key: Any, default: Any = None) -> Any:
        """Get value from cache."""
        return self._cache.get(key, default)

    @synchronized
    def __setitem__(self, key: Any, value: Any) -> None:
        """Set value in cache."""
        self._cache[key] = value

    @synchronized
    def __getitem__(self, key: Any) -> Any:
        """Get value from cache with KeyError if not found."""
        return self._cache[key]

    @synchronized
    def __contains__(self, key: Any) -> bool:
        """Check if key exists in cache."""
        return key in self._cache

    @synchronized
    def pop(self, key: Any, default: Any = None) -> Any:
        """Remove and return value from cache."""
        return self._cache.pop(key, default)

    @synchronized
    def clear(self) -> None:
        """Clear all entries from cache."""
        self._cache.clear()

    @synchronized
    def __len__(self) -> int:
        """Get current cache size."""
        return len(self)


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
    thumbnail: Path | None


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
    data: Any | None
    error: str | None


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


def find_camera_by_id(camera_id: CameraId) -> BlinkCamera | None:
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
    error: Exception,
    operation: str,
    status_code: int = Config.HTTP_STATUS_INTERNAL_ERROR,
) -> tuple[ApiResponse, int]:
    """Handle API errors with user-friendly messages.

    Args:
        error: Exception that occurred
        operation: Description of operation that failed
        status_code: HTTP status code to return

    Returns:
        Standardized error response tuple
    """
    logger.error(f"Error {operation}: {error}")

    # Map common exceptions to user-friendly messages
    error_message = str(error)
    if isinstance(error, ConnectionError):
        error_message = "Unable to connect to your Blink system. Please check your internet connection and try again."
    elif isinstance(error, TimeoutError):
        error_message = "The request timed out. Please try again in a moment."
    elif isinstance(error, ValueError):
        error_message = "Invalid data provided. Please check your input and try again."
    elif "authentication" in str(error).lower() or "login" in str(error).lower():
        error_message = Config.ErrorMessages.AUTH_FAILED
    elif "not found" in str(error).lower():
        error_message = "The requested item could not be found."
    elif status_code >= 500:
        error_message = Config.ErrorMessages.INTERNAL_ERROR

    return create_api_response(
        success=False, error=error_message, status_code=status_code
    )


def require_camera(
    camera_id: CameraId,
) -> tuple[BlinkCamera | None, tuple[ApiResponse, int] | None]:
    """Find camera by ID, return error response if not found.

    Args:
        camera_id: Camera ID to find

    Returns:
        Tuple of (camera, error_response). One will be None.
    """
    camera = find_camera_by_id(camera_id)
    if camera is None:
        error_response = create_api_response(
            success=False, error=Config.ErrorMessages.CAMERA_NOT_FOUND, status_code=404
        )
        return None, error_response
    return camera, None


def require_sync_module(
    network_id: NetworkId,
) -> tuple[BlinkSyncModule | None, tuple[ApiResponse, int] | None]:
    """Find sync module by network ID, return error response if not found.

    Args:
        network_id: Network ID to find

    Returns:
        Tuple of (sync_module, error_response). One will be None.
    """
    assert blink is not None
    for name, sync in blink.sync.items():
        if str(sync.network_id) == str(network_id):
            return sync, None

    error_response = create_api_response(
        success=False, error=Config.ErrorMessages.SYSTEM_NOT_FOUND, status_code=404
    )
    return None, error_response


def parse_clip_id(
    clip_id_str: str,
) -> tuple[ClipId | None, tuple[ApiResponse, int] | None]:
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


def create_api_response(
    success: bool = True,
    data: Any = None,
    error: str | None = None,
    status_code: int = Config.HTTP_STATUS_OK,
) -> tuple[ApiResponse, int]:
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


def requires_blink(
    func: Callable[P, ResponseReturnValue],
) -> Callable[P, ResponseReturnValue]:
    """Decorator that ensures blink is available before calling the function.

    This decorator also serves as a type guard, telling type checkers that
    after the check, blink is guaranteed to be non-None and available.

    Usage in decorated functions:
        @requires_blink
        def my_function() -> ResponseReturnValue:
            assert blink is not None  # For Pylance type narrowing
            return jsonify(blink.sync)  # No type errors
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> ResponseReturnValue:
        error_response = require_blink()
        if error_response is not None:
            response, status_code = error_response
            return jsonify(response), status_code

        # At this point, type checkers know blink is not None and available
        assert blink is not None  # Help type checkers understand this
        assert blink.available  # Additional assertion for Pylance

        return func(*args, **kwargs)

    return wrapper


def require_blink() -> tuple[ApiResponse, int] | None:
    """Check if Blink is available, return error response if not.

    Returns:
        None if Blink is available, error response tuple if not
    """
    if blink is None:
        return create_api_response(
            success=False,
            error=Config.ErrorMessages.SYSTEM_NOT_INITIALIZED,
            status_code=Config.HTTP_STATUS_INTERNAL_ERROR,
        )
    if not blink.available:
        return create_api_response(
            success=False,
            error=Config.ErrorMessages.AUTH_FAILED,
            status_code=401,
        )
    return None


# Cache instances are now created using OO implementation above


def ensure_cache_paths_initialized() -> None:
    """Ensure cache paths are initialized, raising an error if not.

    This function serves as a type guard for mypy to understand that
    the cache path variables are not None after this call.

    Raises:
        RuntimeError: If cache paths haven't been initialized
    """
    if (
        CACHE_DIR is None
        or CREDENTIALS_FILE is None
        or THUMBNAIL_CACHE_DIR is None
        or CLIPS_CACHE_DIR is None
    ):
        raise RuntimeError(
            "Cache paths not initialized. Call initialize_cache_paths() first."
        )


def initialize_cache_paths() -> None:
    """Initialize cache directory paths from Flask config or defaults.

    Sets global path variables for cache directories and credential file.
    Uses Flask app config 'CACHE_DIR' or defaults to Config.DEFAULT_CACHE_DIR.

    Side Effects:
        Updates global variables: CACHE_DIR, CREDENTIALS_FILE,
        THUMBNAIL_CACHE_DIR, CLIPS_CACHE_DIR, SETTINGS_FILE
    """
    global \
        CACHE_DIR, \
        CREDENTIALS_FILE, \
        THUMBNAIL_CACHE_DIR, \
        CLIPS_CACHE_DIR, \
        SETTINGS_FILE
    cache_dir = Path(app.config.get("CACHE_DIR", Config.DEFAULT_CACHE_DIR))
    CACHE_DIR = str(cache_dir)
    CREDENTIALS_FILE = str(cache_dir / Config.CREDENTIALS_FILENAME)
    THUMBNAIL_CACHE_DIR = str(cache_dir / Config.THUMBNAILS_SUBDIR)
    CLIPS_CACHE_DIR = str(cache_dir / Config.CLIPS_SUBDIR)
    SETTINGS_FILE = str(cache_dir / Config.SETTINGS_FILENAME)


# Cache configuration
CLIPS_CACHE_SIZE = Config.CLIPS_CACHE_SIZE  # Maximum number of clips to cache
SETTINGS_FILE: str | None = (
    None  # Path to settings file, set in initialize_cache_paths()
)

# Legacy stream variables removed - now handled by StreamManager

# Blink operations delegated to blink_thread module


async def initialize_blink(
    username: str, password: str
) -> bool | Literal["2fa_required"]:
    """Initialize Blink system following blinkpy README.

    Args:
        username: Blink account username/email
        password: Blink account password

    Returns:
        True if successful, '2fa_required' if 2FA needed, False if failed
    """
    global blink
    with error_context("initialize Blink system", AuthenticationError):
        from aiohttp import ClientSession

        session = ClientSession()
        blink = Blink(session=session)
        blink_connection.blink = blink  # Set reference in connection
        auth = Auth(
            {"username": username, "password": password},
            no_prompt=True,
            session=session,
        )
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
        assert blink is not None
        await blink.auth.send_auth_key(blink, tfa_key)

        logger.debug("Setting up post verification...")
        await blink.setup_post_verify()

        logger.debug("Saving credentials...")
        assert CREDENTIALS_FILE is not None
        await blink.save(CREDENTIALS_FILE)

        logger.info("2FA verification and save completed successfully")
        return True


def extract_thumbnail_timestamp(thumbnail_url: str | None) -> int:
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
    except (AttributeError, ValueError, TypeError) as e:
        logger.debug(f"Failed to extract timestamp from URL '{thumbnail_url}': {e}")
        return 0


def create_device_data(
    camera: BlinkCamera, cache_key: CameraId, current_ts: int, cached_ts: int
) -> dict[str, Any]:
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
        except (ValueError, TypeError, AttributeError) as e:
            logger.debug(
                f"Failed to calculate time difference for camera {camera.name}: {e}"
            )
            last_updated = (
                format_time_ago(camera.last_record) if camera.last_record else "Never"
            )

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

    def update_thumbnail() -> None:
        # Double-check timestamp to prevent race condition
        current_entry = thumbnail_cache.get(cache_key)
        current_cached_ts = current_entry.get("timestamp", 0) if current_entry else 0
        if current_ts <= current_cached_ts:
            logger.debug(f"Thumbnail already updated for {camera.name}, skipping")
            return

        # Remove old cached file if exists
        old_entry = thumbnail_cache.get(cache_key)
        if old_entry is not None:
            old_filename = old_entry.get("filename")
            if old_filename is not None:
                assert THUMBNAIL_CACHE_DIR is not None
                old_filepath = Path(cast(str, THUMBNAIL_CACHE_DIR)) / old_filename
                try:
                    if old_filepath.exists():
                        old_filepath.unlink()
                        logger.debug(f"Removed old thumbnail file: {old_filename}")
                except OSError as e:
                    logger.debug(f"Could not remove old thumbnail: {e}")

        thumbnail_response = blink_connection.execute(camera.thumbnail)
        if (
            thumbnail_response is not None
            and thumbnail_response.status == Config.HTTP_STATUS_OK
        ):
            image_data = blink_connection.execute(thumbnail_response.read())

            # Save to file with new timestamp
            filename = f"{cache_key}_{current_ts}.jpg"
            assert THUMBNAIL_CACHE_DIR is not None
            filepath = Path(cast(str, THUMBNAIL_CACHE_DIR)) / filename
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


def process_cloud_clips(videos_metadata: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Process cloud storage clips into day-grouped format.

    Args:
        videos_metadata: Raw video metadata from Blink API

    Returns:
        List of day groups with clips
    """
    clips_by_day: dict[str, dict[str, Any]] = {}
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


def process_local_clips() -> list[dict[str, Any]]:
    """Process local storage clips into day-grouped format.

    Returns:
        List of day groups with clips
    """
    clips_by_day: dict[str, dict[str, Any]] = {}

    assert blink is not None
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
    clips_by_day: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
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


def format_time_ago(timestamp_str: str | int | None) -> str:
    """Format timestamp as 'Xd ago' format.

    Args:
        timestamp_str: ISO format timestamp string, Unix timestamp integer, or None

    Returns:
        Formatted time string like '5d ago', '2h ago', '30m ago', or 'Unknown'
    """
    try:
        if timestamp_str is None:
            return "Unknown"

        # Handle different input types
        if isinstance(timestamp_str, int):
            # Unix timestamp (seconds since epoch)
            timestamp = datetime.fromtimestamp(timestamp_str, tz=timezone.utc)
        elif isinstance(timestamp_str, str):
            # ISO format timestamp string
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        else:
            logger.debug(f"Unsupported timestamp type: {type(timestamp_str)}")
            return "Unknown"

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
    except (ValueError, TypeError, AttributeError, OSError) as e:
        logger.debug(f"Failed to format time ago for '{timestamp_str}': {e}")
        return "Unknown"


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


@app.route("/login", methods=["GET", "POST"])
def login() -> ResponseReturnValue:
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
            return render_template("auth.html", is_2fa=False, error=str(e))

        # Initialize Blink thread if needed
        blink_connection.start()

        try:
            success = blink_connection.execute(initialize_blink(username, password))
            assert blink is not None
            if success == "2fa_required":
                session["temp_username"] = username
                session["temp_password"] = password
                return redirect(url_for("two_factor"))
            elif success:
                assert CREDENTIALS_FILE is not None
                blink_connection.execute(blink.save(CREDENTIALS_FILE))
                session["authenticated"] = True
                return redirect(url_for("index"))
            else:
                return render_template(
                    "auth.html",
                    is_2fa=False,
                    error=Config.ErrorMessages.INVALID_CREDENTIALS,
                )
        except AuthenticationError as e:
            return render_template("login.html", error=str(e))
        except Exception as e:
            logger.error(f"Unexpected login error: {e}")
            return render_template(
                "auth.html", is_2fa=False, error=Config.ErrorMessages.LOGIN_FAILED
            )

    return render_template("auth.html", is_2fa=False)


@app.route("/2fa", methods=["GET", "POST"])
def two_factor() -> ResponseReturnValue:
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
                "auth.html",
                is_2fa=True,
                error=str(e),
                email=session.get("temp_username", ""),
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
                return render_template(
                    "auth.html",
                    is_2fa=True,
                    error=Config.ErrorMessages.INVALID_2FA_CODE,
                    email=session.get("temp_username", ""),
                )
        except AuthenticationError as e:
            return render_template(
                "auth.html",
                is_2fa=True,
                error=str(e),
                email=session.get("temp_username", ""),
            )
        except Exception as e:
            logger.error(f"Unexpected 2FA error: {e}")
            return render_template(
                "auth.html",
                is_2fa=True,
                error=Config.ErrorMessages.TFA_VERIFICATION_FAILED,
                email=session.get("temp_username", ""),
            )

    return render_template(
        "auth.html", is_2fa=True, email=session.get("temp_username", "")
    )


def clear_all_caches() -> dict[str, Any]:
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
def clear_cache() -> ResponseReturnValue:
    """Clear all caches except credentials."""
    executor.submit(clear_all_caches)
    response, status_code = create_api_response(
        success=True, data={"message": "Cache clearing initiated"}
    )
    return jsonify(response), status_code


@app.route("/logout", methods=["POST"])
def logout() -> ResponseReturnValue:
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
    assert CREDENTIALS_FILE is not None
    cred_file = Path(CREDENTIALS_FILE)
    if cred_file.exists():
        cred_file.unlink()

    response, status_code = create_api_response(
        success=True, data={"message": "Logged out successfully"}
    )
    return jsonify(response), status_code


@app.route("/api/system/list")
@requires_blink
def get_systems() -> ResponseReturnValue:
    """Get list of available Blink systems.

    Returns:
        JSON response with list of systems or error message
    """
    assert blink is not None  # Guaranteed by @requires_blink decorator

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


@app.route("/api/system/<network_id_str>/devices")
@requires_blink
def get_devices(network_id_str: str) -> ResponseReturnValue:
    """Get devices for a specific Blink system.

    Args:
        network_id: Network ID of the Blink system

    Returns:
        JSON response with list of devices or error message
    """
    try:
        network_id = NetworkId(network_id_str)
    except ValueError as e:
        response, status_code = create_api_response(
            success=False, error=str(e), status_code=400
        )
        return jsonify(response), status_code
    devices = []

    # Find the sync module for this network
    sync_module, error_response = require_sync_module(network_id)
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code

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

    response, status_code = create_api_response(success=True, data=devices)
    return jsonify(response), status_code


@app.route("/api/system/<network_id_str>/arm", methods=["POST"])
@requires_blink
def arm_system(network_id_str: str) -> ResponseReturnValue:
    """Arm or disarm a Blink system.

    Args:
        network_id: Network ID of the system to arm/disarm

    Returns:
        JSON response with success status or error message
    """
    try:
        network_id = NetworkId(network_id_str)
    except ValueError as e:
        response, status_code = create_api_response(
            success=False, error=str(e), status_code=400
        )
        return jsonify(response), status_code
    try:
        data = request.get_json()
        if not isinstance(data, dict):
            response, status_code = create_api_response(
                success=False,
                error=Config.ErrorMessages.INVALID_JSON_DATA,
                status_code=400,
            )
            return jsonify(response), status_code

        armed = data.get("armed")
        if not isinstance(armed, bool):
            response, status_code = create_api_response(
                success=False,
                error=Config.ErrorMessages.INVALID_ARM_STATUS,
                status_code=400,
            )
            return jsonify(response), status_code
    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Invalid request data for arm/disarm: {e}")
        response, status_code = create_api_response(
            success=False,
            error=Config.ErrorMessages.INVALID_REQUEST_DATA,
            status_code=400,
        )
        return jsonify(response), status_code

    # Find the sync module
    sync_module, error_response = require_sync_module(network_id)
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code

    with error_context("arm/disarm system"):
        if sync_module is not None:
            blink_connection.execute(sync_module.async_arm(armed))
        response, status_code = create_api_response(success=True, data={"armed": armed})
        return jsonify(response), status_code


@app.route("/api/camera/<camera_id_str>/refresh", methods=["POST"])
@requires_blink
def refresh_camera(camera_id_str: str) -> ResponseReturnValue:
    """Refresh camera thumbnail."""
    assert blink is not None
    try:
        camera_id = CameraId(camera_id_str)
    except ValueError as e:
        response, status_code = create_api_response(
            success=False, error=str(e), status_code=400
        )
        return jsonify(response), status_code

    camera, error_response = require_camera(camera_id)
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code

    assert camera is not None
    with error_context("refresh camera thumbnail", CameraError):
        # Remove camera thumbnail from cache in background
        def remove_thumbnail_cache() -> None:
            cache_key = CameraId(camera.camera_id)
            cached_info = thumbnail_cache.get(cache_key)
            if cached_info is not None:
                # Remove cached file
                if "filename" in cached_info:
                    assert THUMBNAIL_CACHE_DIR is not None
                    cached_file = (
                        Path(cast(str, THUMBNAIL_CACHE_DIR)) / cached_info["filename"]
                    )
                    try:
                        if cached_file.exists():
                            cached_file.unlink()
                    except OSError as e:
                        logger.debug(f"Could not remove cached thumbnail: {e}")
                # Remove from cache
                thumbnail_cache.pop(cache_key, None)

        executor.submit(remove_thumbnail_cache)

        if camera is not None:
            blink_connection.execute(camera.snap_picture())

        # Refresh camera data to get updated thumbnail URL
        blink_connection.execute(blink.refresh())

        response, status_code = create_api_response(
            success=True, data={"message": "Thumbnail refresh initiated"}
        )
        return jsonify(response), status_code


@app.route("/api/clips")
@requires_blink
def get_clips() -> ResponseReturnValue:
    """Get clips from cloud or local storage."""
    assert blink is not None
    storage_type = request.args.get("storage", "cloud")
    if storage_type not in ["cloud", "local"]:
        response, status_code = create_api_response(
            success=False,
            error=Config.ErrorMessages.INVALID_STORAGE_TYPE,
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


@app.route("/api/system/refresh", methods=["POST"])
@requires_blink
def refresh_system() -> ResponseReturnValue:
    """Manually refresh the Blink system."""
    assert blink is not None
    try:
        success = blink_connection.execute(blink.refresh(force=True))

        if success is True:
            response, status_code = create_api_response(
                success=True, data={"message": "System refreshed successfully"}
            )
            return jsonify(response), status_code
        else:
            response, status_code = create_api_response(
                success=False,
                error=Config.ErrorMessages.SYSTEM_REFRESH_FAILED,
                status_code=500,
            )
            return jsonify(response), status_code
    except Exception as e:
        logger.error(f"Error refreshing system: {e}")
        response, status_code = create_api_response(
            success=False,
            error=Config.ErrorMessages.SYSTEM_REFRESH_FAILED,
            status_code=500,
        )
        return jsonify(response), status_code


@app.route("/api/clip/<clip_id_str>/process", methods=["POST"])
@requires_blink
def process_clip(clip_id_str: str) -> ResponseReturnValue:
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
    try:
        if clip_id.is_local():
            sync_name, item_id = clip_id.get_local_parts()
            process_local_clip_background(clip_id, sync_name, item_id)
        else:
            process_cloud_clip_background(clip_id)

        response, status_code = create_api_response(
            success=True, data={"message": "Clip processing initiated"}
        )
        return jsonify(response), status_code
    except Exception as e:
        response, status_code = handle_api_error(e, f"processing clip {clip_id}")
        return jsonify(response), status_code


@app.route("/api/clip/<clip_id_str>/download")
@requires_blink
def download_clip(clip_id_str: str) -> ResponseReturnValue:
    """Download a specific clip."""
    clip_id, error_response = parse_clip_id(clip_id_str)
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code
    assert clip_id is not None
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
) -> ResponseReturnValue:
    """Common clip download logic after file is downloaded."""
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


@app.route("/api/camera/<camera_id_str>/liveview")
@requires_blink
def get_camera_liveview(camera_id_str: str) -> ResponseReturnValue:
    """Get live view stream for camera using init_livestream() as specified in IMPLEMENTATION.md.

    Args:
        camera_id_str: String representation of the camera ID

    Returns:
        JSON response with stream URLs (TCP and HLS) or error message

    Raises:
        ValueError: If camera_id_str is invalid
    """
    try:
        camera_id = CameraId(camera_id_str)
    except ValueError as e:
        response, status_code = create_api_response(
            success=False, error=str(e), status_code=400
        )
        return jsonify(response), status_code

    camera, error_response = require_camera(camera_id)
    if error_response is not None:
        response, status_code = error_response
        return jsonify(response), status_code

    assert camera is not None
    try:
        # Use init_livestream() as specified in IMPLEMENTATION.md
        async def init_stream() -> Any:
            stream = await camera.init_livestream()
            if (
                stream is not None
                and hasattr(stream, "start")
                and hasattr(stream, "feed")
            ):
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
                hls_url, error_msg = stream_manager.start_stream(
                    str(camera_id), tcp_url
                )
            else:
                hls_url = None

            if hls_url is not None:
                # Store the stream object for later cleanup
                if not hasattr(blink_connection, "_active_streams"):
                    blink_connection._active_streams = {}
                active_streams = getattr(blink_connection, "_active_streams", {})
                active_streams[str(camera_id)] = stream

                response, status_code = create_api_response(
                    success=True,
                    data={
                        "tcp_url": tcp_url,
                        "hls_url": hls_url,
                        "stream_id": str(camera_id),
                    },
                )
                return jsonify(response), status_code
            else:
                # Clean up the stream if HLS transcoding failed
                if hasattr(stream, "stop"):
                    try:
                        stream.stop()
                    except Exception as e:
                        logger.warning(f"Error stopping stream during cleanup: {e}")

                response, status_code = create_api_response(
                    success=False,
                    error=Config.ErrorMessages.HLS_TRANSCODING_FAILED,
                    status_code=500,
                )
                return jsonify(response), status_code
        else:
            response, status_code = create_api_response(
                success=False,
                error=Config.ErrorMessages.LIVE_VIEW_FAILED,
                status_code=500,
            )
            return jsonify(response), status_code
    except Exception as e:
        logger.error(f"Error starting livestream for camera {camera_id}: {e}")
        response, status_code = handle_api_error(
            e, f"starting livestream for camera {camera_id}"
        )
        return jsonify(response), status_code


@app.route("/api/camera/<camera_id_str>/liveview/stop", methods=["POST"])
def stop_camera_liveview(camera_id_str: str) -> ResponseReturnValue:
    """Stop live view stream for camera."""
    try:
        camera_id = CameraId(camera_id_str)
    except ValueError as e:
        response, status_code = create_api_response(
            success=False, error=str(e), status_code=400
        )
        return jsonify(response), status_code

    try:
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
                    logger.warning(
                        f"Error stopping livestream for camera {camera_id}: {e}"
                    )
                finally:
                    # Remove from active streams
                    del blink_connection._active_streams[str(camera_id)]

        response, status_code = create_api_response(
            success=True, data={"message": "Livestream stopped successfully"}
        )
        return jsonify(response), status_code

    except Exception as e:
        logger.error(f"Error stopping livestream for camera {camera_id}: {e}")
        response, status_code = handle_api_error(
            e, f"stopping livestream for camera {camera_id}"
        )
        return jsonify(response), status_code


@app.route("/api/hls/<camera_id_str>/<path:filename>")
def serve_hls_file(camera_id_str: str, filename: str) -> ResponseReturnValue:
    """Serve HLS playlist and segment files."""
    if not stream_manager:
        response, status_code = create_api_response(
            success=False,
            error=Config.ErrorMessages.STREAM_MANAGER_UNAVAILABLE,
            status_code=Config.HTTP_STATUS_SERVICE_UNAVAILABLE,
        )
        return jsonify(response), status_code

    file_path = stream_manager.get_stream_file(camera_id_str, filename)

    if file_path is None:
        response, status_code = create_api_response(
            success=False, error=Config.ErrorMessages.STREAM_NOT_FOUND, status_code=404
        )
        return jsonify(response), status_code

    if filename.endswith(".m3u8"):
        file_response = send_file(
            str(file_path), mimetype="application/vnd.apple.mpegurl"
        )
        return file_response
    elif filename.endswith(".ts"):
        file_response = send_file(str(file_path), mimetype="video/mp2t")
        return file_response
    else:
        response, status_code = create_api_response(
            success=False, error=Config.ErrorMessages.INVALID_FILE_TYPE, status_code=400
        )
        return jsonify(response), status_code


@app.route("/api/clip/<clip_id_str>/thumbnail")
def get_clip_thumbnail(clip_id_str: str) -> ResponseReturnValue:
    clip_id, error_response = parse_clip_id(clip_id_str)
    if error_response is not None:
        api_response, status_code = error_response
        return jsonify(api_response), status_code
    """Serve clip thumbnail."""
    cached_clip = clips_download_cache.get(clip_id)
    if cached_clip is not None:
        thumbnail_path = cached_clip.get("thumbnail")
        if thumbnail_path is not None and thumbnail_path.exists():
            response = send_file(str(thumbnail_path), mimetype="image/jpeg")
            return response, 200

    api_response, status_code = create_api_response(
        success=False, error=Config.ErrorMessages.THUMBNAIL_NOT_FOUND, status_code=404
    )
    return jsonify(api_response), status_code


@app.route("/api/camera/<camera_id_str>/thumbnail/timestamp")
@requires_blink
def get_camera_thumbnail_timestamp(camera_id_str: str) -> ResponseReturnValue:
    """Get camera thumbnail timestamp for polling.

    Args:
        camera_id_str: String representation of the camera ID

    Returns:
        JSON response with thumbnail timestamp or error message

    Raises:
        ValueError: If camera_id_str is invalid
    """
    try:
        camera_id = CameraId(camera_id_str)
    except ValueError as e:
        response, status_code = create_api_response(
            success=False, error=str(e), status_code=400
        )
        return jsonify(response), status_code

    camera = find_camera_by_id(camera_id)
    if camera is None:
        response, status_code = create_api_response(
            success=False, error=Config.ErrorMessages.CAMERA_NOT_FOUND, status_code=404
        )
        return jsonify(response), status_code

    timestamp = extract_thumbnail_timestamp(camera.thumbnail)
    logger.info(
        f"Camera {camera_id} thumbnail timestamp: {timestamp}, URL: {camera.thumbnail}"
    )
    response, status_code = create_api_response(
        success=True, data={"timestamp": timestamp}
    )
    return jsonify(response), status_code


@app.route("/api/camera/<camera_id_str>/thumbnail")
@requires_blink
def get_camera_thumbnail(camera_id_str: str) -> ResponseReturnValue:
    """Proxy camera thumbnail with authentication.

    Args:
        camera_id_str: String representation of the camera ID

    Returns:
        JPEG image file or JSON error response

    Raises:
        ValueError: If camera_id_str is invalid
    """
    try:
        camera_id = CameraId(camera_id_str)
    except ValueError as e:
        response, status_code = create_api_response(
            success=False, error=str(e), status_code=400
        )
        return jsonify(response), status_code

    camera = find_camera_by_id(camera_id)
    if camera is None or camera.thumbnail is None:
        response, status_code = create_api_response(
            success=False,
            error=Config.ErrorMessages.CAMERA_THUMBNAIL_NOT_FOUND,
            status_code=404,
        )
        return jsonify(response), status_code

    try:
        # Check cache first
        cached_thumbnail = thumbnail_cache.get(camera_id)
        if cached_thumbnail is not None:
            logger.debug(f"Serving cached thumbnail for camera {camera_id}")
            filename = cached_thumbnail["filename"]
            assert THUMBNAIL_CACHE_DIR is not None
            filepath = Path(cast(str, THUMBNAIL_CACHE_DIR)) / filename
            if filepath.exists():
                file_response = send_file(str(filepath), mimetype="image/jpeg")
                return response, 200
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
            response, status_code = create_api_response(
                success=False,
                error=Config.ErrorMessages.THUMBNAIL_FETCH_FAILED,
                status_code=500,
            )
            return jsonify(response), status_code
    except Exception as e:
        response, status_code = handle_api_error(
            e, f"fetching thumbnail for camera {camera_id}"
        )
        return jsonify(response), status_code


def notify_thumbnail_ready(clip_id: ClipId) -> None:
    """Thumbnail ready notification (no longer needed with polling approach)."""
    logger.debug(f"Thumbnail ready for clip: {clip_id}")


@app.route("/api/config")
def get_config() -> ResponseReturnValue:
    """Get client-side configuration constants.

    Returns configuration values needed by the JavaScript frontend.
    This allows centralizing timing and polling constants in the Config class.
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

    response, status_code = create_api_response(success=True, data=config_data)
    return jsonify(response), status_code


@app.route("/placeholder")
def placeholder() -> ResponseReturnValue:
    """Show placeholder message."""
    response, status_code = create_api_response(
        success=False,
        error=Config.ErrorMessages.FEATURE_NOT_AVAILABLE,
        status_code=Config.HTTP_STATUS_NOT_IMPLEMENTED,
    )
    return jsonify(response), status_code


async def load_saved_blink() -> bool:
    """Load Blink system from saved credentials file.

    Returns:
        True if successfully loaded, False otherwise
    """
    global blink
    assert CREDENTIALS_FILE is not None
    cred_file = Path(cast(str, CREDENTIALS_FILE))
    if cred_file.exists():
        try:
            from aiohttp import ClientSession

            from blinkpy.helpers.util import json_load

            assert CREDENTIALS_FILE is not None
            # Type ignore for mypy issue with blinkpy's json_load function
            auth_data: dict[str, Any] | None = await json_load(
                cast(str, CREDENTIALS_FILE)
            )  # type: ignore[misc]
            session = ClientSession()
            auth = Auth(auth_data, session=session)
            blink = Blink(session=session)
            blink.auth = auth
            success = await blink.start()
            if success is True:
                logger.info("Blink system loaded from saved credentials")
                return True
            else:
                logger.warning("Failed to load Blink system from saved credentials")
                await session.close()
                return False
        except Exception as e:
            logger.warning(f"Could not load Blink system from saved credentials: {e}")
            if "session" in locals():
                await session.close()
            return False
    return False


def dump_cloud_videos(videos: list[dict[str, Any]]) -> None:
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
    global stream_manager

    try:
        # Initialize cache paths
        initialize_cache_paths()

        # Create cache directories if they don't exist
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
    assert THUMBNAIL_CACHE_DIR is not None
    cache_dir = Path(cast(str, THUMBNAIL_CACHE_DIR))
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
def settings() -> ResponseReturnValue:
    """Get or save application settings.

    GET: Returns current user settings (temperature units, clip retention, etc.)
    POST: Updates settings with provided JSON data

    Settings are persisted to cache/settings.json and survive logout/restart.
    """
    if request.method == "GET":
        try:
            assert SETTINGS_FILE is not None
            settings_file = Path(cast(str, SETTINGS_FILE))
            if settings_file.exists():
                import json

                with open(settings_file) as f:
                    settings_data = json.load(f)
            else:
                settings_data = {
                    "temperatureUnits": "celsius",
                    "cloudClipRetention": "30",
                    "localClipRetention": "never",
                    "clipThumbnailSize": "medium",
                }

            response, status_code = create_api_response(
                success=True, data=settings_data
            )
            return jsonify(response), status_code
        except Exception as e:
            response, status_code = handle_api_error(e, "loading settings")
            return jsonify(response), status_code

    else:  # POST
        try:
            data = request.get_json()
            if not isinstance(data, dict):
                response, status_code = create_api_response(
                    success=False,
                    error=Config.ErrorMessages.INVALID_JSON_DATA,
                    status_code=400,
                )
                return jsonify(response), status_code

            # Load existing settings
            assert SETTINGS_FILE is not None
            settings_file = Path(cast(str, SETTINGS_FILE))
            if settings_file.exists():
                import json

                with open(settings_file) as f:
                    settings_data = json.load(f)
            else:
                settings_data = {}

            # Update settings
            settings_data.update(data)

            # Save settings
            import json

            with open(settings_file, "w") as f:
                json.dump(settings_data, f, indent=2)

            response, status_code = create_api_response(
                success=True, data={"message": "Settings saved"}
            )
            return jsonify(response), status_code
        except Exception as e:
            response, status_code = handle_api_error(e, "saving settings")
            return jsonify(response), status_code


@app.route("/api/clip/<clip_id_str>/thumbnail/check")
def check_clip_thumbnail(clip_id_str: str) -> ResponseReturnValue:
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
        executor.shutdown(wait=False)

        # Shutdown stream manager if initialized
        if stream_manager is not None:
            stream_manager.shutdown()

        # Clean up active livestreams
        if hasattr(blink_connection, "_active_streams"):
            for stream_id, stream in blink_connection._active_streams.items():
                try:
                    if hasattr(stream, "stop"):
                        stream.stop()
                        logger.info(f"Stopped active livestream {stream_id}")
                except (AttributeError, RuntimeError, OSError) as e:
                    logger.warning(f"Error stopping livestream {stream_id}: {e}")
            blink_connection._active_streams.clear()

        # Clean up Blink session only if connection is active
        if blink and blink_connection.loop and blink_connection.loop.is_running():
            try:
                blink_connection.execute(cleanup_blink_session())
            except (RuntimeError, ConnectionError, TimeoutError) as e:
                logger.debug(f"Error during Blink session cleanup: {e}")

        # Shutdown Blink connection
        blink_connection.shutdown()

        # Close HTTP session
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


def main() -> None:
    """Main entry point with command line argument parsing."""
    import argparse

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


if __name__ == "__main__":
    main()
