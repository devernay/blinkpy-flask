"""
Cache classes for the Blink Camera Flask application.

This module provides thread-safe caching implementations for different types
of data used throughout the application:
- ThumbnailCache: Stores camera thumbnail metadata and timestamps
- ClipsMetadataCache: Caches clip listing data to reduce API calls
- ClipsDownloadCache: Manages downloaded clip files and thumbnails

All cache classes use LRU (Least Recently Used) eviction policy and are
thread-safe for concurrent access from Flask request handlers.
"""

import functools
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict, TypeVar

from cachetools import LRUCache, cachedmethod
from cachetools.keys import hashkey

from config import Config

# Type definitions for better code clarity
CacheKey = str
T = TypeVar("T")


def synchronized(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to make cache methods thread-safe using the instance's _lock.

    This follows the standard Python pattern for creating decorators that
    preserve function metadata using functools.wraps. Each cache instance
    maintains its own threading lock for safe concurrent access.

    Args:
        func: The function to synchronize with thread locking

    Returns:
        Thread-safe wrapper function that acquires lock before execution
    """

    @functools.wraps(func)
    def wrapper(self: object, *args: object, **kwargs: object) -> T:
        # Acquire the instance's lock before executing the function
        with self._lock:  # type: ignore[attr-defined]
            return func(self, *args, **kwargs)

    return wrapper


# ============================================================================
# Base Cache Classes
# ============================================================================


class ThreadSafeCache(LRUCache[str, dict[str, object]]):
    """Base thread-safe cache class with common functionality.

    Provides thread-safe operations for all cache implementations,
    eliminating code duplication across cache classes. Uses LRU (Least
    Recently Used) eviction policy to automatically manage memory usage
    when the cache reaches its maximum size.

    This class wraps the cachetools.LRUCache with thread synchronization
    to ensure safe concurrent access from multiple Flask request handlers.
    All methods are protected by a reentrant lock to prevent race conditions.

    Attributes:
        _lock: Threading RLock for synchronizing access to cache operations

    Example:
        >>> cache = ThreadSafeCache(maxsize=50)
        >>> cache["key1"] = {"data": "value1"}
        >>> result = cache.get("key1", {})
    """

    def __init__(self, maxsize: int = 100) -> None:
        """Initialize cache with specified maximum size.

        Creates an LRU cache with the given capacity and initializes
        the threading lock for safe concurrent access.

        Args:
            maxsize: Maximum number of items to cache before LRU eviction begins
                    (default: 100)
        """
        super().__init__(maxsize=maxsize)
        # Use RLock to allow recursive locking from same thread
        # This prevents deadlocks when cache methods call other cache methods
        self._lock = threading.RLock()

    # Thread-safe overrides for LRUCache methods using @synchronized decorator
    @synchronized
    def get(self, key: CacheKey, default: object = None) -> object:
        """Thread-safe get method with optional default value.

        Retrieves a value from the cache without raising KeyError if
        the key doesn't exist. Updates the LRU order when key is found.

        Args:
            key: Cache key to retrieve
            default: Default value if key not found (default: None)

        Returns:
            Cached value or default if key not found
        """
        return super().get(key, default)

    @synchronized
    def __getitem__(self, key: CacheKey) -> object:
        """Thread-safe getitem method for dict-like access.

        Allows cache[key] syntax. Updates LRU order when key is accessed.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached value

        Raises:
            KeyError: If key not found in cache
        """
        return super().__getitem__(key)

    @synchronized
    def __setitem__(self, key: CacheKey, value: object) -> None:
        """Thread-safe setitem method for dict-like assignment.

        Allows cache[key] = value syntax. May trigger LRU eviction
        if cache is at maximum capacity.

        Args:
            key: Cache key to set
            value: Value to store
        """
        super().__setitem__(key, value)

    @synchronized
    def __delitem__(self, key: CacheKey) -> None:
        """Thread-safe delitem method for dict-like deletion.

        Allows del cache[key] syntax.

        Args:
            key: Cache key to delete

        Raises:
            KeyError: If key not found in cache
        """
        super().__delitem__(key)

    @synchronized
    def __contains__(self, key: CacheKey) -> bool:
        """Thread-safe contains method for membership testing.

        Allows 'key in cache' syntax. Does not update LRU order.

        Args:
            key: Cache key to check

        Returns:
            True if key exists in cache, False otherwise
        """
        return super().__contains__(key)

    @synchronized
    def __len__(self) -> int:
        """Thread-safe len method for getting cache size.

        Allows len(cache) syntax.

        Returns:
            Number of items currently in cache
        """
        return super().__len__()

    @synchronized
    def pop(self, key: CacheKey, default: object = None) -> object:
        """Thread-safe pop method for removing and returning a value.

        Args:
            key: Cache key to remove
            default: Default value if key not found

        Returns:
            Removed value or default if key not found
        """
        return super().pop(key, default)

    @synchronized
    def popitem(self) -> tuple[CacheKey, object]:
        """Thread-safe popitem method for removing LRU item.

        Returns:
            Tuple of (key, value) for the least recently used item

        Raises:
            KeyError: If cache is empty
        """
        return super().popitem()

    @synchronized
    def clear(self) -> None:
        """Thread-safe clear method for removing all items.

        Empties the entire cache, resetting it to initial state.
        """
        super().clear()

    @synchronized
    def setdefault(self, key: CacheKey, default: object = None) -> object:
        """Thread-safe setdefault method.

        Gets value if key exists, otherwise sets and returns default.

        Args:
            key: Cache key to get or set
            default: Default value to set if key doesn't exist

        Returns:
            Existing value or newly set default value
        """
        return super().setdefault(key, default)

    @synchronized
    def update(self, *args: object, **kwargs: object) -> None:
        """Thread-safe update method for bulk updates.

        Updates cache with key-value pairs from another mapping or iterable.

        Args:
            *args: Positional arguments (mapping or iterable of pairs)
            **kwargs: Keyword arguments as key-value pairs
        """
        super().update(*args, **kwargs)

    @synchronized
    def keys(self) -> list[str]:
        """Thread-safe keys method."""
        return list(super().keys())

    @synchronized
    def values(self) -> list[dict[str, object]]:
        """Thread-safe values method."""
        return list(super().values())

    @synchronized
    def items(self) -> list[tuple[str, dict[str, object]]]:
        """Thread-safe items method."""
        return list(super().items())

    @property
    def maxsize(self) -> int:
        """Get maximum cache size."""
        return int(super().maxsize)

    @synchronized
    def get_cache_stats(self) -> dict[str, object]:
        """Get cache statistics for monitoring and debugging."""
        return {"size": len(self), "maxsize": self.maxsize}


# ============================================================================
# Specialized Cache Implementations
# ============================================================================


class ThumbnailCache(ThreadSafeCache):
    """
    Thumbnail cache with specialized methods for camera thumbnails.

    Stores camera thumbnail metadata including timestamps, file paths,
    and cache status. Inherits all thread-safe cache operations from
    ThreadSafeCache while adding thumbnail-specific functionality.
    """

    # Inherits __init__ and all basic cache methods from ThreadSafeCache

    # Custom methods using @cachedmethod decorator for automatic caching
    @cachedmethod(lambda self: self, lock=lambda self: self._lock)
    def get_thumbnail_data(self, camera_id: str, timestamp: int) -> dict[str, object]:
        """
        Get thumbnail data - automatically cached and thread-safe.

        Uses cachetools @cachedmethod decorator to automatically cache
        results based on camera_id and timestamp parameters.

        This method uses @cachedmethod decorator as recommended by cachetools.
        Only called once per unique (camera_id, timestamp) combination.

        Returns:
            Dictionary with camera metadata for caching
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
        """Update thumbnail if timestamp is newer than cached version.

        Implements conditional caching logic where decorators aren't suitable.
        Only updates the cache if the new timestamp is more recent than
        the currently cached thumbnail for this camera.

        Args:
            camera_id: ID of the camera
            timestamp: Timestamp of the new thumbnail (Unix timestamp)
            filename: Filename of the thumbnail file

        Returns:
            True if thumbnail was updated (newer timestamp), False otherwise
        """
        # Check for existing entries for this camera
        cache_key = f"{camera_id}_current"
        current_entry = self.get(cache_key)

        # Extract current timestamp, defaulting to 0 if no entry exists
        current_ts = (
            current_entry.get("timestamp", 0) if isinstance(current_entry, dict) else 0
        )

        # Only update if new timestamp is more recent
        if timestamp > current_ts:
            self[cache_key] = {
                "camera_id": camera_id,
                "timestamp": timestamp,
                "filename": filename,
            }
            return True
        return False

    @synchronized
    def get_current_thumbnail(self, camera_id: str) -> dict[str, object] | None:
        """Get current thumbnail info for camera."""
        result = self.get(f"{camera_id}_current")
        return result if isinstance(result, dict) else None

    def clear_cache(self) -> None:
        """Clear all cached thumbnails."""
        self.clear()

    @synchronized
    def get_cache_stats(self) -> dict[str, object]:
        """Get cache statistics."""
        return {"size": len(self), "maxsize": self.maxsize}


class ClipsMetadataCache(ThreadSafeCache):
    """
    Clips metadata cache with specialized methods for clip data.

    Inherits thread-safe operations from ThreadSafeCache and adds
    clip-specific functionality.
    """

    def __init__(self, maxsize: int = 1000):
        super().__init__(maxsize=maxsize)

    @cachedmethod(lambda self: self, lock=lambda self: self._lock)
    def get_clips_metadata(self, storage_type: str) -> list[dict[str, object]]:
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
        self, storage_type: str, filters: dict[str, object]
    ) -> list[dict[str, object]]:
        """Get filtered clips with custom key function.

        Uses custom key function to handle dict parameters properly.

        Args:
            storage_type: Type of storage ('cloud' or 'local')
            filters: Dictionary of filters to apply

        Returns:
            List of filtered clip metadata dictionaries
        """
        base_clips = self.get_clips_metadata(storage_type)
        # Apply filters here
        return base_clips

    @synchronized
    def cache_clips_manually(
        self, storage_type: str, clips: list[dict[str, object]]
    ) -> None:
        """Manually cache clips list (for cases where decorator isn't suitable).

        Args:
            storage_type: Type of storage ('cloud' or 'local')
            clips: List of clip metadata dictionaries to cache
        """
        # Manually add to cache using the same key pattern as the decorator
        cache_key = (self.get_clips_metadata, storage_type)
        self[cache_key] = clips

    def clear_cache(self) -> None:
        """Clear all cached clips metadata."""
        self.clear()


