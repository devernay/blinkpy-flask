"""Settings service for loading and managing user preferences."""

import json
import logging
from pathlib import Path
from typing import Literal

import blinkapp
from blinkapp.config import Config
from blinkapp.models.types import JsonDict

logger = logging.getLogger(__name__)

__all__ = ["get_user_settings", "get_temperature_unit", "get_app_config"]


def get_app_config() -> JsonDict:
    """Get application configuration.

    Returns:
        JSON response with configuration data
    """
    return {
        "version": "1.0.0",
        "features": {
            "live_streaming": True,
            "clip_management": True,
            "thumbnail_caching": True,
            "settings_persistence": True,
        },
        "limits": {
            "max_clip_cache_size": Config.CLIPS_CACHE_SIZE,
            "thumbnail_cache_max_age": 300,  # 5 minutes
            "api_timeout": 30,
        },
        "supported_formats": {
            "video": ["mp4"],
            "image": ["jpg", "jpeg"],
            "streaming": ["hls", "m3u8"],
        },
    }


def update_settings(settings_data: JsonDict) -> JsonDict | tuple[JsonDict, int]:
    """Update user settings.

    Args:
        settings_data: Dictionary containing settings to update

    Returns:
        Updated settings dictionary or error response
    """
    import json

    try:
        settings_path = get_settings_file_path()

        # Load existing settings or use defaults
        current_settings = get_user_settings()

        # Update with new settings - convert to dict first
        settings_dict = dict(current_settings)
        settings_dict.update(settings_data)

        # Save to file
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_path, "w") as f:
            json.dump(settings_dict, f, indent=2)

        return {"success": True, "data": current_settings}

    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return {"success": False, "error": str(e)}, 500


def get_user_settings() -> JsonDict:
    """Load user settings from file or return defaults.

    Returns:
        Dictionary containing user settings with keys:
        - temperatureUnits: "C" or "F"
        - cloudClipRetention: retention period in days
        - localClipRetention: "never" or retention period
        - clipThumbnailSize: "small", "medium", or "large"
    """
    # Use the settings file path accessor
    settings_file = get_settings_file_path()

    try:
        if settings_file.exists():
            with open(settings_file) as f:
                settings_data = json.load(f)
                logger.debug(f"Loaded user settings from {settings_file}")
                return settings_data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load settings from {settings_file}: {e}")

    # Return default settings if file doesn't exist or can't be loaded
    default_settings = {
        "temperatureUnits": "C",
        "cloudClipRetention": "30",
        "localClipRetention": "never",
        "clipThumbnailSize": "medium",
    }
    logger.debug("Using default settings")
    return default_settings


def get_temperature_unit() -> Literal["C", "F"]:
    """Get the user's preferred temperature unit.

    Returns:
        Temperature unit preference: "C" for Celsius or "F" for Fahrenheit

    Raises:
        ValueError: If temperatureUnits setting is not "C" or "F"
    """
    settings = get_user_settings()
    unit = settings.get("temperatureUnits", "C")

    if unit not in ("C", "F"):
        raise ValueError(f"Invalid temperature unit '{unit}', must be 'C' or 'F'")

    return unit


def get_settings_file_path() -> Path:
    """Get the settings file path.

    Returns:
        Path: Resolved path to the settings file.
    """
    assert blinkapp._SETTINGS_FILE_PATH is not None, (
        "Cache paths not initialized. Call initialize_cache_paths() first."
    )
    return blinkapp._SETTINGS_FILE_PATH
