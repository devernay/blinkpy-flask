"""Authentication service for Blink Camera Flask application.

This module handles all authentication-related business logic including
Blink system initialization, 2FA verification, and credential management.
"""

from __future__ import annotations

__all__ = [
    "handle_2fa_verification",
    "handle_login",
    "initialize_blink",
    "is_blink_authenticated",
    "is_valid_email_format",
    "load_saved_blink",
    "logger",
    "validate_credentials",
    "verify_2fa_and_save",
]

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from aiohttp import ClientSession

from blinkapp.models.types import SimpleJsonDict
from blinkapp.services.blink_service import get_blink_instance
from blinkapp.utils.decorators import error_context
from blinkapp.utils.errors import AuthenticationError

if TYPE_CHECKING:
    from blinkpy import Blink

if TYPE_CHECKING:
    from blinkpy.auth import Auth

logger = logging.getLogger(__name__)


def is_blink_authenticated(blink_instance: Blink | None = None) -> bool:
    """Check if user is currently authenticated with Blink API.

    Args:
        blink_instance: Optional blink instance for testing

    Returns:
        True if authenticated with Blink API and startup complete, False otherwise
    """
    if blink_instance is None:
        try:
            from blinkapp.services.blink_service import ensure_blink_initialized

            blink_instance = ensure_blink_initialized()
        except RuntimeError:
            return False

    return blink_instance is not None and blink_instance.auth.token is not None


def is_valid_email_format(email: str) -> bool:
    """Validate email format - pure function.

    Args:
        email: Email address to validate.

    Returns:
        True if email format is valid.
    """
    if not email or not isinstance(email, str):
        return False

    # Basic email validation
    if "@" not in email:
        return False

    parts = email.split("@")
    if len(parts) != 2:
        return False

    local, domain = parts
    if not local or not domain:
        return False

    # Check for basic domain format
    if "." not in domain:
        return False

    return True


def validate_credentials(username: str, password: str) -> bool:
    """Validate credentials format - pure function.

    Args:
        username: Username to validate.
        password: Password to validate.

    Returns:
        True if credentials format is valid.
    """
    from ..config import Config

    if not username or not password:
        return False

    if not isinstance(username, str) or not isinstance(password, str):
        return False

    # Validate email format for username
    if not is_valid_email_format(username):
        return False

    # Check for XSS patterns
    xss_patterns = ["<script", "</script", "javascript:", "onload=", "onerror="]
    if any(
        pattern in username.lower() or pattern in password.lower()
        for pattern in xss_patterns
    ):
        return False

    # Check password length
    if len(password) > Config.MAX_PASSWORD_LENGTH:
        return False

    # Basic validation - non-empty strings
    return len(username.strip()) > 0 and len(password.strip()) > 0


def _create_blink_session(
    session_factory: type[ClientSession] | None = None,
) -> ClientSession:
    """Create Blink session with injectable factory."""
    if session_factory is None:
        from aiohttp import ClientSession

        session_factory = ClientSession

    return session_factory()


def _create_auth_object(
    username: str,
    password: str,
    session_obj: ClientSession,
    auth_factory: type[Auth] | None = None,
) -> Auth:
    """Create auth object with injectable factory."""
    if auth_factory is None:
        from blinkpy.auth import Auth

        auth_factory = Auth

    return auth_factory(
        {"username": username, "password": password},
        no_prompt=True,
        session=session_obj,
    )


async def initialize_blink(
    username: str, password: str
) -> bool | Literal["2fa_required"]:
    """Initialize Blink system following blinkpy README.

    Creates a new Blink session with the provided credentials and attempts
    to authenticate with the Blink API. This function handles the initial
    authentication flow and determines if 2FA is required.

    The function creates a new aiohttp ClientSession and Blink instance,
    then attempts to start the authentication process. If successful,
    it updates the global blink reference for use throughout the application.

    Args:
        username: Blink account username/email address
        password: Blink account password

    Returns:
        True if authentication successful and no 2FA required
        '2fa_required' if 2FA verification is needed
        False if authentication failed

    Raises:
        AuthenticationError: If authentication fails due to invalid credentials
        or network issues

    Example:
        >>> result = await initialize_blink("user@example.com", "password123")
        >>> if result == "2fa_required":
        ...     # Prompt user for 2FA code
        ...     pass
    """
    with error_context("initialize Blink system", AuthenticationError):
        # Create new HTTP session for Blink API communication
        session_obj = _create_blink_session()

        # Import blink_service to work directly with global instance
        from blinkapp.services import blink_service

        blink_service.initialize_blink_instance(session_obj)  # type: ignore[arg-type]

        # Create authentication object with credentials
        auth = _create_auth_object(username, password, session_obj)
        blink_service.ensure_blink_initialized().auth = auth

        # Attempt to start Blink system and authenticate
        blink_instance = get_blink_instance()
        assert blink_instance is not None, "Blink instance must be initialized"

        # blinkpy >=0.25 raises BlinkTwoFARequiredError from start() when 2FA
        # is required (this replaces the removed blink.key_required attribute).
        from blinkpy.auth import BlinkTwoFARequiredError

        try:
            await blink_instance.start()
        except BlinkTwoFARequiredError:
            logger.info("2FA key required - check your email or SMS")
            return "2fa_required"

        logger.info("Blink system initialized successfully")

        return True


