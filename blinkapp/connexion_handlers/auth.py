"""Connexion-compatible authentication handlers."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Response


def main_page() -> "Response":
    """Main application interface."""
    from flask import redirect, render_template, session, url_for

    if not session.get("authenticated"):
        return redirect(url_for("login_page_route"))

    return render_template("index.html")


def login_page() -> "Response":
    """Login page."""
    from flask import render_template

    return render_template("auth.html")


def authenticate_user() -> "Response":
    """Authenticate user.

    NOTE: This handler is called by login_page_route() on POST requests,
    not by a dedicated authenticate_user_route().
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


def twofa_page() -> "Response":
    """2FA verification page."""
    from flask import redirect, render_template, session, url_for

    if not session.get("pending_2fa"):
        return redirect(url_for("login_page_route"))

    return render_template("auth.html", show_2fa=True)


def verify_twofa() -> "Response":
    """Verify 2FA code.

    NOTE: This handler is called by twofa_page_route() on POST requests,
    not by a dedicated verify_twofa_route().
    """
    from flask import redirect, render_template, request, url_for

    from ..services.auth_service import handle_2fa_verification

    code = request.form.get("code", "")

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


def logout_user() -> "Response":
    """Logout user."""
    from flask import redirect, url_for

    from ..services.auth_service import handle_logout

    handle_logout()
    return redirect(url_for("login_page_route"))
