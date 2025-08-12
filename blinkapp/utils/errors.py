"""Error classes for the Blink Camera Flask application."""


class BlinkError(Exception):
    """Base exception for Blink-related errors."""

    pass


class ValidationError(Exception):
    """Exception for validation errors with custom status codes."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthenticationError(BlinkError):
    """Authentication-related errors."""

    pass


class CameraError(BlinkError):
    """Camera-related errors."""

    pass


class StreamError(BlinkError):
    """Streaming-related errors."""

    pass


class CacheError(BlinkError):
    """Cache-related errors."""

    pass
