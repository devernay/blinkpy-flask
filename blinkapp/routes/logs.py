"""Log file viewing routes."""

from flask import Blueprint, Flask, render_template

logs_bp = Blueprint("logs", __name__)


@logs_bp.route("/logs")
def log_viewer() -> str:
    """Display the log file viewer page."""
    return render_template("logs.html")


def setup_logs_routes(app: Flask) -> None:
    """Set up log viewing routes."""
    app.register_blueprint(logs_bp)
