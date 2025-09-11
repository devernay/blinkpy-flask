"""Centralized type definitions for the Blink Camera Flask application.

This module contains all common type aliases used throughout the application
to ensure consistency and avoid duplication. Import these types instead of
defining them locally in individual modules.
"""

from collections.abc import Callable, Mapping, Sequence
from typing import ParamSpec, TypedDict, TypeVar

from flask import Response

# Common type variables used across the application
P = ParamSpec("P")
T = TypeVar("T")


# Clip data structures
class ClipApiData(TypedDict):
    """Structure for clip data."""

    id: str
    created_at: str
    device_name: str
    thumbnail: str
    media: str


class ClipDayGroup(TypedDict):
    """Structure for clips grouped by day."""

    date: str
    clips: list[ClipApiData]


# Explicitly define what this module exports
__all__ = [
    "P",
    "T",
    "ClipApiData",
    "ClipDayGroup",
    "JsonDict",
    "ClipsResponse",
    "SimpleJsonDict",
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

# Basic data types - use structural types for JSON-serializable objects
JsonValue = (
    str
    | int
    | float
    | bool
    | None
    | Sequence["JsonValue"]  # Any array-like object
    | Mapping[str, "JsonValue"]  # Any dict-like object with str keys
    | list["SystemDict"]
    | list["DeviceDict"]
    | list["ClipDayGroup"]  # Add app-specific types
    | tuple[Response, int]  # Flask response tuples
    | tuple[Response, int, dict[str, str]]  # Flask response tuples with headers
    | tuple["JsonDict", int]  # API response tuples
)
JsonDict = Mapping[str, JsonValue]  # Any dict-like object that can be JSON serialized
DeviceDict = dict[str, JsonValue]  # Device information dictionary
SystemDict = dict[str, JsonValue]  # System information dictionary
ClipsResponse = dict[str, list[ClipDayGroup]]  # Clips API response type

# API response types
ApiResponse = tuple[JsonDict, int]  # Standard API response (data, status_code)
ErrorResponse = tuple[Response, int]  # Error response with Flask Response

# Flask response types - use Flask's own types
FlaskResponse = Response | tuple[Response, int] | tuple[Response, int, dict[str, str]]
TemplateResult = str | FlaskResponse  # What template functions can return
RouteResult = (
    FlaskResponse | JsonDict | tuple[JsonDict, int] | JsonValue
)  # What route functions can return

# Decorated route function types
DecoratedRouteFunction = Callable[
    ..., RouteResult  # Use RouteResult instead of FlaskResponse
]  # What decorated route functions return
DecoratorFunction = Callable[
    [Callable[..., RouteResult]], DecoratedRouteFunction
]  # Decorator type

# Cache and utility types
CacheKey = str  # Cache key identifier
ValidationFunction = Callable[
    [str], object
]  # Input validation function type - validates string input and returns validated object (e.g., CameraId, ClipId)

# Simple types
SimpleJsonDict = dict[
    str, str | int | bool
]  # Simple flat JSON dict without complex nested types
