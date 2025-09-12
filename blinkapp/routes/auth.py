"""Authentication routes for Blink Camera Flask application."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask
    from flask import Response as FlaskResponse
    from werkzeug.wrappers import Response as WerkzeugResponse

type ResponseReturnValue = str | tuple[str, int] | "FlaskResponse" | "WerkzeugResponse"


def setup_auth_routes(app: Flask) -> None:
    """Set up authentication routes with the Flask app.

    Args:
        app: Flask application instance to register routes with.
    """

    @app.route("/")
    def main_page_route() -> ResponseReturnValue:
        """Main page route - serves the main application page.

        Returns:
            ResponseReturnValue: Main page template or redirect response.
        """
        from ..connexion_handlers.auth import main_page

        return main_page()

    @app.route("/login", methods=["GET", "POST"])
    def login_page_route() -> ResponseReturnValue:
        """Login route - handles both GET (show form) and POST (authenticate) requests.

        NOTE: Exception to naming convention - this route calls both login_page()
        and authenticate_user() handlers based on HTTP method.

        Returns:
            ResponseReturnValue: Login form template or authentication redirect response.
        """
        from flask import request

        from ..connexion_handlers.auth import authenticate_user, login_page

        if request.method == "GET":
            return login_page()
        return authenticate_user()

    @app.route("/2fa", methods=["GET", "POST"])
    def twofa_page_route() -> ResponseReturnValue:
        """2FA route - handles both GET (show form) and POST (verify code) requests.

        NOTE: Exception to naming convention - this route calls both twofa_page()
        and verify_twofa() handlers based on HTTP method.

        Returns:
            ResponseReturnValue: 2FA form template or verification redirect response.
        """
        from flask import request

        from ..connexion_handlers.auth import twofa_page, verify_twofa

        if request.method == "GET":
            return twofa_page()
        return verify_twofa()

    @app.route("/logout", methods=["POST"])
    def logout_user_route() -> ResponseReturnValue:
        """Logout route - clears user session and redirects to login page.

        Returns:
            ResponseReturnValue: Redirect response to login page.
        """
        from ..connexion_handlers.auth import logout_user

        return logout_user()
