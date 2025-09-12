"""Thread-safe caching module for Blink Flask application.

This module provides thread-safe cache implementations using a generic wrapper
approach. ThreadSafeCache provides thread-safety for any cache implementation
through multiple inheritance.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Any, TypedDict, TypeVar

from cachetools import Cache, LRUCache

from blinkapp.models.ids import CameraId, ClipId


class ClipCacheData(TypedDict):
    """Structure for clip data returned by the API."""

    id: str
    camera_name: str
    system_name: str
    time: str
    event_type: str
    thumbnail: str
    media_url: str


class ClipCacheEntryRequired(TypedDict):
    """Required fields for clip cache entries."""


class ClipCacheEntry(ClipCacheEntryRequired, total=False):
    """Structure for clip cache entries."""

    # All fields are optional since entries can be created with different subsets
    clip_data: ClipCacheData
    cached_at: float
    access_count: int
    last_accessed: float
    filepath: Path
    thumbnail: Path | None
    cloud_thumbnail_url: str | None  # URL for cloud thumbnail
    media_url: str
    created_at: str


class CameraThumbnailCacheEntry(TypedDict):
    """Structure for camera thumbnail cache entries.

    This represents the actual data stored for each cached camera thumbnail,
    containing the timestamp when the thumbnail was cached and the filename
    of the cached thumbnail file.
    """

    timestamp: int  # Unix timestamp when thumbnail was cached
    filename: str  # Filename of the cached thumbnail file


# Generic type variables for key and value types
K = TypeVar("K")  # Key type
V = TypeVar("V")  # Value type

logger = logging.getLogger(__name__)

# Explicitly define what this module exports
__all__ = [
    "CameraThumbnailCache",
    "CameraThumbnailCacheEntry",
    "ClipCacheData",
    "ClipCacheEntry",
    "ClipsCache",
    "ThreadSafeCache",
    "ThreadSafeLRUCache",
]


class ThreadSafeCache[K, V](Cache[K, V]):
    """Thread-safe cache wrapper.

    Provides thread-safe access to cache operations through a lock.
    Only overrides core data access methods to maintain type compatibility.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize cache with thread safety."""
        super().__init__(*args, **kwargs)
        self._lock = threading.RLock()

    def __getitem__(self, key: K) -> V:
        """Thread-safe getitem method."""
        with self._lock:
            return super().__getitem__(key)

    def __setitem__(self, key: K, value: V) -> None:
        """Thread-safe setitem method."""
        with self._lock:
            super().__setitem__(key, value)

    def __delitem__(self, key: K) -> None:
        """Thread-safe delitem method."""
        with self._lock:
            super().__delitem__(key)

    def clear(self) -> None:
        """Thread-safe clear method."""
        with self._lock:
            super().clear()

    def items_list(self) -> list[tuple[K, V]]:
        """Get items as a list for safe iteration.

        Returns:
            list[tuple[K, V]]: List of (key, value) tuples from the cache.
        """
        with self._lock:
            return list(super().items())

    def get_stats(self) -> dict[str, int | float]:
        """Get cache statistics including size, max size, and hit rate.

        Returns:
            dict[str, int | float]: Dictionary containing cache statistics.
        """
        with self._lock:
            return {
                "size": len(self),
                "maxsize": getattr(
                    self, "maxsize", 0
                ),  # Safe access - not all cache types have these attrs
                "hits": getattr(
                    self, "hits", 0
                ),  # Safe access - not all cache types have these attrs
                "misses": getattr(
                    self, "misses", 0
                ),  # Safe access - not all cache types have these attrs
                "hit_rate": (
                    getattr(self, "hits", 0)  # Safe access for hit rate calculation
                    / max(
                        getattr(self, "hits", 0) + getattr(self, "misses", 0), 1
                    )  # Safe access for hit rate calculation
                ),
            }


class ThreadSafeLRUCache[K, V](ThreadSafeCache[K, V], LRUCache[K, V]):
    """Thread-safe LRU cache implementation."""

    def __init__(self, maxsize: int = 128, **kwargs: Any) -> None:
        """Initialize with LRU eviction policy."""
        super().__init__(maxsize, **kwargs)


class CameraThumbnailCache(ThreadSafeLRUCache[CameraId, CameraThumbnailCacheEntry]):
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

    def get_thumbnail_timestamp(self, camera_id: CameraId) -> float | None:
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

    def is_thumbnail_fresh(
        self, camera_id: CameraId, max_age_seconds: int = 300
    ) -> bool:
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
        camera_id: CameraId,
        thumbnail_data: bytes,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Update thumbnail with current timestamp.

        Args:
            camera_id: Camera identifier
            thumbnail_data: Raw thumbnail image data
            metadata: Optional metadata to store with thumbnail
        """
        cache_entry = CameraThumbnailCacheEntry(
            timestamp=int(time.time()),
            filename="",  # Will be set by the actual cache logic
        )
        self[camera_id] = cache_entry


class ClipsCache(ThreadSafeLRUCache[ClipId, ClipCacheEntry]):
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

    def add_clip(self, clip_id: ClipId, clip_data: ClipCacheData) -> None:
        """Add clip with automatic metadata enhancement.

        Stores clip data with additional tracking metadata for cache management
        including access statistics and timestamps for cleanup operations.

        Args:
            clip_id: Unique clip identifier
            clip_data: Clip information and metadata from Blink API
        """
        enhanced_data: ClipCacheEntry = {
            "clip_data": clip_data,
            "cached_at": time.time(),  # When clip was added to cache
            "access_count": 0,  # Track access frequency
            "last_accessed": time.time(),  # Most recent access time
        }
        self[clip_id] = enhanced_data

    def get_clip(self, clip_id: ClipId) -> ClipCacheData | None:
        """Get clip and update access statistics.

        Args:
            clip_id: Unique clip identifier

        Returns:
            Clip data if found, None otherwise
        """
        clip_entry = self.get(clip_id)
        if clip_entry is not None:
            # Update access statistics if they exist
            if "access_count" in clip_entry:
                clip_entry["access_count"] = clip_entry["access_count"] + 1
            if "last_accessed" in clip_entry:
                clip_entry["last_accessed"] = time.time()

            # Update the cache with new stats
            self[clip_id] = clip_entry

            # Return the actual clip data if it exists
            if "clip_data" in clip_entry:
                return clip_entry["clip_data"]
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
        old_clips: list[ClipId] = []

        for clip_id, clip_entry in self.items_list():
            cached_at = clip_entry.get("cached_at", 0)
            if (current_time - cached_at) > max_age_seconds:
                old_clips.append(clip_id)

        for clip_id in old_clips:
            del self[clip_id]

        if old_clips:
            logger.info(f"Cleaned up {len(old_clips)} old clips from cache")
        return len(old_clips)
