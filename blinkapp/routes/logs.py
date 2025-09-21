"""Log file viewing routes."""

from flask import Blueprint, Flask, render_template

logs_bp = Blueprint("logs", __name__)


@logs_bp.route("/logs")
def log_viewer() -> str:
    """Display the log file viewer page.

    Returns:
        str: Rendered HTML template for log viewer.
    """
    return render_template("logs.html")


def setup_logs_routes(app: Flask) -> None:
    """Set up log viewing routes.

    Args:
        app: Flask application instance to register routes with.
    """
    app.register_blueprint(logs_bp)
