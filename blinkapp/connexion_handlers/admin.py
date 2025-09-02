"""Connexion-compatible admin handlers."""

from ..models.types import JsonDict


def clear_all_caches() -> JsonDict:
    """Clear all caches.

    Returns:
        Cache clear result
    """
    from ..services.cache_service import clear_all_caches as service_clear_all

    return service_clear_all()


def clear_thumbnail_cache() -> JsonDict:
    """Clear thumbnail cache.

    Returns:
        Cache clear result
    """
    from ..services.cache_service import (
        clear_thumbnail_cache as service_clear_thumbnails,
    )

    return service_clear_thumbnails()


def clear_clips_cache() -> JsonDict:
    """Clear clips cache.

    Returns:
        Cache clear result
    """
    from ..services.cache_service import clear_clips_cache as service_clear_clips

    return service_clear_clips()
