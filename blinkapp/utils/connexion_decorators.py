"""Decorators for connexion handlers."""

from collections.abc import Callable
from datetime import datetime
from functools import wraps

from ..models.types import JsonDict

__all__ = ["api_response"]


def api_response(
    func: Callable[..., JsonDict | dict[str, str]],
) -> Callable[..., JsonDict]:
    """Decorator to wrap connexion handler responses in standard API format.

    Converts raw data returns into {"success": True, "data": ..., "timestamp": "..."} format.
    """

    @wraps(func)
    def wrapper(*args: str | int, **kwargs: str | int) -> JsonDict:
        result = func(*args, **kwargs)
        # Ensure result is compatible with JsonValue
        data_value: JsonDict | dict[str, str] = result
        response: JsonDict = {
            "success": True,
            "data": data_value,
            "timestamp": datetime.now().isoformat(),
        }
        return response

    return wrapper
