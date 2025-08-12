"""Cache service for Blink Camera Flask application.

This module handles all cache-related business logic including
cache initialization, management, and cleanup operations.
"""

from __future__ import annotations

__all__ = [
    "ensure_clips_cache_initialized",
    "ensure_thumbnail_cache_initialized",
    "clear_all_caches",
]

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def ensure_clips_cache_initialized():
    """Ensure clips cache is initialized.

    Returns:
        Initialized clips cache instance

    Raises:
        RuntimeError: If clips_cache hasn't been initialized
    """
    from blinkapp import clips_cache

    if clips_cache is None:
        raise RuntimeError(
            "Clips cache not initialized. Call initialize_caches() first."
        )
    return clips_cache


def ensure_thumbnail_cache_initialized():
    """Ensure thumbnail cache is initialized.

    Returns:
        Initialized thumbnail cache instance
    """
    from blinkapp import (
        ensure_thumbnail_cache_initialized as _ensure_thumbnail_cache_initialized,
    )

    return _ensure_thumbnail_cache_initialized()


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
