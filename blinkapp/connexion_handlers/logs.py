"""Connexion handlers for log file operations."""

import re
from pathlib import Path
from typing import Any

from blinkapp.config import Config


def get_logs(
    level: str = "DEBUG", module: str = "*"
) -> dict[str, Any] | tuple[dict[str, str], int]:
    """Get log entries with optional filtering.

    Args:
        level: Minimum log level to show (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        module: Module name to filter by, or "*" for all modules

    Returns:
        dict: Response containing logs and available modules
    """
    log_file = Path(Config.get_log_file_path())
    if not log_file.exists():
        return {"logs": [], "modules": []}

    try:
        with open(log_file, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return {"error": f"Failed to read log file: {e}"}, 500

    log_entries: list[dict[str, str]] = []
    modules: set[str] = set()
    level_values = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }
    min_level = level_values.get(level.upper(), 10)

    log_pattern = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - ([^-]+) - (\w+) - (.+)"
    )

    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = log_pattern.match(line)
        if match:
            timestamp, log_module, log_level, message = match.groups()
            log_module = log_module.strip()
            log_level = log_level.strip()

            modules.add(log_module)

            if level_values.get(log_level, 0) >= min_level:
                if module == "*" or log_module == module:
                    log_entries.append(
                        {
                            "timestamp": timestamp,
                            "module": log_module,
                            "level": log_level,
                            "message": message.strip(),
                        }
                    )
        else:
            if log_entries:
                log_entries[-1]["message"] += "\n" + line

    return {"logs": log_entries, "modules": sorted(modules)}
