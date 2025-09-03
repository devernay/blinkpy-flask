"""Authentication routes for Blink Camera Flask application."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask.typing import ResponseReturnValue

if TYPE_CHECKING:
    from flask import Flask


def register_auth_routes(app: Flask) -> None:
    """Register authentication routes with the Flask app.

    Args:
        app: Flask application instance to register routes with.
    """

    @app.route("/")
    def main_page_route() -> ResponseReturnValue:
        """Main page route - thin wrapper around connexion handler."""
        from ..connexion_handlers.auth import main_page

        return main_page()

    @app.route("/login", methods=["GET", "POST"])
    def login_page_route() -> ResponseReturnValue:
        """Login route - thin wrapper around connexion handlers.

        NOTE: Exception to naming convention - this route calls both login_page()
        and authenticate_user() handlers based on HTTP method.
        """
        from flask import request

        from ..connexion_handlers.auth import authenticate_user, login_page

        if request.method == "GET":
            return login_page()
        else:
            return authenticate_user()

    @app.route("/2fa", methods=["GET", "POST"])
    def twofa_page_route() -> ResponseReturnValue:
        """2FA route - thin wrapper around connexion handlers.

        NOTE: Exception to naming convention - this route calls both twofa_page()
        and verify_twofa() handlers based on HTTP method.
        """
        from flask import request

        from ..connexion_handlers.auth import twofa_page, verify_twofa

        if request.method == "GET":
            return twofa_page()
        else:
            return verify_twofa()

    @app.route("/logout", methods=["POST"])
    def logout_user_route() -> ResponseReturnValue:
        """Logout route - thin wrapper around connexion handler."""
        from ..connexion_handlers.auth import logout_user

        return logout_user()


def setup_auth_routes(app: Flask) -> None:
    """Alias for register_auth_routes for compatibility.

    Args:
        app: Flask application instance to register routes with.
    """
    register_auth_routes(app)
