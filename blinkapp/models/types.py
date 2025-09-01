"""
Centralized type definitions for the Blink Camera Flask application.

This module contains all common type aliases used throughout the application
to ensure consistency and avoid duplication. Import these types instead of
defining them locally in individual modules.
"""

from collections.abc import Callable
from typing import ParamSpec, TypedDict, TypeVar

from flask import Response
from flask.typing import ResponseReturnValue

# Common type variables used across the application
P = ParamSpec("P")
T = TypeVar("T")


# Clip data structures
class ClipData(TypedDict):
    """Structure for clip data."""

    id: str
    created_at: str
    device_name: str
    thumbnail: str
    media: str


class ClipDayGroup(TypedDict):
    """Structure for clips grouped by day."""

    date: str
    clips: list[ClipData]


# Explicitly define what this module exports
__all__ = [
    "P",
    "T",
    "ClipData",
    "ClipDayGroup",
    "JsonDict",
    "ClipsResponse",
    "AuthJsonDict",
    "ApiResponse",
    "RouteResult",
    "FlaskResponse",
    "ErrorResponse",
    "TemplateResult",
    "DecoratorFunction",
    "DecoratedRouteFunction",
    "ValidationFunction",
    "CacheKey",
    "DeviceDict",
    "SystemDict",
]

# Basic data types
JsonDict = dict[str, object]  # Standard JSON-serializable dictionary
DeviceDict = dict[str, object]  # Device information dictionary
SystemDict = dict[str, object]  # System information dictionary
ClipsResponse = dict[str, list[ClipDayGroup]]  # Clips API response type

# API response types
ApiResponse = tuple[JsonDict, int]  # Standard API response (data, status_code)
ErrorResponse = tuple[Response, int]  # Error response with Flask Response

# Flask response types - use Flask's own types
FlaskResponse = Response | tuple[Response, int] | tuple[Response, int, dict[str, str]]
TemplateResult = str | FlaskResponse  # What template functions can return
RouteResult = FlaskResponse | JsonDict | object  # What route functions can return

# Decorated route function types
DecoratedRouteFunction = Callable[
    ..., FlaskResponse
]  # What decorated route functions return
DecoratorFunction = Callable[
    [Callable[..., object]], DecoratedRouteFunction
]  # Decorator type

# Cache and utility types
CacheKey = str  # Cache key identifier
ValidationFunction = Callable[[str], object]  # Input validation function type

# Auth-specific types
AuthJsonDict = dict[str, str | int | bool]  # Auth module JSON dict