async def verify_2fa_and_save(username: str, password: str, tfa_key: str) -> bool:
    """Verify 2FA code and save credentials in same thread as Blink creation.

    Completes the two-factor authentication process by sending the verification
    code to the Blink API and saving the authenticated session to disk for
    future use. This function must be called after initialize_blink() returns
    "2fa_required".

    The function uses the existing Blink session created during initialization
    to maintain session continuity and avoid authentication state issues.

    Args:
        username: Blink account username (unused but kept for API consistency)
        password: Blink account password (unused but kept for API consistency)
        tfa_key: 2FA verification code from email/SMS (typically 6 digits)

    Returns:
        True if 2FA verification successful and credentials saved
        False if verification failed

    Raises:
        AuthenticationError: If 2FA verification fails or credential saving fails

    Example:
        >>> success = await verify_2fa_and_save("user@example.com", "pass", "123456")
        >>> if success:
        ...     print("2FA verified and credentials saved")
    """
    # Import here to avoid circular imports during module initialization

    with error_context("verify 2FA and save credentials", AuthenticationError):
        logger.debug(f"Starting 2FA verification with key: {tfa_key[:2]}***")

        # Send 2FA key using the same session/thread that created the Blink instance
        # This is critical to maintain authentication state
        logger.debug("Sending 2FA key...")
        blink_instance = get_blink_instance()
        assert blink_instance is not None, (
            "Blink instance must be initialized before 2FA verification"
        )
        # blinkpy >=0.25: send_2fa_code() completes the OAuth 2FA flow and runs
        # setup_post_verify() internally (replaces the removed
        # auth.send_auth_key() + separate setup_post_verify() sequence).
        success = await blink_instance.send_2fa_code(tfa_key)
        if not success:
            logger.error("2FA verification failed")
            return False

        # Save encrypted credentials to disk for future sessions
        logger.debug("Saving credentials...")
        credentials_file = get_credentials_file_path()
        await blink_instance.save(str(credentials_file))

        logger.info("2FA verification and save completed successfully")
        return True


async def load_saved_blink() -> bool:
    """Load Blink system from saved credentials file.

    Attempts to restore a previous Blink session using encrypted
    credentials stored in the cache directory. This allows users
    to avoid re-entering credentials on application restart.

    The function creates a new HTTP session and attempts to authenticate
    using the saved credentials. If successful, it updates the global
    blink reference for use throughout the application.

    Returns:
        True if successfully loaded and authenticated, False otherwise

    Side Effects:
        - Updates global blinkapp.blink reference if successful
        - Closes HTTP session if authentication fails

    Example:
        >>> if await load_saved_blink():
        ...     print("Restored previous session")
        ... else:
        ...     print("Need to login again")
    """
    # Import here to avoid circular imports during module initialization

    credentials_file = get_credentials_file_path()
    cred_file = credentials_file

    # Check if credentials file exists before attempting to load
    if cred_file.exists():
        try:
            from blinkpy.auth import Auth
            from blinkpy.helpers.util import json_load

            credentials_file = get_credentials_file_path()
            # Load encrypted credentials from file
            # The json_load function handles decryption automatically
            auth_data: SimpleJsonDict | None = await json_load(str(credentials_file))

            if auth_data is None:
                logger.warning("No credentials found in file")
                return False

            # Type narrowing: auth_data is now guaranteed to be a dictionary
            assert isinstance(auth_data, dict), "auth_data must be a dictionary"

            # Create fresh session and Blink instance for credential loading
            # This matches the pattern from blinkpy-source example
            from aiohttp import ClientSession
            from blinkpy.blinkpy import Blink

            session_obj = ClientSession()
            try:
                # Create fresh Blink instance with new session
                blink = Blink(session=session_obj)
                blink.auth = Auth(auth_data, session=session_obj)

                # Try to start with fresh session
                success = await blink.start()

                if success is True:
                    logger.info("Blink system loaded from saved credentials")
                    camera_count = len(blink.cameras) if blink.cameras else 0
                    logger.info(f"Found {camera_count} cameras")

                    # Update saved credentials after successful authentication
                    credentials_file = get_credentials_file_path()
                    await blink.save(str(credentials_file))

                    # Update the BlinkConnection's blink instance
                    from blinkapp.services.blink_service import (
                        ensure_blink_connection_initialized,
                    )

                    blink_connection = ensure_blink_connection_initialized()

                    # Close old session if it exists
                    if (
                        blink_connection.blink is not None
                        and blink_connection.blink.auth is not None
                        and blink_connection.blink.auth.session is not None
                    ):
                        await blink_connection.blink.auth.session.close()

                    # Replace with new instance in both BlinkConnection and global variable
                    blink_connection.blink = blink

                    # Also update the global _blink variable so ensure_blink_initialized() works
                    from blinkapp.services import blink_service

                    blink_service._blink = blink

                    return True
                logger.warning(
                    "Failed to load Blink system from saved credentials - token may be expired"
                )
                await session_obj.close()
                return False
            except Exception as inner_e:
                logger.error(f"Exception in load_saved_blink: {inner_e}")
                await session_obj.close()
                raise inner_e
        except Exception as e:
            logger.warning(f"Could not load Blink system from saved credentials: {e}")
            return False

    # No credentials file found
    return False


