"""Thread-safe caching module for Blink Flask application.

This module provides thread-safe cache implementations using a generic wrapper
approach. ThreadSafeCache provides thread-safety for any cache implementation
through multiple inheritance.
"""

import logging
import threading
import time
from typing import Any, TypeVar

from cachetools import Cache, LRUCache

# Generic type variable for cache implementation
CacheImpl = TypeVar("CacheImpl", bound=Cache)

logger = logging.getLogger(__name__)


class ThreadSafeCache[CacheImpl](Cache):
    """Thread-safe cache wrapper using multiple inheritance.

    This class provides thread-safe access to any cache implementation
    through a lock. The actual cache implementation is specified when
    creating specialized subclasses.

    Attributes:
        _lock: Threading RLock for synchronizing access to cache operations

    Example:
        >>> class MyLRUCache(ThreadSafeCache[LRUCache], LRUCache):
        ...     pass
        >>> cache = MyLRUCache(maxsize=50)
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize cache with thread safety.

        Args:
            *args: Arguments passed to the underlying cache implementation
            **kwargs: Keyword arguments passed to the underlying cache implementation
        """
        super().__init__(*args, **kwargs)
        # Use RLock to allow recursive locking from same thread
        self._lock = threading.RLock()

    def __setitem__(self, key, value) -> None:
        """Thread-safe setitem method."""
        with self._lock:
            super().__setitem__(key, value)

    def __getitem__(self, key):
        """Thread-safe getitem method."""
        with self._lock:
            return super().__getitem__(key)

    def __delitem__(self, key) -> None:
        """Thread-safe delitem method."""
        with self._lock:
            super().__delitem__(key)

    def __contains__(self, key) -> bool:
        """Thread-safe contains method for membership testing."""
        with self._lock:
            return super().__contains__(key)

    def __len__(self) -> int:
        """Thread-safe len method for getting cache size."""
        with self._lock:
            return super().__len__()

    def __iter__(self):
        """Thread-safe iterator over cache keys."""
        with self._lock:
            # Create a list to avoid iteration during lock
            return iter(list(super().keys()))

    def get(self, key, default=None):
        """Thread-safe get method with optional default value."""
        with self._lock:
            return super().get(key, default)

    def pop(self, key, *args):
        """Thread-safe pop method."""
        with self._lock:
            return super().pop(key, *args)

    def setdefault(self, key, default=None):
        """Thread-safe setdefault method."""
        with self._lock:
            return super().setdefault(key, default)

    def clear(self) -> None:
        """Thread-safe clear method to remove all items."""
        with self._lock:
            super().clear()

    def keys(self):
        """Thread-safe keys method."""
        with self._lock:
            return list(super().keys())

    def values(self):
        """Thread-safe values method."""
        with self._lock:
            return list(super().values())

    def items(self):
        """Thread-safe items method."""
        with self._lock:
            return list(super().items())

    def get_stats(self) -> dict[str, int | float]:
        """Get cache statistics.

        Returns:
            Dictionary containing cache statistics including size,
            hit rate, and other performance metrics
        """
        with self._lock:
            return {
                "size": len(self),
                "maxsize": getattr(self, "maxsize", 0),
                "hits": getattr(self, "hits", 0),
                "misses": getattr(self, "misses", 0),
                "hit_rate": (
                    getattr(self, "hits", 0)
                    / max(getattr(self, "hits", 0) + getattr(self, "misses", 0), 1)
                ),
            }


class ThumbnailCache(ThreadSafeCache[LRUCache], LRUCache):
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


class ClipsCache(ThreadSafeCache[LRUCache], LRUCache):
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

        Stores clip data with additional tracking metadata for cache management
        including access statistics and timestamps for cleanup operations.

        Args:
            clip_id: Unique clip identifier
            clip_data: Clip information and metadata from Blink API
        """
        enhanced_data = {
            "clip_data": clip_data,
            "cached_at": time.time(),  # When clip was added to cache
            "access_count": 0,  # Track access frequency
            "last_accessed": time.time(),  # Most recent access time
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


def initialize_caches(config: dict[str, Any]) -> None:
    """Initialize global cache instances with configuration.

    Args:
        config: Configuration dictionary with cache settings
    """
    global thumbnail_cache, clips_cache

    thumbnail_cache = ThumbnailCache(maxsize=config.get("thumbnail_cache_size", 100))
    clips_cache = ClipsCache(maxsize=config.get("clips_cache_size", 50))

    logger.info("Cache instances initialized successfully")


def clear_all_caches() -> None:
    """Clear all cache instances."""
    if thumbnail_cache:
        thumbnail_cache.clear()
    if clips_cache:
        clips_cache.clear()

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

    return stats
