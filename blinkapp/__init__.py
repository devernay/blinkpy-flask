#!/usr/bin/env python3
"""Blink Camera Flask Web Interface.

A comprehensive web application for managing Blink camera systems with features
including:
- Multi-system support with real-time camera thumbnails
- Live streaming via TCP to HLS transcoding using Blink's init_livestream()
- Cloud and local clip management with thumbnail generation
- User settings (temperature units, clip retention, thumbnail sizes)
- Mobile-optimized responsive interface
- Background processing for clip downloads and thumbnail generation

Main components:
- Flask web server with RESTful API
- Async Blink connection management
- HLS stream manager for live video from TCP streams
- Intelligent caching with configurable retention
- Thread-safe operations with proper cleanup

Author: Fredderic Devernay
License: MIT
"""

import logging
import os
from pathlib import Path

# Live streaming management
# Third-party imports
# Flask framework components
# Type alias for Flask responses
from flask import (
    Flask,
    Response,
)

# Authentication and session management
# Caching system for camera thumbnails, clips, and metadata
# ID validation and type safety
# Type definitions for better code clarity
# Application configuration
from blinkapp.config import Config

# Route setup functions
from blinkapp.routes.admin import setup_admin_routes
from blinkapp.routes.auth import setup_auth_routes
from blinkapp.routes.camera import setup_camera_routes
from blinkapp.routes.clips import setup_clips_routes
from blinkapp.routes.logs import setup_logs_routes
from blinkapp.routes.settings import setup_settings_routes
from blinkapp.routes.streaming import setup_streaming_routes
from blinkapp.routes.system import setup_system_routes
from blinkapp.routes.thumbnails import setup_camera_thumbnail_routes

# Import functions that tests expect to be available at module level
from blinkapp.services.cache_service import clear_all_caches
from blinkapp.utils.logging_config import setup_logging

# Explicitly define what this module exports
__all__ = [
    "Path",
    "app",
    "clear_all_caches",
    "logger",
    "setup_logging",
]

# ============================================================================
# Flask Application Setup
# ============================================================================

# Create Flask app instance with secure configuration
app = Flask(__name__, template_folder="../templates", static_folder="../static")
_secret_key = os.environ.get("SECRET_KEY")
if not _secret_key:
    # No hardcoded fallback: a shared, well-known key would let anyone forge
    # signed session cookies. Generate an ephemeral random key instead. This
    # invalidates existing sessions on restart; set SECRET_KEY in the
    # environment to keep sessions stable across restarts.
    import secrets

    _secret_key = secrets.token_hex(32)
    logging.getLogger(__name__).warning(
        "SECRET_KEY not set; using a random ephemeral key."
        + " Set SECRET_KEY in the environment for stable sessions."
    )
app.secret_key = _secret_key


# Favicon route
@app.route("/favicon.ico")
def favicon() -> "Response":
    """Serve favicon from static directory.

    Returns:
        Response: Flask response serving the favicon.ico file.
    """
    from flask import send_from_directory

    static_folder = app.static_folder
    if static_folder is None:
        raise RuntimeError("Static folder not configured")
    return send_from_directory(static_folder, "favicon.ico")


# Set up authentication routes
setup_auth_routes(app)

# Set up camera routes
setup_camera_routes(app)

# Set up camera thumbnail routes
setup_camera_thumbnail_routes(app)

# Set up streaming routes
setup_streaming_routes(app)

# Set up clip routes
setup_clips_routes(app)

# Set up system routes
setup_system_routes(app)

# Set up settings routes
setup_settings_routes(app)

# Set up logs routes
setup_logs_routes(app)

# Set up admin routes
setup_admin_routes(app)

# ============================================================================
# Global Application State
# ============================================================================

# File system paths for application data storage
# Cache configuration - initialized in initialize_cache_paths()
# Resolved Path objects (set once during initialization to avoid chdir issues)
_CACHE_DIR_PATH: Path | None = None
_CLIPS_CACHE_DIR_PATH: Path | None = None
_THUMBNAIL_CACHE_DIR_PATH: Path | None = None
_HLS_OUTPUT_DIR_PATH: Path | None = None
_CREDENTIALS_FILE_PATH: Path | None = None
_SETTINGS_FILE_PATH: Path | None = None

# ============================================================================
# Error Handling and API Response Utilities
# ============================================================================


# Configure logging - will be reconfigured after cache paths are set
logger = logging.getLogger(__name__)


# ============================================================================
# Cache and File System Management
# ============================================================================
# Cache and File System Management
# ============================================================================

# Cache configuration constants
CLIPS_CACHE_SIZE = Config.CLIPS_CACHE_SIZE  # Maximum number of clips to cache

# ============================================================================
# Global Variable Validation and Type Guards
# ============================================================================


# Camera thumbnail update functionality


# ============================================================================
# API Routes - System Management
# ============================================================================


# ============================================================================
# API Routes - Clip Management
# ============================================================================


# ============================================================================
# API Routes - Configuration and Settings
# ============================================================================


# Removed generate_thumbnail_async - thumbnails only generated on clip download


# Stream management functionality


# LRUCache automatically handles eviction, no manual cleanup needed

# Import main function for module execution
if __name__ == "__main__":
    from blinkapp.__main__ import main

    main()
