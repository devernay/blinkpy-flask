"""Connexion-compatible admin handlers."""

from ..models.types import JsonDict


def clear_all_caches() -> JsonDict:
    """Clear all caches.

    Returns:
        Cache clear result
    """
    from ..services.cache_service import clear_all_caches

    result = clear_all_caches()
    # Extract the message as string to ensure JsonDict compatibility
    message = str(result.get("message", "All caches cleared"))
    return {"success": True, "message": message}


def clear_thumbnail_cache() -> JsonDict:
    """Clear thumbnail cache.

    Returns:
        Cache clear result
    """
    from ..services.cache_service import clear_camera_thumbnail_cache_files

    clear_camera_thumbnail_cache_files()
    return {"success": True, "message": "Camera thumbnail cache cleared"}


def clear_clips_cache() -> JsonDict:
    """Clear clips cache.

    Returns:
        Cache clear result
    """
    from ..services.cache_service import clear_clips_cache_files

    clear_clips_cache_files()
    return {"success": True, "message": "Clips cache cleared"}
