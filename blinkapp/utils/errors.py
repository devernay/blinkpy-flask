"""Error classes for the Blink Camera Flask application."""

# Explicitly define what this module exports
__all__ = [
    "BlinkError",
    "ValidationError",
    "AuthenticationError",
    "CameraError",
    "StreamError",
    "CacheError",
]


class BlinkError(Exception):
    """Base exception for Blink-related errors."""


class ValidationError(Exception):
    """Exception for validation errors with custom status codes."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthenticationError(BlinkError):
    """Authentication-related errors."""


class CameraError(BlinkError):
    """Camera-related errors."""


class StreamError(BlinkError):
    """Streaming-related errors."""


class CacheError(BlinkError):
    """Cache-related errors."""
