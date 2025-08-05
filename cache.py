"""Thread-safe caching module for Blink Flask application.

This module provides thread-safe cache implementations with proper inheritance
from cachetools.LRUCache. The ThreadSafeCache class directly overrides LRUCache
methods with thread-safe versions, eliminating the need for separate safe_* methods.
"""

import logging
import threading
import time
from typing import Any, Generic, TypeVar

from cachetools import LRUCache

# Generic type variables for flexible cache typing
K = TypeVar("K")  # Key type
V = TypeVar("V")  # Value type

logger = logging.getLogger(__name__)


class ThreadSafeCache(LRUCache[K, V], Generic[K, V]):
    """Thread-safe LRU cache with direct method overrides.

    This class properly inherits from cachetools.LRUCache and directly overrides
    all methods with thread-safe versions. This eliminates the need for separate
    safe_* methods and provides a clean, standard dict-like interface.

    The cache uses LRU (Least Recently Used) eviction policy to automatically
    manage memory usage when the cache reaches its maximum size.

    Attributes:
        _lock: Threading RLock for synchronizing access to cache operations

    Example:
        >>> cache = ThreadSafeCache[str, dict[str, Any]](maxsize=50)
        >>> cache["key1"] = {"data": "value1"}
        >>> result = cache.get("key1", {})
        >>> if "key2" in cache:
        ...     value = cache["key2"]
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

    def __setitem__(self, key: K, value: V) -> None:
        """Thread-safe setitem method.

        Args:
            key: Cache key to set
            value: Value to store
        """
        with self._lock:
            super().__setitem__(key, value)

    def __getitem__(self, key: K) -> V:
        """Thread-safe getitem method.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached value

        Raises:
            KeyError: If key not found in cache
        """
        with self._lock:
            return super().__getitem__(key)

    def __delitem__(self, key: K) -> None:
        """Thread-safe delitem method.

        Args:
            key: Cache key to delete

        Raises:
            KeyError: If key not found in cache
        """
        with self._lock:
            super().__delitem__(key)

    def __contains__(self, key: object) -> bool:
        """Thread-safe contains check.

        Args:
            key: Cache key to check

        Returns:
            True if key exists in cache
        """
        with self._lock:
            return super().__contains__(key)

    def __len__(self) -> int:
        """Thread-safe len method for getting cache size."""
        with self._lock:
            return super().__len__()

    def get(self, key: K, default: V | None = None) -> V | None:
        """Thread-safe get method with optional default value.

        Args:
            key: Cache key to retrieve
            default: Default value if key not found

        Returns:
            Cached value or default if key not found
        """
        with self._lock:
            return super().get(key, default)

    def pop(self, key: K, default: V | None = None) -> V | None:
        """Thread-safe pop method.

        Args:
            key: Cache key to remove
            default: Default value if key not found

        Returns:
            Removed value or default
        """
        with self._lock:
            return super().pop(key, default)

    def popitem(self) -> tuple[K, V]:
        """Thread-safe popitem method.

        Returns:
            Removed key-value pair

        Raises:
            KeyError: If cache is empty
        """
        with self._lock:
            return super().popitem()

    def clear(self) -> None:
        """Thread-safe clear method for removing all items."""
        with self._lock:
            super().clear()

    def keys(self):
        """Thread-safe keys method.

        Returns:
            Keys view (snapshot at call time)
        """
        with self._lock:
            return list(super().keys())

    def values(self):
        """Thread-safe values method.

        Returns:
            Values view (snapshot at call time)
        """
        with self._lock:
            return list(super().values())

    def items(self):
        """Thread-safe items method.

        Returns:
            Items view (snapshot at call time)
        """
        with self._lock:
            return list(super().items())

    def setdefault(self, key: K, default: V | None = None) -> V | None:
        """Thread-safe setdefault method.

        Args:
            key: Cache key
            default: Default value to set if key doesn't exist

        Returns:
            Existing value or default
        """
        with self._lock:
            return super().setdefault(key, default)

    def update(self, *args, **kwargs) -> None:
        """Thread-safe update method.

        Args:
            *args: Positional arguments for update
            **kwargs: Keyword arguments for update
        """
        with self._lock:
            super().update(*args, **kwargs)

    def clear_cache(self) -> None:
        """Clear all cached items.

        This method provides a consistent interface for cache clearing
        across all cache implementations in the application.
        """
        self.clear()

    def get_stats(self) -> dict[str, int | float]:
        """Get cache statistics.

        Returns:
            Dictionary with cache size and capacity information
        """
        with self._lock:
            return {
                "size": len(self),
                "maxsize": self.maxsize,
            }


class ThumbnailCache(ThreadSafeCache[str, dict[str, Any]]):
    """Specialized cache for camera thumbnails with timestamp tracking.

    Extends ThreadSafeCache with thumbnail-specific functionality including
    timestamp tracking and freshness checking for camera thumbnail images.
    """

    def __init__(self, maxsize: int = 100) -> None:
        """Initialize thumbnail cache.

        Args:
            maxsize: Maximum number of thumbnails to cache
        """
        super().__init__(maxsize=maxsize)

    def get_thumbnail_timestamp(self, camera_id: str) -> float | None:
        """Get timestamp for cached thumbnail.

        Args:
            camera_id: Camera identifier

        Returns:
            Timestamp when thumbnail was cached, or None if not found
        """
        thumbnail_data = self.get(camera_id)
        if thumbnail_data and "timestamp" in thumbnail_data:
            timestamp_obj = thumbnail_data["timestamp"]
            if isinstance(timestamp_obj, int | float):
                return float(timestamp_obj)
        return None

    def is_thumbnail_fresh(self, camera_id: str, max_age_seconds: int = 300) -> bool:
        """Check if cached thumbnail is still fresh.

        Args:
            camera_id: Camera identifier
            max_age_seconds: Maximum age in seconds before thumbnail is stale

        Returns:
            True if thumbnail exists and is within max age
        """
        timestamp = self.get_thumbnail_timestamp(camera_id)
        if timestamp is None:
            return False
        return (time.time() - timestamp) < max_age_seconds

    def update_thumbnail(
        self,
        camera_id: str,
        thumbnail_data: bytes,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update thumbnail with current timestamp.

        Args:
            camera_id: Camera identifier
            thumbnail_data: Raw thumbnail image data
            metadata: Optional metadata to store with thumbnail
        """
        cache_entry = {
            "data": thumbnail_data,
            "timestamp": time.time(),
            "metadata": metadata or {},
        }
        self[camera_id] = cache_entry


