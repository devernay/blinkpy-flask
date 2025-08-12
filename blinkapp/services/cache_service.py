"""Cache service for Blink Camera Flask application.

This module handles all cache-related business logic including
cache initialization, management, and cleanup operations.
"""

from __future__ import annotations

__all__ = [
    "initialize_caches",
    "ensure_clips_cache_initialized",
    "ensure_thumbnail_cache_initialized",
    "clear_all_caches",
]

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from blinkapp.models.cache import ClipsCache, ThumbnailCache

logger = logging.getLogger(__name__)

# Global cache instances
clips_cache: ClipsCache | None = None
thumbnail_cache: ThumbnailCache | None = None


def initialize_caches(config: dict[str, Any]) -> None:
    """Initialize the global cache instances."""
    global clips_cache, thumbnail_cache
    from blinkapp.models.cache import initialize_caches as _initialize_caches

    clips_cache, thumbnail_cache = _initialize_caches(config)


def ensure_clips_cache_initialized():
    """Ensure clips cache is initialized.

    Returns:
        Initialized clips cache instance

    Raises:
        RuntimeError: If clips_cache hasn't been initialized
    """
    if clips_cache is None:
        raise RuntimeError(
            "Clips cache not initialized. Call initialize_caches() first."
        )
    return clips_cache


def ensure_thumbnail_cache_initialized():
    """Ensure thumbnail cache is initialized.

    Returns:
        Initialized thumbnail cache instance

    Raises:
        RuntimeError: If thumbnail_cache hasn't been initialized
    """
    if thumbnail_cache is None:
        raise RuntimeError(
            "Thumbnail cache not initialized. Call initialize_caches() first."
        )
    return thumbnail_cache


def clear_all_caches() -> dict[str, Any]:
    """Clear all application caches.

    Returns:
        Dictionary with operation result
    """
    try:
        # Clear clips cache
        clips_cache = ensure_clips_cache_initialized()
        clips_cache.clear()

        # Clear thumbnail cache
        thumbnail_cache = ensure_thumbnail_cache_initialized()
        thumbnail_cache.clear()

        logger.info("All caches cleared successfully")
        return {"success": True, "message": "All caches cleared"}
    except Exception as e:
        logger.error(f"Failed to clear caches: {e}")
        return {"success": False, "error": str(e)}
