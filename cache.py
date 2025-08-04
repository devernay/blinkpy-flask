"""Cache classes for the Blink Camera Flask application."""

import functools
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TypedDict, TypeVar

from cachetools import LRUCache, cachedmethod
from cachetools.keys import hashkey

from config import Config

# Type definitions
CacheKey = str
T = TypeVar("T")


def synchronized(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to make cache methods thread-safe using the instance's _lock.

    This follows the standard Python pattern for creating decorators that
    preserve function metadata using functools.wraps.

    Args:
        func: The function to synchronize

    Returns:
        Thread-safe wrapper function
    """

    @functools.wraps(func)
    def wrapper(self: object, *args: object, **kwargs: object) -> T:
        with self._lock:  # type: ignore[attr-defined]
            return func(self, *args, **kwargs)

    return wrapper


class ThreadSafeCache(LRUCache[str, dict[str, object]]):
    """
    Base thread-safe cache class with common functionality.

    Provides thread-safe operations for all cache implementations,
    eliminating code duplication across cache classes.
    """

    def __init__(self, maxsize: int = 100) -> None:
        """Initialize cache with specified maximum size.

        Args:
            maxsize: Maximum number of items to cache
        """
        super().__init__(maxsize=maxsize)
        self._lock = threading.RLock()

    # Thread-safe overrides for LRUCache methods using decorator
    @synchronized
    def get(self, key: CacheKey, default: object = None) -> object:
        """Thread-safe get method.

        Args:
            key: Cache key to retrieve
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        return super().get(key, default)

    @synchronized
    def __getitem__(self, key: CacheKey) -> object:
        """Thread-safe getitem method.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached value

        Raises:
            KeyError: If key not found
        """
        return super().__getitem__(key)

    @synchronized
    def __setitem__(self, key: CacheKey, value: object) -> None:
        """Thread-safe setitem method."""
        super().__setitem__(key, value)

    @synchronized
    def __delitem__(self, key: CacheKey) -> None:
        """Thread-safe delitem method."""
        super().__delitem__(key)

    @synchronized
    def __contains__(self, key: CacheKey) -> bool:
        """Thread-safe contains method."""
        return super().__contains__(key)

    @synchronized
    def __len__(self) -> int:
        """Thread-safe len method."""
        return super().__len__()

    @synchronized
    def pop(self, key: CacheKey, default: object = None) -> object:
        """Thread-safe pop method."""
        return super().pop(key, default)

    @synchronized
    def popitem(self) -> tuple[CacheKey, object]:
        """Thread-safe popitem method."""
        return super().popitem()

    @synchronized
    def clear(self) -> None:
        """Thread-safe clear method."""
        super().clear()

    @synchronized
    def setdefault(self, key: CacheKey, default: object = None) -> object:
        """Thread-safe setdefault method."""
        return super().setdefault(key, default)

    @synchronized
    def update(self, *args: object, **kwargs: object) -> None:
        """Thread-safe update method."""
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
        """Get cache statistics."""
        return {"size": len(self), "maxsize": self.maxsize}


class ThumbnailCache(ThreadSafeCache):
    """
    Thumbnail cache with specialized methods for camera thumbnails.

    Inherits all thread-safe cache operations from ThreadSafeCache,
    adding only thumbnail-specific functionality.
    """

    # No need to redefine __init__ or any basic cache methods - inherited from ThreadSafeCache!

    # Custom methods using @cachedmethod decorator
    @cachedmethod(lambda self: self, lock=lambda self: self._lock)
    def get_thumbnail_data(self, camera_id: str, timestamp: int) -> dict[str, object]:
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
        """Update thumbnail if timestamp is newer.

        For conditional caching logic where decorators aren't suitable.

        Args:
            camera_id: ID of the camera
            timestamp: Timestamp of the new thumbnail
            filename: Filename of the thumbnail

        Returns:
            True if thumbnail was updated, False otherwise
        """
        # Check for existing entries for this camera
        cache_key = f"{camera_id}_current"
        current_entry = self.get(cache_key)
        current_ts = (
            current_entry.get("timestamp", 0) if isinstance(current_entry, dict) else 0
        )

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

    Inherits thread-safe operations from ThreadSafeCache and adds
    download-specific functionality.
    """

    @cachedmethod(lambda self: self, lock=lambda self: self._lock)
    def get_clip_download_info(self, clip_id: str) -> dict[str, object]:
        """Get clip download info - automatically cached and thread-safe.

        Uses @cachedmethod decorator as recommended by cachetools.

        Args:
            clip_id: ID of the clip to get download info for

        Returns:
            Dictionary containing clip download information
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
        """Manually cache clip info (for cases where decorator isn't suitable).

        Args:
            clip_id: ID of the clip
            filepath: Path to the clip file
            thumbnail_path: Optional path to the thumbnail file
        """
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

# Hybrid approach: Keep both implementations for compatibility
# Object-oriented cache instances (new approach)
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