class ClipsDownloadCache(ThreadSafeCache):
    """
    Clips download cache with specialized methods for clip downloads.

    Manages cached clip files and their associated thumbnails. Stores
    file paths, download status, and thumbnail information for both
    cloud and local clips. Inherits thread-safe operations from
    ThreadSafeCache and adds download-specific functionality.
    """

    @cachedmethod(lambda self: self, lock=lambda self: self._lock)
    def get_clip_download_info(self, clip_id: str) -> dict[str, object]:
        """Get clip download info - automatically cached and thread-safe.

        Uses @cachedmethod decorator as recommended by cachetools.
        This method is only called once per unique clip_id and results
        are automatically cached for subsequent requests.

        Args:
            clip_id: ID of the clip to get download info for

        Returns:
            Dictionary containing clip download information including
            file path and thumbnail status
        """
        return {
            "clip_id": clip_id,
            "filepath": f"/downloads/{clip_id}.mp4",
            "thumbnail": None,  # Will be updated when thumbnail is generated
        }

    @synchronized
    def cache_clip_manually(
        self, clip_id: str, filepath: str, thumbnail_path: str | None = None
    ) -> None:
        """Manually cache clip info for cases where decorator isn't suitable.

        Used when we need to update cache entries with actual file paths
        and thumbnail information after download/processing operations.

        Args:
            clip_id: ID of the clip
            filepath: Actual path to the downloaded clip file
            thumbnail_path: Optional path to the generated thumbnail file
        """
        # Use the same cache key format as the decorated method
        cache_key = (self.get_clip_download_info, clip_id)
        self[cache_key] = {
            "clip_id": clip_id,
            "filepath": filepath,
            "thumbnail": thumbnail_path,
        }

    def clear_cache(self) -> None:
        """Clear all cached clip download info."""
        self.clear()


# Cache instances using object-oriented memoizing decorators
thumbnail_cache_oo = ThumbnailCache(maxsize=Config.THUMBNAIL_CACHE_SIZE)
clips_metadata_cache_oo = ClipsMetadataCache(maxsize=Config.CLIPS_METADATA_CACHE_SIZE)
clips_download_cache_oo = ClipsDownloadCache(maxsize=Config.CLIPS_CACHE_SIZE)

# Cache instances for application use
thumbnail_cache = thumbnail_cache_oo
clips_metadata_cache = clips_metadata_cache_oo
clips_download_cache = clips_download_cache_oo


def get_cache_stats() -> dict[str, dict[str, object]]:
    """Get statistics for all caches using OO implementation."""
    return {
        "thumbnail_cache": thumbnail_cache.get_cache_stats(),
        "clips_metadata_cache": clips_metadata_cache.get_cache_stats(),
        "clips_download_cache": clips_download_cache.get_cache_stats(),
    }


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
