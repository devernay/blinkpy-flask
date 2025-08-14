"""Authentication service for Blink Camera Flask application.

This module handles all authentication-related business logic including
Blink system initialization, 2FA verification, and credential management.
"""

from __future__ import annotations

__all__ = [
    "is_authenticated",
    "initialize_blink",
    "verify_2fa_and_save",
    "load_saved_blink",
]

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

from blinkapp.utils.decorators import error_context
from blinkapp.utils.errors import AuthenticationError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def is_authenticated() -> bool:
    """Check if user is currently authenticated with Blink.

    Returns:
        True if authenticated and startup complete, False otherwise
    """
    # Import here to avoid circular imports
    from blinkapp.services.blink_service import blink

    return blink is not None and blink.auth.token is not None


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
    # Import here to avoid circular imports during module initialization
    from blinkapp.services.connection_service import blink_connection

    with error_context("initialize Blink system", AuthenticationError):
        from aiohttp import ClientSession
        from blinkpy.auth import Auth
        from blinkpy.blinkpy import Blink

        # Create new HTTP session for Blink API communication
        session_obj = ClientSession()
        blink = Blink(session=session_obj)
        blink_connection.blink = blink  # Set reference in connection manager

        # Create authentication object with credentials
        auth = Auth(
            {"username": username, "password": password},
            no_prompt=True,  # Disable interactive prompts for web interface
            session=session_obj,
        )
        blink.auth = auth

        # Attempt to start Blink system and authenticate
        await blink.start()

        # Check if 2FA is required before proceeding
        if blink.key_required:
            logger.info("2FA key required - check your email or SMS")
            return "2fa_required"

        logger.info("Blink system initialized successfully")

        # Update global blink reference for use in route handlers

        from blinkapp.services import blink_service

        blink_service.blink = blink

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
    from blinkapp import CREDENTIALS_FILE
    from blinkapp.services.blink_service import blink

    with error_context("verify 2FA and save credentials", AuthenticationError):
        logger.debug(f"Starting 2FA verification with key: {tfa_key[:2]}***")

        # Send 2FA key using the same session/thread that created the Blink instance
        # This is critical to maintain authentication state
        logger.debug("Sending 2FA key...")
        assert blink is not None, (
            "Blink instance must be initialized before 2FA verification"
        )
        await blink.auth.send_auth_key(blink, tfa_key)

        # Complete the post-verification setup process
        logger.debug("Setting up post verification...")
        await blink.setup_post_verify()

        # Save encrypted credentials to disk for future sessions
        logger.debug("Saving credentials...")
        assert CREDENTIALS_FILE is not None, "Credentials file path must be set"
        await blink.save(CREDENTIALS_FILE)

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
    from blinkapp import CREDENTIALS_FILE
    from blinkapp.services.blink_service import blink

    assert CREDENTIALS_FILE is not None, "Credentials file path must be set"
    cred_file = Path(cast(str, CREDENTIALS_FILE))

    # Check if credentials file exists before attempting to load
    if cred_file.exists():
        try:
            from aiohttp import ClientSession
            from blinkpy.auth import Auth
            from blinkpy.blinkpy import (
                Blink,
            )
            from blinkpy.helpers.util import json_load

            assert CREDENTIALS_FILE is not None
            # Load encrypted credentials from file
            # The json_load function handles decryption automatically
            # Type ignore for mypy issue with blinkpy's json_load function
            auth_data: dict[str, Any] | None = cast(
                dict[str, Any] | None, await json_load(cast(str, CREDENTIALS_FILE))
            )

            # Create new HTTP session and attempt authentication with saved data
            session_obj = ClientSession()
            try:
                auth = Auth(auth_data, session=session_obj)
                blink = Blink(session=session_obj)
                blink.auth = auth

                # Attempt to start Blink system with saved credentials
                success = await blink.start()
                if success is True:
                    logger.info("Blink system loaded from saved credentials")
                    # blink is already updated in the blink_service module
                    return True
                else:
                    logger.warning("Failed to load Blink system from saved credentials")
                    await session_obj.close()  # Clean up failed session
                    return False
            except Exception as inner_e:
                # Ensure session is closed even if an exception occurs
                await session_obj.close()
                raise inner_e
        except Exception as e:
            logger.warning(f"Could not load Blink system from saved credentials: {e}")
            return False

    # No credentials file found
    return False
