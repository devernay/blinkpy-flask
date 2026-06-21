"""Connexion-compatible settings handlers."""

from ..models.types import JsonDict


def get_app_config() -> JsonDict:
    """Get application configuration.

    Returns:
        Application configuration
    """
    from ..services.settings_service import get_app_config

    return get_app_config()


def get_user_settings() -> JsonDict:
    """Get user settings.

    Returns:
        User settings
    """
    from ..services.settings_service import get_user_settings

    return get_user_settings()


def update_user_settings(body: JsonDict) -> JsonDict | tuple[JsonDict, int]:
    """Update user settings.

    Args:
        body: Settings update data

    Returns:
        Update result
    """
    from ..services.settings_service import update_settings

    if not body:
        return {"success": False, "error": "No settings data provided"}, 400

    result = update_settings(body)

    # If the session lifetime changed, apply it immediately.
    if "sessionLifetimeDays" in body:
        from ..services.auth_service import refresh_session_lifetime

        refresh_session_lifetime()

    return result
