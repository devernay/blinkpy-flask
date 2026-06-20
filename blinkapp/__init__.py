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
from datetime import timedelta
from pathlib import Path

# Live streaming management
# Third-party imports
# Flask framework components
# Type alias for Flask responses
from flask import (
    Flask,
    Response,
)
from werkzeug.wrappers import Response as WerkzeugResponse

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


def _secret_key_file_path() -> Path:
    """Fallback location for a persisted SECRET_KEY when no keychain exists."""
    return Path(Config.DEFAULT_CACHE_DIR) / ".secret_key"


def _load_or_create_persistent_secret_key() -> str:
    """Return a SECRET_KEY that is stable across restarts.

    Tries the OS keychain first (macOS Keychain / Windows Credential Locker /
    Linux Secret Service via the ``keyring`` package), falling back to a
    0600 key file in the data directory for headless environments, and finally
    to an ephemeral key if neither can be persisted.
    """
    import secrets

    log = logging.getLogger(__name__)

    # 1) OS keychain (preferred): survives restarts, no plaintext on disk.
    try:
        import keyring

        existing = keyring.get_password("blinkapp", "flask-secret-key")
        if existing:
            return existing
        new_key = secrets.token_hex(32)
        keyring.set_password("blinkapp", "flask-secret-key", new_key)
        log.info(
            "Stored a new Flask SECRET_KEY in the OS keychain; "
            "sessions now persist across restarts."
        )
        return new_key
    except Exception as e:
        log.warning("Keychain unavailable for SECRET_KEY (%s); trying a key file.", e)

    # 2) Key file fallback (headless): persists across restarts.
    try:
        key_path = _secret_key_file_path()
        if key_path.exists():
            stored = key_path.read_text().strip()
            if stored:
                return stored
        new_key = secrets.token_hex(32)
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_text(new_key)
        try:
            os.chmod(key_path, 0o600)
        except OSError:
            pass
        log.info("Stored a new Flask SECRET_KEY in %s.", key_path)
        return new_key
    except Exception as e:
        log.warning(
            "Could not persist SECRET_KEY (%s); using an ephemeral key "
            "(sessions reset on restart).",
            e,
        )

    # 3) Ephemeral last resort.
    return secrets.token_hex(32)


def _resolve_secret_key() -> str:
    """Resolve the Flask SECRET_KEY: env override, else a persistent key."""
    import secrets
    import sys

    env_key = os.environ.get("SECRET_KEY")
    if env_key:
        return env_key
    # Never touch the OS keychain / key file during the test suite.
    if "pytest" in sys.modules:
        return secrets.token_hex(32)
    return _load_or_create_persistent_secret_key()


app.secret_key = _resolve_secret_key()

# Persistent login cookie: sessions marked permanent last this long (a sliding
# window, refreshed on each request) and survive browser restarts.
app.permanent_session_lifetime = timedelta(days=Config.SESSION_LIFETIME_DAYS)


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


# Endpoints reachable without authentication (login/2FA pages, favicon, static).
_PUBLIC_ENDPOINTS = frozenset(
    {"login_page_route", "twofa_page_route", "favicon", "static"}
)


@app.before_request
def _require_authentication() -> "WerkzeugResponse | tuple[Response, int] | None":
    """Require an authenticated session for protected endpoints.

    The web UI signs in via the login/2FA pages, which set
    ``session['authenticated']``. Everything else is protected:
    unauthenticated requests to ``/api/*`` receive a 401 JSON response, while
    other unauthenticated requests are redirected to the login page. This
    prevents the API and pages from being reachable without logging in, even
    when the server is bound to all interfaces.

    Returns:
        None to allow the request, or a 401/redirect response to block it.
    """
    from flask import jsonify, redirect, request, session, url_for

    # Allow disabling the guard (the existing test suite exercises API
    # endpoints directly, as an already-logged-in user would).
    if not app.config.get("REQUIRE_AUTH", True):
        return None

    # Let unmatched routes fall through to Flask's normal 404 handling.
    if request.endpoint is None:
        return None

    # Always-public endpoints and static assets.
    if request.endpoint in _PUBLIC_ENDPOINTS or request.path.startswith("/static/"):
        return None

    if session.get("authenticated"):
        return None

    # Not authenticated: JSON 401 for API, redirect to login for pages.
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "Authentication required"}), 401
    return redirect(url_for("login_page_route"))


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
_RECORDINGS_DIR_PATH: Path | None = None

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
