"""Decorators and utility functions for the Blink Camera Flask application."""

import functools
import logging
import traceback
from collections.abc import Callable, Generator
from contextlib import contextmanager
from functools import wraps
from typing import Any, Protocol, TypeVar

from flask import Response, jsonify, request
from flask.wrappers import Request

from blinkapp.config import Config
from blinkapp.models.types import (
    ApiResponse,
    CacheKey,
    DecoratedRouteFunction,
    DecoratorFunction,
    ErrorResponse,
    FlaskResponse,
    P,
    RouteResult,
    T,
    TemplateResult,
    ValidationFunction,
)

# Type definitions
TemplateF = TypeVar("TemplateF", bound=Callable[..., TemplateResult])

logger = logging.getLogger(__name__)


# Explicitly define what this module exports
__all__ = [
    "error_context",
    "ensure_blink_available",
    "CacheProtocol",
    "api_route",
    "api_route_with_validation",
    "simple_success_response",
    "cached_response",
    "file_response_route",
    "method_dispatch_route",
    "cached_api_route",
    "template_route_with_validation",
    "safe_execute",
    "ensure_blink_available",
    "check_blink_availability",
]


@contextmanager
def error_context(
    operation: str, reraise_as: type[Exception] | None = None
) -> Generator[None, None, None]:
    """Context manager for consistent error handling.

    Args:
        operation: Description of the operation being performed
        reraise_as: Exception type to reraise as (default: BlinkError)

    Yields:
        None: Context for the operation

    Raises:
        BlinkError: If the operation fails (or the specified reraise_as type)
    """
    # Import here to avoid circular dependency
    from blinkapp.utils.errors import BlinkError

    if reraise_as is None:
        reraise_as = BlinkError

    try:
        yield
    except Exception as e:
        # Import logger here to avoid circular imports
        import logging

        logger = logging.getLogger(__name__)

        logger.error(f"Error during {operation}: {e}")
        logger.debug(f"Full traceback for {operation}: {traceback.format_exc()}")
        if isinstance(e, BlinkError):
            raise
        raise reraise_as(f"Failed to {operation}: {str(e)}") from e


def safe_execute(
    func: Callable[[], T], default: T | None = None, log_error: bool = True
) -> T | None:
    """Execute function safely with error logging.

    Args:
        func: Function to execute safely
        default: Default value to return on exception
        log_error: Whether to log errors

    Returns:
        Function result or default value on exception
    """
    try:
        return func()
    except Exception as e:
        if log_error:
            # Import logger here to avoid circular imports
            import logging

            logger = logging.getLogger(__name__)

            logger.error(f"Safe execution failed: {e}")
            logger.debug(f"Full traceback: {traceback.format_exc()}")
        return default


def ensure_blink_available(
    func: Callable[P, T],
) -> Callable[P, T | FlaskResponse]:
    """Decorator that ensures blink is available before calling the function.

    This decorator automatically checks if the Blink system is initialized and
    available, returning an error response if not. It also serves as a type guard,
    telling type checkers that after the check, blink is guaranteed to be non-None.

    Usage in decorated functions:
        @ensure_blink_available
        def my_function() -> ResponseReturnValue:
            assert blink is not None  # For Pylance type narrowing
            return jsonify(blink.sync)  # No type errors
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | FlaskResponse:
        error_response = check_blink_availability()
        if error_response is not None:
            response, status_code = error_response
            return jsonify(response), status_code

        # Import blink here to avoid circular imports
        from blinkapp.services.blink_service import blink

        assert blink is not None  # Help type checkers understand this
        assert blink.available  # Additional assertion for Pylance

        return func(*args, **kwargs)

    return wrapper


def check_blink_availability() -> ApiResponse | None:
    """Check if Blink system is initialized and available.

    Returns:
        None if Blink is available, error response tuple if not initialized or unavailable
    """
    # Import here to avoid circular imports
    import blinkapp
    from blinkapp.services.blink_service import blink

    create_api_response = blinkapp.create_api_response

    if blink is None:
        return create_api_response(
            success=False,
            error=Config.ErrorMessages.SYSTEM_NOT_INITIALIZED,
            status_code=Config.HTTP_STATUS_INTERNAL_ERROR,
        )
    if not blink.available:
        return create_api_response(
            success=False,
            error=Config.ErrorMessages.AUTH_FAILED,
            status_code=401,
        )
    return None


# ============================================================================
# Route decorators (merged from route_decorators.py)
# ============================================================================

"""
Route decorators for Flask application to reduce code duplication.

