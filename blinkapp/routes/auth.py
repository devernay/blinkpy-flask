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

from flask import Flask, redirect, render_template, request, session, url_for
from flask.typing import ResponseReturnValue

from app_types import AuthJsonDict as JsonDict
from blinkapp.services.auth_service import (
    initialize_blink,
    is_authenticated,
    load_saved_blink,
    verify_2fa_and_save,
)
from blinkapp.utils.errors import AuthenticationError
from blinkapp.utils.validators import validate_string_input
from config import Config
from route_decorators import simple_success_response

logger = logging.getLogger(__name__)

# Explicitly define what this module exports
__all__ = [
    "is_authenticated",
    "initialize_blink",
    "verify_2fa_and_save",
    "load_saved_blink",
    "setup_auth_routes",
]


def setup_auth_routes(app_instance: Flask) -> None:
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
