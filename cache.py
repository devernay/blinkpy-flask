"""Thread-safe caching module for Blink Flask application.

This module provides thread-safe cache implementations with proper inheritance
from cachetools.LRUCache while maintaining full type safety.

The solution avoids mypy signature conflicts by not overriding methods that
have complex generic signatures, instead providing thread-safe access through
context managers and helper methods.
"""

import logging
import threading
import time
from typing import Any, TypeAlias

from cachetools import LRUCache

# Type aliases for better readability
CacheKey: TypeAlias = str
CacheValue: TypeAlias = dict[str, object]

logger = logging.getLogger(__name__)


def synchronized(func):
    """Decorator for thread-safe method execution.

    This decorator is kept for backwards compatibility but should not be used
    on methods that override parent class methods due to mypy signature conflicts.
    """

    def wrapper(self, *args, **kwargs):
        with self._lock:
            return func(self, *args, **kwargs)

    return wrapper


class ThreadSafeCache(LRUCache[str, dict[str, object]]):
    """Thread-safe LRU cache with method access control.

    This class properly inherits from cachetools.LRUCache while providing
    thread safety. It invalidates direct access to unsafe methods and provides
    safe alternatives, ensuring all cache operations are thread-safe.

    The cache uses LRU (Least Recently Used) eviction policy to automatically
    manage memory usage when the cache reaches its maximum size.

    Attributes:
        _lock: Threading RLock for synchronizing access to cache operations
        _lock_holder: Thread-local storage to track lock ownership

    Example:
        >>> cache = ThreadSafeCache(maxsize=50)
        >>> # Recommended: Use safe methods
        >>> cache.safe_set("key1", {"data": "value1"})
        >>> result = cache.safe_get("key1", {})
        >>>
        >>> # Or use context manager for multiple operations
        >>> with cache.lock():
        ...     cache["key2"] = {"data": "value2"}
        ...     value = cache.get("key1")  # Only works within context
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
        # Thread-local storage to track lock ownership
        self._lock_holder = threading.local()

    def lock(self):
        """Get the lock context manager for thread-safe operations.

        Returns:
            Context manager that enables safe direct method access

        Example:
            >>> with cache.lock():
            ...     cache["key"] = {"data": "value"}
            ...     value = cache.get("key")
        """
        return self._LockContext(self)

    class _LockContext:
        """Context manager for thread-safe cache access."""

        def __init__(self, cache):
            self.cache = cache

        def __enter__(self):
            self.cache._lock.acquire()
            self.cache._lock_holder.has_lock = True
            return self.cache

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.cache._lock_holder.has_lock = False
            self.cache._lock.release()

    def _check_lock_context(self, method_name: str) -> None:
        """Check if method is called within proper lock context.

        Args:
            method_name: Name of the method being called

        Raises:
            RuntimeError: If method is called outside lock context
        """
        # Allow calls when we already hold the lock (from safe methods or context manager)
        if getattr(self._lock_holder, "has_lock", False):
            return

        # Block direct calls without proper synchronization
        safe_method = f"safe_{method_name.replace('__', '').replace('getitem', 'get').replace('setitem', 'set')}"
        raise RuntimeError(
            f"Direct use of {method_name}() is not thread-safe. "
            f"Use {safe_method}() or access within lock() context."
        )

    # Override only the setitem method (simpler signature, no mypy conflicts)
    def __setitem__(self, key: str, value: dict[str, object]) -> None:
        """Context-aware setitem method.

        This method can only be called within a lock() context manager.
        For automatic thread safety, use safe_set() instead.

        Args:
            key: Cache key to set
            value: Value to store

        Raises:
            RuntimeError: If called outside lock() context
        """
        self._check_lock_context("__setitem__")
        super().__setitem__(key, value)

    def __getitem__(self, key: str) -> dict[str, object]:
        """Context-aware getitem method.

        This method can only be called within a lock() context manager.
        For automatic thread safety, use safe_get() instead.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached value

        Raises:
            KeyError: If key not found in cache
            RuntimeError: If called outside lock() context
        """
        self._check_lock_context("__getitem__")
        return super().__getitem__(key)

    # Don't override get() to avoid mypy conflicts, but provide safe alternative
    # The parent get() method will call __getitem__ which we do control

    # Override only the simplest methods to avoid signature conflicts
    def __len__(self) -> int:
        """Thread-safe len method for getting cache size."""
        with self._lock:
            return super().__len__()

    def clear(self) -> None:
        """Thread-safe clear method for removing all items."""
        with self._lock:
            super().clear()

    # Provide thread-safe helper methods with simple signatures
    def safe_get(
        self, key: str, default: dict[str, object] | None = None
    ) -> dict[str, object] | None:
        """Thread-safe get method with optional default value.

        Args:
            key: Cache key to retrieve
            default: Default value if key not found

        Returns:
            Cached value or default if key not found
        """
        with self._lock:
            # Set the flag to indicate we hold the lock
            self._lock_holder.has_lock = True
            try:
                return super().get(key, default)
            finally:
                self._lock_holder.has_lock = False

    def safe_set(self, key: str, value: dict[str, object]) -> None:
        """Thread-safe set method.

        Args:
            key: Cache key to set
            value: Value to store
        """
        with self._lock:
            # Set the flag to indicate we hold the lock
            self._lock_holder.has_lock = True
            try:
                super().__setitem__(key, value)
            finally:
                self._lock_holder.has_lock = False

    def safe_delete(self, key: str) -> bool:
        """Thread-safe delete method.

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted, False if key didn't exist
        """
        with self._lock:
            try:
                super().__delitem__(key)
                return True
            except KeyError:
                return False

    def safe_contains(self, key: str) -> bool:
        """Thread-safe contains check.

        Args:
            key: Cache key to check

        Returns:
            True if key exists in cache
        """
        with self._lock:
            return super().__contains__(key)

    def safe_pop(
        self, key: str, default: dict[str, object] | None = None
    ) -> dict[str, object] | None:
        """Thread-safe pop method.

        Args:
            key: Cache key to remove
            default: Default value if key not found

        Returns:
            Removed value or default
        """
        with self._lock:
            return super().pop(key, default)

    def safe_keys(self) -> list[str]:
        """Thread-safe keys method.

        Returns:
            List of all cache keys (snapshot at call time)
        """
        with self._lock:
            return list(super().keys())

    def safe_values(self) -> list[dict[str, object]]:
        """Thread-safe values method.

        Returns:
            List of all cache values (snapshot at call time)
        """
        with self._lock:
            return list(super().values())

    def safe_items(self) -> list[tuple[str, dict[str, object]]]:
        """Thread-safe items method.

        Returns:
            List of all cache key-value pairs (snapshot at call time)
        """
        with self._lock:
            return list(super().items())

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


class ThumbnailCache(ThreadSafeCache):
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
        thumbnail_data = self.safe_get(camera_id)
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
        self.safe_set(camera_id, cache_entry)


class ClipsCache(ThreadSafeCache):
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
        self.safe_set(clip_id, enhanced_data)

    def get_clip(self, clip_id: str) -> dict[str, Any] | None:
        """Get clip and update access statistics.

        Args:
            clip_id: Unique clip identifier

        Returns:
            Clip data if found, None otherwise
        """
        with self.lock():
            clip_entry = self.safe_get(clip_id)
            if clip_entry:
                # Update access statistics
                access_count = clip_entry.get("access_count", 0)
                if isinstance(access_count, int):
                    clip_entry["access_count"] = access_count + 1
                clip_entry["last_accessed"] = time.time()

                # Update the cache with new stats
                self.safe_set(clip_id, clip_entry)

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
        with self.lock():
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            old_clips = []

            for clip_id, clip_entry in self.safe_items():
                if isinstance(clip_entry, dict):
                    cached_at = clip_entry.get("cached_at", 0)
                    if (
                        isinstance(cached_at, int | float)
                        and (current_time - cached_at) > max_age_seconds
                    ):
                        old_clips.append(clip_id)

            for clip_id in old_clips:
                self.safe_delete(clip_id)

            if old_clips:
                logger.info(f"Cleaned up {len(old_clips)} old clips from cache")
            return len(old_clips)


# Global cache instances (initialized by app.py)
thumbnail_cache: ThumbnailCache | None = None
clips_cache: ClipsCache | None = None
settings_cache: ThreadSafeCache | None = None


def initialize_caches(config: dict[str, Any]) -> None:
    """Initialize global cache instances with configuration.

    Args:
        config: Configuration dictionary with cache settings
    """
    global thumbnail_cache, clips_cache, settings_cache

    thumbnail_cache = ThumbnailCache(maxsize=config.get("thumbnail_cache_size", 100))
    clips_cache = ClipsCache(maxsize=config.get("clips_cache_size", 50))
    settings_cache = ThreadSafeCache(maxsize=config.get("settings_cache_size", 10))

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
