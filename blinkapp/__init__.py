#!/usr/bin/env python3
"""
Blink Camera Flask Web Interface

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

__all__ = [
    "app",
    "CLIPS_CACHE_SIZE",
    "THUMBNAIL_CACHE_DIR",
    "CLIPS_CACHE_DIR",
    "logger",
]

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Authentication and session management
# Caching system for camera thumbnails, clips, and metadata

# ID validation and type safety
# Type definitions for better code clarity
# Blink camera library - third-party integration

# Application configuration
from blinkapp.config import Config

# API response models
from blinkapp.models.responses import create_api_response

# Admin routes
from blinkapp.routes.admin import register_admin_routes
from blinkapp.routes.auth import (
    register_auth_routes,
    setup_auth_routes,
)

# Camera operations and route handlers
from blinkapp.routes.camera import (
    setup_camera_routes,
)

# Clip management routes
from blinkapp.routes.clips import setup_clips_routes

# Configuration routes
from blinkapp.routes.config import setup_config_routes

# Settings management routes
from blinkapp.routes.settings import setup_settings_routes

# Streaming routes
from blinkapp.routes.streaming import setup_streaming_routes

# System management routes
from blinkapp.routes.system import setup_system_routes

# Thumbnail routes
from blinkapp.routes.thumbnails import setup_camera_thumbnail_routes
from blinkapp.services.blink_validators import require_sync_module

# Cache management
from blinkapp.services.cache_service import (
    clear_all_caches,
    initialize_cache_paths,
    load_clips_cache,
)
from blinkapp.services.debug_service import (
    dump_cloud_videos,
)

# Application lifecycle
from blinkapp.services.lifecycle_service import (
    cleanup_resources,
    startup,
)

# Route setup functions
# Route decorators and error handling
# Utilities
from blinkapp.utils.error_handlers import handle_api_error

# Utilities
from blinkapp.utils.logging_config import setup_logging

# Live streaming management


if TYPE_CHECKING:
    pass

# Third-party imports

# Flask framework components
# Type alias for Flask responses
from flask import (
    Flask,
)

# Explicitly define what this module exports
__all__ = [
    # Flask application instance
    "app",
    # Core initialization functions
    # Utility functions (now imported from utils modules)
    "handle_api_error",
    "require_sync_module",
    "setup_logging",
    "initialize_cache_paths",
    # Cache management
    "clear_all_caches",
    "load_clips_cache",
    # Configuration and debugging
    "dump_cloud_videos",
    # Application lifecycle
    "startup",
    "cleanup_resources",
    "main",
    # API utilities
    "create_api_response",
    # Configuration files and paths (commonly patched in tests)
    "Path",
    "SETTINGS_FILE",
    "CREDENTIALS_FILE",
    "CACHE_DIR",
    "CLIPS_CACHE_DIR",
    "THUMBNAIL_CACHE_DIR",
    "HLS_OUTPUT_DIR",
    # Logger (commonly patched in tests)
    "logger",
]

# ============================================================================
# Flask Application Setup
# ============================================================================

# Create Flask app instance with secure configuration
app = Flask(__name__, template_folder="../templates")
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-change-in-production")

# Set up authentication routes
setup_auth_routes(app)

# Set up camera routes
setup_camera_routes(app)

# Set up camera thumbnail routes
setup_camera_thumbnail_routes(app)

# Set up streaming routes
setup_streaming_routes(app)

# Set up configuration routes
setup_config_routes(app)

# Set up clip routes
setup_clips_routes(app)

# Set up system routes
setup_system_routes(app)

# Set up settings routes
setup_settings_routes(app)

# Set up admin routes
register_admin_routes(app)

# Register additional auth routes (index)
register_auth_routes(app)

# ============================================================================
# Global Application State
# ============================================================================

# File system paths for application data storage
# Cache configuration - initialized in initialize_cache_paths()
CACHE_DIR: str = ""  # Base cache directory
CREDENTIALS_FILE: str = ""  # Encrypted credentials storage
THUMBNAIL_CACHE_DIR: str = ""  # Camera thumbnail cache
CLIPS_CACHE_DIR: str = ""  # Downloaded clips storage
HLS_OUTPUT_DIR: str = ""  # HLS streaming output directory
SETTINGS_FILE: str = ""  # User settings persistence

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
