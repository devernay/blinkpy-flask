"""Thumbnail service for Blink Camera Flask application.

This module handles all thumbnail-related business logic including
thumbnail generation, caching, and processing operations.
"""

from __future__ import annotations

__all__ = [
    "generate_clip_thumbnail",
    "notify_thumbnail_ready",
    "get_thumbnail_cache_stats",
]

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from blinkapp.models.ids import ClipId

logger = logging.getLogger(__name__)


def generate_clip_thumbnail(clip_id: ClipId, clip_path: str) -> bool:
    """Generate thumbnail for a clip.

    Args:
        clip_id: The clip ID
        clip_path: Path to the clip file

    Returns:
        True if thumbnail generated successfully, False otherwise
    """
    from blinkapp import generate_clip_thumbnail as _generate_clip_thumbnail

    return _generate_clip_thumbnail(clip_id, clip_path)


def notify_thumbnail_ready(clip_id: ClipId) -> None:
    """Notify that thumbnail is ready for a clip.

    Args:
        clip_id: The clip ID
    """
    from blinkapp import notify_thumbnail_ready as _notify_thumbnail_ready

    _notify_thumbnail_ready(clip_id)


def get_thumbnail_cache_stats() -> dict[str, Any]:
    """Get thumbnail cache statistics.

    Returns:
        Dictionary with cache statistics
    """
    from blinkapp.services.cache_service import ensure_thumbnail_cache_initialized

    try:
        thumbnail_cache = ensure_thumbnail_cache_initialized()
        return {
            "size": len(thumbnail_cache),
            "max_size": getattr(thumbnail_cache, "max_size", "unknown"),
            "hit_rate": getattr(thumbnail_cache, "hit_rate", "unknown"),
        }
    except Exception as e:
        logger.error(f"Failed to get thumbnail cache stats: {e}")
        return {"error": str(e)}
