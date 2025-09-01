"""Settings service for loading and managing user preferences."""

import json
import logging
from pathlib import Path
from typing import Any

import blinkapp
from blinkapp.config import Config

logger = logging.getLogger(__name__)

__all__ = ["get_user_settings", "get_temperature_unit"]


def get_user_settings() -> dict[str, Any]:
    """Load user settings from file or return defaults.

    Returns:
        Dictionary containing user settings with keys:
        - temperatureUnits: "celsius" or "fahrenheit"
        - cloudClipRetention: retention period in days
        - localClipRetention: "never" or retention period
        - clipThumbnailSize: "small", "medium", or "large"
    """
    # Use the global cache directory if available, otherwise use default
    cache_dir = blinkapp.CACHE_DIR or Config.DEFAULT_CACHE_DIR
    settings_file = Path(cache_dir) / "settings.json"

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
        "temperatureUnits": "celsius",
        "cloudClipRetention": "30",
        "localClipRetention": "never",
        "clipThumbnailSize": "medium",
    }
    logger.debug("Using default settings")
    return default_settings


def get_temperature_unit() -> str:
    """Get the user's preferred temperature unit.

    Returns:
        Temperature unit preference: "celsius" or "fahrenheit"
    """
    settings = get_user_settings()
    unit = settings.get("temperatureUnits", "celsius")

    # Validate and normalize the unit
    if unit.lower() in ("celsius", "c"):
        return "celsius"
    elif unit.lower() in ("fahrenheit", "f"):
        return "fahrenheit"
    else:
        logger.warning(f"Invalid temperature unit '{unit}', defaulting to celsius")
        return "celsius"
