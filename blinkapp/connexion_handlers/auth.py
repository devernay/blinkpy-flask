"""Connexion-compatible authentication handlers."""

from flask import render_template


def index() -> str:
    """Render the main application page.

    Returns:
        Rendered HTML template
    """
    return render_template("index.html")