This module provides decorators that handle common patterns in API routes,
including error handling, response formatting, and validation.
"""


# Explicitly define what this module exports
__all__ = [
    "CacheProtocol",
    "api_route",
    "api_route_with_validation",
    "simple_success_response",
    "cached_response",
    "file_response_route",
    "method_dispatch_route",
    "cached_api_route",
    "template_route_with_validation",
]


# Type variables for template functions


class CacheProtocol(Protocol):
    """Protocol for cache-like objects."""

    def get(self, key: CacheKey, default: Any = None) -> Any: ...
    def __setitem__(self, key: CacheKey, value: Any) -> None: ...


def _get_operation_name(
    func: Callable[..., Any], operation_name: str | None = None
) -> str:
    """Get operation name for logging and error messages."""
    return operation_name or func.__name__.replace("_", " ")


def _handle_response_formatting(result: RouteResult) -> FlaskResponse:
    """Handle common response formatting logic."""
    # Import here to avoid circular import
    from blinkapp import create_api_response

    # If the function already returns a Flask response, pass it through
    if isinstance(result, Response) or (
        isinstance(result, tuple)
        and len(result) >= 2
        and isinstance(result[0], Response)
    ):
        return result

    # Otherwise, wrap in standard API response
    if isinstance(result, dict):
        # For dict results, cast to the expected type
        dict_result = result
        response, status_code = create_api_response(success=True, data=dict_result)
        return jsonify(response), status_code
    else:
        # For non-dict results, wrap in success response
        response, status_code = create_api_response(
            success=True, data={"result": result}
        )
        return jsonify(response), status_code


def _handle_error(e: Exception, operation_name: str) -> ErrorResponse:
    """Handle common error processing logic."""
    # Import here to avoid circular import
    from blinkapp.utils.error_handlers import handle_api_error

    logger.error(f"Error in {operation_name}: {e}")
    response, status_code = handle_api_error(e, operation_name)
    return jsonify(response), status_code


def _validate_json_payload(
    required_fields: list[str] | None = None,
) -> ErrorResponse | None:
    """Validate JSON payload and return error response or None on success."""
    # Import here to avoid circular import
    from blinkapp import Config, create_api_response

    assert isinstance(request, Request)
    data: dict[str, Any] | None = request.get_json()  # pyright: ignore[reportAttributeAccessIssue]
    if data is None or not isinstance(data, dict):
        response, status_code = create_api_response(
            success=False,
            error=Config.ErrorMessages.INVALID_JSON_DATA,
            status_code=400,
        )
        return jsonify(response), status_code

    # Check required fields
    if required_fields:
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            response, status_code = create_api_response(
                success=False,
                error=f"Missing required fields: {', '.join(missing_fields)}",
                status_code=400,
            )
            return jsonify(response), status_code

    return None  # Success - data is available via request.get_json()


def _validate_parameters(
    kwargs: dict[str, Any], validate_params: dict[str, ValidationFunction]
) -> ErrorResponse | None:
    """Validate URL parameters and return error response or None on success.

    Transforms string URL parameters into validated objects using provided
    validation functions. For example, converts "camera_id_str" to a CameraId
    object and replaces it in kwargs as "camera_id".

    Args:
        kwargs: Route function keyword arguments (modified in place)
        validate_params: Mapping of parameter names to validation functions

    Returns:
        Error response tuple if validation fails, None if successful

    Side Effects:
        Modifies kwargs in place, replacing validated parameters
    """
    # Import here to avoid circular import
    from blinkapp import create_api_response

    for param_name, validator in validate_params.items():
        if param_name in kwargs:
            try:
                # Apply validation function (e.g., CameraId(camera_id_str))
                param_value = kwargs[param_name]
                if not isinstance(param_value, str):
                    raise ValueError(f"Parameter {param_name} must be a string")
                validated_value = validator(param_value)

                # Replace string parameter with validated object
                # Remove "_str" suffix from parameter name for cleaner API
                del kwargs[param_name]
                new_param_name = param_name.replace("_str", "")
                kwargs[new_param_name] = validated_value
            except (ValueError, TypeError) as e:
                response, status_code = create_api_response(
                    success=False, error=str(e), status_code=400
                )
                return jsonify(response), status_code

    return None  # Success - kwargs has been modified in place


def _create_base_decorator(
    operation_name: str | None = None,
    validate_json: bool = False,
    required_fields: list[str] | None = None,
    validate_params: dict[str, ValidationFunction] | None = None,
    success_message: str | None = None,
    cache_dict: CacheProtocol | None = None,
    cache_key_func: Callable[..., CacheKey] | None = None,
    skip_response_formatting: bool = False,
) -> DecoratorFunction:
    """
    Base decorator that handles all common patterns.

    This is the core decorator that all other decorators build upon.
    It handles validation, caching, error handling, and response formatting.

    Args:
        operation_name: Optional name for the operation
        validate_json: Whether to validate JSON payload
        required_fields: List of required fields in JSON payload
        validate_params: Dict mapping parameter names to validation functions
        success_message: Success message for simple success responses
        cache_dict: Dictionary to use for caching
        cache_key_func: Function to generate cache key
        skip_response_formatting: If True, return result directly (for file responses)
    """

    def decorator(func: Callable[..., Any]) -> DecoratedRouteFunction:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> FlaskResponse:
            op_name = _get_operation_name(func, operation_name)

            try:
                # Handle caching (check cache first)
                if cache_dict is not None:
                    cache_key = _get_cache_key(cache_key_func, args, kwargs)
                    cached_result = cache_dict.get(cache_key)
                    if cached_result is not None:
                        return _create_cached_response(cached_result)

                # Validate JSON if required
                if validate_json:
                    json_error = _validate_json_payload(required_fields)
                    if json_error is not None:
                        return json_error
                    # json validation passed, data is available via request.get_json()

                # Validate parameters
                if validate_params:
                    # Convert kwargs to mutable dict for validation
                    kwargs_dict = dict(kwargs)
                    param_error = _validate_parameters(kwargs_dict, validate_params)
                    if param_error is not None:
                        return param_error
                    # parameter validation passed, update kwargs
                    # We need to cast back to the original type for the function call
                    kwargs = kwargs_dict

                # Call the original function
                result = func(*args, **kwargs)

                # Handle caching (store result)
                if cache_dict is not None and not _is_error_response(result):
                    cache_key = _get_cache_key(cache_key_func, args, kwargs)
                    cache_dict[cache_key] = result

                # Handle simple success response
                if success_message is not None:
                    return _create_success_message_response(success_message)

                # Handle response formatting
                if skip_response_formatting:
                    # For file responses and method dispatch, the function should return FlaskResponse
                    # Cast to FlaskResponse as this is the expected contract for these decorators
                    return result
                else:
                    return _handle_response_formatting(result)

            except Exception as e:
                return _handle_error(e, op_name)

        return wrapper

    return decorator


def _get_cache_key(
    cache_key_func: Callable[..., CacheKey] | None = None,
    args: tuple[Any, ...] | None = None,
    kwargs: dict[str, Any] | None = None,
) -> CacheKey:
    """Generate cache key from function arguments."""
    if cache_key_func is not None:
        return cache_key_func(*(args or ()), **(kwargs or {}))
    else:
        return str(args[0]) if args is not None else "default"


def _create_cached_response(cached_result: Any) -> FlaskResponse:
    """Create response for cached data."""
    # Import here to avoid circular import
    from blinkapp import create_api_response

    response, status_code = create_api_response(success=True, data=cached_result)
    return jsonify(response), status_code


def _create_success_message_response(message: str) -> FlaskResponse:
    """Create response for simple success messages."""
    # Import here to avoid circular import
    from blinkapp import create_api_response

    response, status_code = create_api_response(success=True, data={"message": message})
    return jsonify(response), status_code


def _is_error_response(result: Any) -> bool:
    """Check if result is an error response (Response object or tuple)."""
    return isinstance(result, Response | tuple)


def api_route(operation_name: str | None = None) -> DecoratorFunction:
    """
    Decorator that handles common API route patterns including:
    - Try-catch error handling with standardized responses
    - Automatic JSON response formatting
    - Operation-specific error context

    Args:
        operation_name: Optional name for the operation (used in error messages)
                       If not provided, uses the function name

    Usage:
        @app.route("/api/example")
        @api_route("example operation")
        def example_endpoint():
            # Your business logic here
            return {"message": "success"}  # Will be wrapped in create_api_response
    """
    return _create_base_decorator(operation_name=operation_name)


def api_route_with_validation(
    operation_name: str | None = None,
    validate_json: bool = False,
    required_fields: list[str] | None = None,
    validate_params: dict[str, ValidationFunction] | None = None,
) -> DecoratorFunction:
    """
    Enhanced API route decorator with built-in validation.

    Args:
        operation_name: Optional name for the operation
        validate_json: Whether to validate that request contains valid JSON
        required_fields: List of required fields in JSON payload
        validate_params: Dict mapping parameter names to validation functions

    Usage:
        @app.route("/api/example", methods=["POST"])
        @api_route_with_validation(
            "example operation",
            validate_json=True,
            required_fields=["name", "value"],
            validate_params={"camera_id": CameraId}
        )
        def example_endpoint(camera_id_str: str):
            # Validation is already done, proceed with business logic
            return {"message": "success"}
    """
    return _create_base_decorator(
        operation_name=operation_name,
        validate_json=validate_json,
        required_fields=required_fields,
        validate_params=validate_params,
    )


def simple_success_response(message: str | None = None) -> DecoratorFunction:
    """
    Decorator for endpoints that just need to return a simple success message.

    Args:
        message: Success message to return. If not provided, uses a default.

    Usage:
        @app.route("/api/clear-cache", methods=["POST"])
        @simple_success_response("Cache clearing initiated")
        def clear_cache():
            executor.submit(clear_all_caches)
            # No return needed - decorator handles the response
    """
    return _create_base_decorator(success_message=message)


def cached_response(
    cache_dict: CacheProtocol, cache_key_func: Callable[..., CacheKey] | None = None
) -> DecoratorFunction:
    """
    Decorator that adds caching to API responses.

    Args:
        cache_dict: Dictionary to use for caching
        cache_key_func: Function to generate cache key from function args
                       If not provided, uses the first argument as key

    Usage:
        @app.route("/api/clip/list")
        @cached_response(clips_metadata_cache, lambda storage_type: storage_type)
        @api_route("get clips")
        def get_clips():
            storage_type = request.args.get("storage", "cloud")
            # ... fetch clips logic ...
            return clips
    """
    return _create_base_decorator(cache_dict=cache_dict, cache_key_func=cache_key_func)


def file_response_route(
    operation_name: str | None = None,
    validate_params: dict[str, ValidationFunction] | None = None,
) -> DecoratorFunction:
    """
    Decorator for routes that return file responses (send_file).

    This decorator handles parameter validation but doesn't wrap the response
    in JSON since file responses need to be returned directly.

    Args:
        operation_name: Optional name for the operation
        validate_params: Dict mapping parameter names to validation functions

    Usage:
        @app.route("/api/clip/<clip_id_str>/thumbnail")
        @file_response_route("get clip thumbnail", validate_params={"clip_id_str": ClipId})
        def get_clip_thumbnail(clip_id_str: str):
            # clip_id_str is validated and converted to clip_id
            # Return send_file() directly - no JSON wrapping
            return send_file(thumbnail_path, mimetype="image/jpeg")
    """
    return _create_base_decorator(
        operation_name=operation_name,
        validate_params=validate_params,
        skip_response_formatting=True,
    )


def method_dispatch_route(operation_name: str | None = None) -> DecoratorFunction:
    """
    Decorator for routes that handle multiple HTTP methods with different logic.

    This decorator provides error handling but lets the function handle
    method-specific logic and response formatting.

    Args:
        operation_name: Optional name for the operation

    Usage:
        @app.route("/api/settings", methods=["GET", "POST"])
        @method_dispatch_route("settings")
        def settings():
            if request.method == "GET":
                # Handle GET logic
                return jsonify(response), status_code
            else:  # POST
                # Handle POST logic
                return jsonify(response), status_code
    """
    return _create_base_decorator(
        operation_name=operation_name, skip_response_formatting=True
    )


def cached_api_route(
    operation_name: str | None = None,
    cache_dict: CacheProtocol | None = None,
    cache_key_func: Callable[..., CacheKey] | None = None,
    validate_params: dict[str, ValidationFunction] | None = None,
) -> DecoratorFunction:
    """
    Combined decorator for API routes with caching and validation.

    This combines the functionality of api_route, cached_response, and validation
    into a single decorator for complex routes.

    Args:
        operation_name: Optional name for the operation
        cache_dict: Dictionary to use for caching
        cache_key_func: Function to generate cache key from function args
        validate_params: Dict mapping parameter names to validation functions

    Usage:
        @app.route("/api/clip/list")
        @cached_api_route(
            "get clips",
            cache_dict=clips_metadata_cache,
            cache_key_func=lambda: request.args.get("storage", "cloud")
        )
        def get_clips():
            # Caching and error handling are automatic
            return clips_data
    """
    return _create_base_decorator(
        operation_name=operation_name,
        cache_dict=cache_dict,
        cache_key_func=cache_key_func,
        validate_params=validate_params,
    )


def template_route_with_validation(
    operation_name: str | None = None,
    validate_form: bool = False,
    form_fields: dict[str, tuple[int, str]]
    | None = None,  # field_name: (max_length, display_name)
) -> Callable[[Callable[..., TemplateResult]], Callable[..., TemplateResult]]:
    """
    Decorator for template routes with form validation.

    Args:
        operation_name: Name of the operation for logging
        validate_form: Whether to validate form data
        form_fields: Dict mapping field names to (max_length, display_name) tuples

    Returns:
        Decorated function that handles form validation and error rendering
    """

    def decorator(func: Callable[..., TemplateResult]) -> Callable[..., TemplateResult]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> TemplateResult:
            from flask import render_template, request

            from blinkapp.utils.validators import validate_string_input

            operation = _get_operation_name(func, operation_name)

            try:
                # Validate form data if POST request and validation enabled
                if request.method == "POST" and validate_form and form_fields:
                    validated_data: dict[str, Any] = {}
                    for field_name, (max_length, display_name) in form_fields.items():
                        field_value = request.form.get(field_name, "")
                        try:
                            validated_data[field_name] = validate_string_input(
                                field_value, max_length, display_name
                            )
                        except ValueError as e:
                            # Return template with error for form validation failures
                            return render_template(
                                "auth.html", is_2fa=False, error=str(e)
                            )

                    # Add validated data to kwargs
                    kwargs.update(validated_data)

                # Call the original function
                result = func(*args, **kwargs)
                return result

            except Exception as e:
                # _handle_error returns ErrorResponse which is compatible with TemplateResult
                return _handle_error(e, operation)

        return wrapper

    return decorator
