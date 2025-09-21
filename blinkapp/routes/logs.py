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

    # Add API route for logs
    @app.route("/api/log")
    def api_log_route() -> dict | tuple[dict, int]:
        """API endpoint for log data.

        Returns:
            dict | tuple[dict, int]: Log data response or error response with status code.
        """
        from flask import request

        from ..connexion_handlers.logs import get_logs

        level = request.args.get("level", "DEBUG")
        module = request.args.get("module", "*")

        return get_logs(level=level, module=module)
