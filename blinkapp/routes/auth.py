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

from blinkapp.config import Config
from blinkapp.connexion_handlers.auth import main_page
from blinkapp.models.types import AuthJsonDict as JsonDict, FlaskResponseType
from blinkapp.services.auth_service import (
    initialize_blink,
    verify_2fa_and_save,
)
from blinkapp.utils.errors import AuthenticationError
from blinkapp.utils.route_decorators import simple_success_response
from blinkapp.utils.validators import validate_string_input


def is_session_authenticated() -> bool:
    """Check if user has an authenticated web session.

    Returns:
        True if user has an authenticated session, False otherwise
    """
    return "authenticated" in session


logger = logging.getLogger(__name__)

# Explicitly define what this module exports
__all__ = [
    "setup_auth_routes",
]


def setup_auth_routes(app_instance: Flask) -> None:
    """Set up authentication routes on the Flask app instance."""

    @app_instance.route("/login", methods=["GET", "POST"])
    def login_route() -> FlaskResponseType:
        """Handle login page GET/POST requests.

        Returns:
            Login form template or redirect based on authentication result
        """
        # Import here to avoid circular imports
        # Import here to avoid circular dependency
        from blinkapp import CREDENTIALS_FILE
        from blinkapp.services.blink_service import blink, blink_connection

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
            if blink_connection is None:
                return render_template(
                    "auth.html", is_2fa=False, error="Blink connection not initialized"
                )

            blink_connection.start()

            try:
                success = blink_connection.execute(initialize_blink(username, password))
                assert blink is not None
                if success == "2fa_required":
                    session["temp_username"] = username
                    session["temp_password"] = password
                    return redirect(url_for("two_factor_route"))
                elif success:
                    assert CREDENTIALS_FILE is not None
                    assert blink_connection is not None
                    blink_connection.execute(blink.save(CREDENTIALS_FILE))
                    session["authenticated"] = True
                    return redirect(url_for("index_route"))
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
    def two_factor_route() -> FlaskResponseType:
        """Handle 2FA verification page GET/POST requests.

        Returns:
            2FA form template or redirect based on verification result
        """
        # Import here to avoid circular imports
        # Import here to avoid circular dependency
        from blinkapp.services.blink_service import blink_connection

        if "temp_username" not in session:
            return redirect(url_for("login_route"))

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
                if blink_connection is None:
                    return render_template(
                        "auth.html",
                        is_2fa=True,
                        error="Blink connection not initialized",
                    )
                success = blink_connection.execute(
                    verify_2fa_and_save(username, password, key)
                )

                if success:
                    logger.debug("2FA successful, clearing session and redirecting")
                    session.pop("temp_username", None)
                    session.pop("temp_password", None)
                    session["authenticated"] = True
                    return redirect(url_for("index_route"))
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
    def logout_route() -> "JsonDict":
        """Logout user and clear all credentials and caches.

        Returns:
            JSON response with success status
        """
        # Import here to avoid circular imports

        # Import here to avoid circular dependency
        from blinkapp import CREDENTIALS_FILE, clear_all_caches
        from blinkapp.services.connection_service import ensure_executor_initialized

        # Clear caches first in background
        executor = ensure_executor_initialized()
        executor.submit(clear_all_caches)

        # Clear session and credentials
        session.clear()

        # Clear global blink instance
        from blinkapp.services.blink_service import blink_connection

        if blink_connection:
            blink_connection.shutdown()

        assert CREDENTIALS_FILE is not None
        cred_file = Path(CREDENTIALS_FILE)
        if cred_file.exists():
            cred_file.unlink()

        return {}  # Decorator will handle the success response


def register_auth_routes(app: Flask) -> None:
    """Register authentication routes with the Flask app."""

    @app.route("/")
    def main_page_route() -> FlaskResponseType:
        """Main page - redirect to login if not authenticated.

        Returns:
            Redirect to login page or rendered index template
        """
        if "authenticated" not in session:
            # Check if Blink is available from saved credentials
            from blinkapp.services.blink_service import blink

            if blink and blink.available:
                session["authenticated"] = True
                return main_page()
            else:
                return redirect(url_for("login_route"))
        # Clear initializing flag if set
        session.pop("initializing", None)
        return main_page()
