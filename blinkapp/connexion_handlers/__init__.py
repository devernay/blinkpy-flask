"""Connexion-compatible API handlers.

These functions are designed to work with Connexion's automatic parameter
validation and routing. They use basic Python types that match the OpenAPI
specification and handle their own type conversion internally.
"""

# Auth handlers
# Admin handlers
from .admin import (
    clear_all_caches,
    clear_clips_cache,
    clear_thumbnail_cache,
)
from .auth import (
    authenticate_user,
    login_page,
    logout_user,
    main_page,
    twofa_page,
    verify_twofa,
)

# Camera handlers
from .camera import (
    get_camera_details,
    list_cameras,
    start_camera_recording,
)

# Clips handlers
from .clips import (
    delete_clip,
    download_clip,
    generate_clip_thumbnail,
    get_clip_thumbnail,
    get_clips,
)

# Settings handlers
from .settings import (
    get_app_config,
    get_user_settings,
    update_user_settings,
)

# Streaming handlers
from .streaming import (
    get_hls_stream_segments,
    start_live_stream,
    stop_live_stream,
)

# System handlers
from .system import (
    clear_systems_cache,
    get_system_details,
    get_system_devices,
    get_systems,
    update_system_settings,
)

# Thumbnail handlers
from .thumbnails import (
    get_camera_thumbnail,
    refresh_camera_thumbnail,
)

__all__ = [
    # Auth
    "authenticate_user",
    "login_page",
    "logout_user",
    "main_page",
    "twofa_page",
    "verify_twofa",
    # System
    "clear_systems_cache",
    "get_system_details",
    "get_system_devices",
    "get_systems",
    "update_system_settings",
    # Camera
    "get_camera_details",
    "list_cameras",
    "start_camera_recording",
    # Streaming
    "get_hls_stream_segments",
    "start_live_stream",
    "stop_live_stream",
    # Thumbnails
    "get_camera_thumbnail",
    "refresh_camera_thumbnail",
    # Clips
    "delete_clip",
    "download_clip",
    "generate_clip_thumbnail",
    "get_clip_thumbnail",
    "get_clips",
    # Settings
    "get_app_config",
    "get_user_settings",
    "update_user_settings",
    # Admin
    "clear_all_caches",
    "clear_clips_cache",
    "clear_thumbnail_cache",
]