def handle_login(username: str, password: str) -> SimpleJsonDict:
    """Handle user login attempt.

    This function performs the actual Blink authentication by calling
    initialize_blink asynchronously and handling the response.

    Args:
        username: User's email/username
        password: User's password

    Returns:
        Dict with keys: success, requires_2fa, error
    """
    try:
        # Validate credentials format
        if not validate_credentials(username, password):
            return {"success": False, "error": "Invalid username or password format"}

        # Use blink_connection to run authentication
        try:
            from blinkapp.services.blink_service import (
                ensure_blink_connection_initialized,
            )

            blink_conn = ensure_blink_connection_initialized()
        except RuntimeError:
            return {"success": False, "error": "System not ready. Please try again."}

        result = blink_conn.execute(initialize_blink(username, password))

        if result is True:
            return {"success": True}
        if result == "2fa_required":
            # Store credentials in Flask session for 2FA verification
            from flask import session

            session["pending_2fa"] = True
            session["temp_username"] = username
            session["temp_password"] = password
            return {"success": False, "requires_2fa": True}
        return {"success": False, "error": "Authentication failed"}

    except Exception as e:
        logger.error(f"Login error: {e}")
        return {"success": False, "error": "Authentication failed"}


def handle_logout() -> dict[str, bool]:
    """Handle user logout by clearing session data.

    Returns:
        Dict with success status
    """
    from flask import session

    # Clear all session data
    session.clear()

    return {"success": True}


def handle_2fa_verification(code: str) -> SimpleJsonDict:
    """Handle 2FA verification.

    Args:
        code: 2FA verification code

    Returns:
        Dict with keys: success, error
    """
    try:
        from flask import session

        username = session.get("temp_username")
        password = session.get("temp_password")

        if not username or not password:
            return {"success": False, "error": "Session expired. Please login again."}

        # Use blink_connection for 2FA verification
        try:
            from blinkapp.services.blink_service import (
                ensure_blink_connection_initialized,
            )

            blink_conn = ensure_blink_connection_initialized()
        except RuntimeError:
            return {"success": False, "error": "System not ready. Please try again."}

        result = blink_conn.execute(verify_2fa_and_save(username, password, code))

        if result:
            # Clear temporary session data
            session.pop("pending_2fa", None)
            session.pop("temp_username", None)
            session.pop("temp_password", None)
            session["authenticated"] = True
            return {"success": True}
        return {"success": False, "error": "Invalid 2FA code"}
    except Exception as e:
        logger.error(f"2FA verification error: {e}")
        return {"success": False, "error": "2FA verification failed"}


def get_credentials_file_path() -> Path:
    """Get the credentials file path.

    Returns:
        Path: Resolved path to the credentials file.
    """
    import blinkapp

    assert blinkapp._CREDENTIALS_FILE_PATH is not None, (
        "Cache paths not initialized. Call initialize_cache_paths() first."
    )
    return blinkapp._CREDENTIALS_FILE_PATH


# Testability improvement functions - these provide injectable dependencies
# for better unit testing without changing existing functionality
