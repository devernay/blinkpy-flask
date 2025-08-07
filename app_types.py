"""
Centralized type definitions for the Blink Camera Flask application.

This module contains all common type aliases used throughout the application
to ensure consistency and avoid duplication. Import these types instead of
defining them locally in individual modules.
"""

from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from flask import Response
from flask.typing import ResponseReturnValue

# Type variables for generic functions
P = ParamSpec("P")
T = TypeVar("T")

# Basic data types
JsonDict = dict[str, object]  # Standard JSON-serializable dictionary
SettingsDict = dict[str, str | int | bool]  # User settings dictionary
DeviceDict = dict[str, object]  # Device information dictionary
ClipDict = dict[str, object]  # Clip metadata dictionary
SystemDict = dict[str, object]  # System information dictionary

# API response types
ApiResponse = tuple[JsonDict, int]  # Standard API response (data, status_code)
ErrorResponse = tuple[Response, int]  # Error response with Flask Response

# Flask response types - more specific typing
FlaskResponse = Response | tuple[Response, int] | tuple[Response, int, dict[str, Any]]
FlaskRouteResponse = ResponseReturnValue  # What Flask route functions can return
TemplateResult = str | FlaskResponse  # What template functions can return
RouteResult = FlaskResponse | JsonDict | object  # What route functions can return

# Decorated route function types
DecoratedRouteFunction = Callable[
    ..., FlaskResponse
]  # What decorated route functions return
DecoratorFunction = Callable[
    [Callable[..., Any]], DecoratedRouteFunction
]  # Decorator type

# Cache and utility types
CacheKey = str  # Cache key identifier
ValidationFunction = Callable[[str], object]  # Input validation function type

# Auth-specific types
AuthJsonDict = dict[str, Any]  # Auth module JSON dict
