"""Connexion-compatible authentication handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from flask.wrappers import Response as FlaskResponse
    from werkzeug.wrappers import Response as WerkzeugResponse

ResponseReturnValue = Union[str, tuple[str, int], "FlaskResponse", "WerkzeugResponse"]


def main_page() -> ResponseReturnValue:
    """Main application interface.

    Returns:
        Redirect to login page if not authenticated, otherwise renders main interface.
    """
    from flask import current_app, redirect, render_template, session, url_for

    if not session.get("authenticated"):
        # Check if credentials were loaded at startup and auto-authenticate
        if current_app.config.get("CREDENTIALS_LOADED_AT_STARTUP"):  # type: ignore[misc]  # Flask config typing limitation
            session["authenticated"] = True
        else:
            return redirect(url_for("login_page_route"))

    return render_template("index.html")


def login_page() -> ResponseReturnValue:
    """Login page.

    Returns:
        Rendered authentication template.
    """
    from flask import render_template

    return render_template("auth.html")


def authenticate_user() -> ResponseReturnValue:
    """Authenticate user with email and password.

    NOTE: This handler is called by login_page_route() on POST requests,
    not by a dedicated authenticate_user_route().

    Returns:
        ResponseReturnValue: Redirect to main page on success or auth template with error.
    """
    from flask import redirect, render_template, request, url_for

    from ..services.auth_service import handle_login

    username = request.form.get("username", "")
    password = request.form.get("password", "")

    if not username or not password:
        return render_template("auth.html", error="Username and password required"), 400

    auth_result = handle_login(username, password)

    if auth_result.get("requires_2fa"):
        return redirect(url_for("twofa_page_route"))
    elif auth_result.get("success"):
        return redirect(url_for("main_page_route"))
    else:
        return render_template(
            "auth.html", error=auth_result.get("error", "Authentication failed")
        ), 400


def twofa_page() -> ResponseReturnValue:
    """2FA verification page.

    Returns:
        Redirect to main page if already authenticated, otherwise renders 2FA template.
    """
    from flask import redirect, render_template, session, url_for

    if not session.get("pending_2fa"):
        return redirect(url_for("login_page_route"))

    return render_template("auth.html", is_2fa=True)


def verify_twofa() -> ResponseReturnValue:
    """Verify 2FA code and complete authentication.

    NOTE: This handler is called by twofa_page_route() on POST requests,
    not by a dedicated verify_twofa_route().

    Returns:
        ResponseReturnValue: Redirect to main page on success or auth template with error.
    """
    from flask import redirect, render_template, request, url_for

    from ..services.auth_service import handle_2fa_verification

    code = request.form.get("key", "")

    if not code:
        return render_template(
            "auth.html", show_2fa=True, error="2FA code required"
        ), 400

    verify_result = handle_2fa_verification(code)

    if verify_result.get("success"):
        return redirect(url_for("main_page_route"))
    else:
        return render_template(
            "auth.html",
            show_2fa=True,
            error=verify_result.get("error", "2FA verification failed"),
        ), 400


def logout_user() -> ResponseReturnValue:
    """Logout user.

    Returns:
        Redirect to login page after clearing session.
    """
    from flask import redirect, url_for

    from ..services.auth_service import handle_logout

    handle_logout()
    return redirect(url_for("login_page_route"))
