"""
Authentication functions for the Blink Camera Flask application.

This module handles all authentication-related functionality including:
- User login with email/password
- Two-factor authentication (2FA) support
- Session management and persistence
- Credential storage and retrieval
- Authentication state checking

The authentication flow supports both regular login and 2FA verification,
with credentials securely stored in encrypted format for session persistence.
"""

import logging
from pathlib import Path
from typing import Literal, cast

from flask import redirect, render_template, request, session, url_for
from flask.typing import ResponseReturnValue

from app_types import AuthJsonDict as JsonDict
from config import Config
from decorators import error_context
from errors import AuthenticationError
from route_decorators import simple_success_response
from utils import validate_string_input

logger = logging.getLogger(__name__)


def is_authenticated() -> bool:
    """Check if user is authenticated with Blink.

    Verifies that the global blink object exists and is properly
    authenticated. This is used by route decorators to protect
    endpoints that require authentication.

    Returns:
        True if authenticated and ready for API calls, False otherwise
    """
    # Import here to avoid circular imports
    from blinkapp import blink

    return blink is not None and hasattr(blink, "auth") and blink.auth.startup_complete  # type: ignore[attr-defined]


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
    from blinkapp import blink_connection

    with error_context("initialize Blink system", AuthenticationError):
        from aiohttp import ClientSession

        from blinkpy.auth import Auth  # type: ignore[import-untyped]
        from blinkpy.blinkpy import Blink  # type: ignore[import-untyped,attr-defined]

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
        import blinkapp

        blinkapp.blink = blink

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
    from blinkapp import CREDENTIALS_FILE, blink

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
    import blinkapp
    from blinkapp import CREDENTIALS_FILE

    assert CREDENTIALS_FILE is not None, "Credentials file path must be set"
    cred_file = Path(cast(str, CREDENTIALS_FILE))

    # Check if credentials file exists before attempting to load
    if cred_file.exists():
        try:
            from aiohttp import ClientSession

            from blinkpy.auth import Auth  # type: ignore[import-untyped]
            from blinkpy.blinkpy import (
                Blink,  # type: ignore[import-untyped,attr-defined]
            )
            from blinkpy.helpers.util import json_load  # type: ignore[import-untyped]

            assert CREDENTIALS_FILE is not None
            # Load encrypted credentials from file
            # The json_load function handles decryption automatically
            # Type ignore for mypy issue with blinkpy's json_load function
            auth_data: dict[str, object] | None = await json_load(  # type: ignore[misc]
                cast(str, CREDENTIALS_FILE)
            )

            # Create new HTTP session and attempt authentication with saved data
            session_obj = ClientSession()
            try:
                auth = Auth(auth_data, session=session_obj)  # type: ignore[arg-type]
                blink = Blink(session=session_obj)
                blink.auth = auth

                # Attempt to start Blink system with saved credentials
                success = await blink.start()
                if success is True:
                    logger.info("Blink system loaded from saved credentials")
                    blinkapp.blink = blink  # Update global reference
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


def setup_auth_routes(app_instance):
    """Set up authentication routes on the Flask app instance."""

    @app_instance.route("/login", methods=["GET", "POST"])
    def login() -> ResponseReturnValue:
        """Handle login page GET/POST requests.

        Returns:
            Login form template or redirect based on authentication result
        """
        # Import here to avoid circular imports
        from blinkapp import CREDENTIALS_FILE, blink, blink_connection

        if request.method == "POST":
            try:
                username = validate_string_input(
                    request.form.get("username", ""),
                    Config.MAX_USERNAME_LENGTH,
                    "Username",
                )
                password = validate_string_input(
                    request.form.get("password", ""),
                    Config.MAX_PASSWORD_LENGTH,
                    "Password",
                )
            except ValueError as e:
                return render_template("auth.html", is_2fa=False, error=str(e))

            # Initialize Blink thread if needed
            blink_connection.start()

            try:
                success = blink_connection.execute(initialize_blink(username, password))
                assert blink is not None
                if success == "2fa_required":
                    session["temp_username"] = username
                    session["temp_password"] = password
                    return redirect(url_for("two_factor"))
                elif success:
                    assert CREDENTIALS_FILE is not None
                    blink_connection.execute(blink.save(CREDENTIALS_FILE))
                    session["authenticated"] = True
                    return redirect(url_for("index"))
                else:
                    return render_template(
                        "auth.html",
                        is_2fa=False,
                        error=Config.ErrorMessages.INVALID_CREDENTIALS,
                    )
            except AuthenticationError as e:
                return render_template("login.html", error=str(e))
            except Exception as e:
                logger.error(f"Unexpected login error: {e}")
                return render_template(
                    "auth.html", is_2fa=False, error=Config.ErrorMessages.LOGIN_FAILED
                )

        return render_template("auth.html", is_2fa=False)

    @app_instance.route("/2fa", methods=["GET", "POST"])
    def two_factor() -> ResponseReturnValue:
        """Handle 2FA verification page GET/POST requests.

        Returns:
            2FA form template or redirect based on verification result
        """
        # Import here to avoid circular imports
        from blinkapp import blink_connection

        if "temp_username" not in session:
            return redirect(url_for("login"))

        if request.method == "POST":
            try:
                key = validate_string_input(
                    request.form.get("key", ""), Config.MAX_TFA_LENGTH, "2FA code"
                )
                username = session["temp_username"]
                password = session["temp_password"]
            except ValueError as e:
                return render_template(
                    "auth.html",
                    is_2fa=True,
                    error=str(e),
                    email=session.get("temp_username", ""),
                )

            try:
                logger.debug("Running 2FA verification in Blink thread")
                success = blink_connection.execute(
                    verify_2fa_and_save(username, password, key)
                )

                if success:
                    logger.debug("2FA successful, clearing session and redirecting")
                    session.pop("temp_username", None)
                    session.pop("temp_password", None)
                    session["authenticated"] = True
                    return redirect(url_for("index"))
                else:
                    logger.debug("2FA failed, showing error")
                    return render_template(
                        "auth.html",
                        is_2fa=True,
                        error=Config.ErrorMessages.INVALID_2FA_CODE,
                        email=session.get("temp_username", ""),
                    )
            except AuthenticationError as e:
                return render_template(
                    "auth.html",
                    is_2fa=True,
                    error=str(e),
                    email=session.get("temp_username", ""),
                )
            except Exception as e:
                logger.error(f"Unexpected 2FA error: {e}")
                return render_template(
                    "auth.html",
                    is_2fa=True,
                    error=Config.ErrorMessages.TFA_VERIFICATION_FAILED,
                    email=session.get("temp_username", ""),
                )

        return render_template(
            "auth.html", is_2fa=True, email=session.get("temp_username", "")
        )

    @app_instance.route("/logout", methods=["POST"])
    @simple_success_response("Logged out successfully")
    def logout() -> "JsonDict":
        """Logout user and clear all credentials and caches.

        Returns:
            JSON response with success status
        """
        # Import here to avoid circular imports
        import blinkapp
        from blinkapp import CREDENTIALS_FILE, clear_all_caches, executor

        # Clear caches first in background
        executor.submit(clear_all_caches)

        # Clear session and credentials
        session.clear()
        blinkapp.blink = None
        assert CREDENTIALS_FILE is not None
        cred_file = Path(CREDENTIALS_FILE)
        if cred_file.exists():
            cred_file.unlink()

        return {}  # Decorator will handle the success response