class ClipsCache(ThreadSafeCache[str, dict[str, Any]]):
    """Specialized cache for video clips with metadata and access tracking.

    Extends ThreadSafeCache with clip-specific functionality including
    access counting, age tracking, and automatic cleanup of old clips.
    """

    def __init__(self, maxsize: int = 50) -> None:
        """Initialize clips cache.

        Args:
            maxsize: Maximum number of clips to cache
        """
        super().__init__(maxsize=maxsize)

    def add_clip(self, clip_id: str, clip_data: dict[str, Any]) -> None:
        """Add clip with automatic metadata enhancement.

        Args:
            clip_id: Unique clip identifier
            clip_data: Clip information and metadata
        """
        enhanced_data = {
            "clip_data": clip_data,
            "cached_at": time.time(),
            "access_count": 0,
            "last_accessed": time.time(),
        }
        self[clip_id] = enhanced_data

    def get_clip(self, clip_id: str) -> dict[str, Any] | None:
        """Get clip and update access statistics.

        Args:
            clip_id: Unique clip identifier

        Returns:
            Clip data if found, None otherwise
        """
        clip_entry = self.get(clip_id)
        if clip_entry:
            # Update access statistics
            access_count = clip_entry.get("access_count", 0)
            if isinstance(access_count, int):
                clip_entry["access_count"] = access_count + 1
            clip_entry["last_accessed"] = time.time()

            # Update the cache with new stats
            self[clip_id] = clip_entry

            # Return the actual clip data
            clip_data = clip_entry.get("clip_data")
            if isinstance(clip_data, dict):
                return clip_data
        return None

    def cleanup_old_clips(self, max_age_hours: int = 24) -> int:
        """Remove clips older than specified age.

        Args:
            max_age_hours: Maximum age in hours before clips are removed

        Returns:
            Number of clips removed
        """
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        old_clips = []

        for clip_id, clip_entry in self.items():
            if isinstance(clip_entry, dict):
                cached_at = clip_entry.get("cached_at", 0)
                if (
                    isinstance(cached_at, int | float)
                    and (current_time - cached_at) > max_age_seconds
                ):
                    old_clips.append(clip_id)

        for clip_id in old_clips:
            del self[clip_id]

        if old_clips:
            logger.info(f"Cleaned up {len(old_clips)} old clips from cache")
        return len(old_clips)


# Global cache instances (initialized by app.py)
thumbnail_cache: ThumbnailCache | None = None
clips_cache: ClipsCache | None = None
settings_cache: ThreadSafeCache[str, dict[str, Any]] | None = None


def initialize_caches(config: dict[str, Any]) -> None:
    """Initialize global cache instances with configuration.

    Args:
        config: Configuration dictionary with cache settings
    """
    global thumbnail_cache, clips_cache, settings_cache

    thumbnail_cache = ThumbnailCache(maxsize=config.get("thumbnail_cache_size", 100))
    clips_cache = ClipsCache(maxsize=config.get("clips_cache_size", 50))
    settings_cache = ThreadSafeCache[str, dict[str, Any]](
        maxsize=config.get("settings_cache_size", 10)
    )

    logger.info("Cache instances initialized successfully")


def clear_all_caches() -> None:
    """Clear all cache instances."""
    if thumbnail_cache:
        thumbnail_cache.clear()
    if clips_cache:
        clips_cache.clear()
    if settings_cache:
        settings_cache.clear()

    logger.info("All caches cleared")


def get_cache_stats() -> dict[str, dict[str, int | float]]:
    """Get statistics for all cache instances.

    Returns:
        Dictionary with statistics for each cache type
    """
    stats = {}

    if thumbnail_cache:
        stats["thumbnail_cache"] = thumbnail_cache.get_stats()

    if clips_cache:
        stats["clips_cache"] = clips_cache.get_stats()

    if settings_cache:
        stats["settings_cache"] = settings_cache.get_stats()

    return stats
