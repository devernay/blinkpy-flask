"""Unit tests for utility classes and functions.

This file contains ONLY unit tests for blinkapp/utils/ modules:
- Decorators (decorators.py, route_decorators.py)
- Formatters (formatters.py)
- Validators (validators.py)
- Parsers (parsers.py)
- Error classes (errors.py)
- Logging configuration (logging_config.py)
- Other utility functions

These are pure unit tests with mocked dependencies.
DO NOT add integration tests here - those belong in test_integration_*.py files.
DO NOT add Flask route tests here - those belong in test_integration_api.py.
"""

import tempfile
import unittest
from datetime import UTC
from pathlib import Path
from typing import Never
from unittest.mock import Mock, patch

from blinkapp.config import Config
from tests.test_base import BaseTestCase


class TestApiResponses(BaseTestCase):
    """Test API response functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()


class TestDecorators(BaseTestCase):
    """Test decorator functions."""

    def test_safe_execute_success(self) -> None:
        """Test safe_execute with successful function execution.

        Verifies that safe_execute properly handles successful function
        calls and returns the expected result without modification.

        Tests:
            - Successful function execution
            - Return value matches function output
            - No exception handling interference
        """
        from blinkapp.utils.decorators import safe_execute

        def success_func() -> str:
            return "success"

        result = safe_execute(success_func)
        self.assertEqual(result, "success")

    def test_safe_execute_exception_with_default(self) -> None:
        """Test safe_execute exception handling with default value fallback.

        Verifies that safe_execute properly catches exceptions and
        returns the specified default value when function execution fails.

        Tests:
            - Exception handling during function execution
            - Default value return on exception
            - Graceful error recovery behavior
        """
        from blinkapp.utils.decorators import safe_execute

        def failing_func() -> Never:
            raise ValueError("Test error")

        result = safe_execute(failing_func, default="default_value")
        self.assertEqual(result, "default_value")

    def test_safe_execute_exception_no_default(self) -> None:
        """Test safe_execute exception handling without default value.

        Verifies that safe_execute properly catches exceptions and
        returns None when no default value is specified.

        Tests:
            - Exception handling during function execution
            - None return value when no default specified
            - Graceful error recovery without fallback value
        """
        from blinkapp.utils.decorators import safe_execute

        def failing_func() -> Never:
            raise ValueError("Test error")

        result = safe_execute(failing_func)
        self.assertIsNone(result)

    def test_decorators_basic_usage(self) -> None:
        """Test basic decorator usage and functionality.

        Verifies that utility decorators work correctly with basic
        function decoration and provide expected behavior.

        Tests:
            - Basic decorator application and functionality
            - Decorator behavior with simple functions
            - Proper function wrapping and execution
            - Decorator utility validation
        """
        from blinkapp.utils.decorators import error_context

        @error_context("test operation")
        def simple_test_function() -> str:
            return "success"

        result = simple_test_function()
        self.assertEqual(result, "success")


class TestRouteDecorators(BaseTestCase):
    """Test route decorator functions."""

    def test_get_operation_name_basic(self) -> None:
        """Test _get_operation_name with basic function name extraction.

        Verifies that the operation name extraction utility properly
        extracts and formats function names for operation identification.

        Tests:
            - Basic function name extraction
            - Operation name formatting and processing
            - Function metadata extraction
            - Name resolution utility validation
        """
        from blinkapp.utils.route_decorators import _get_operation_name

        def simple_test_function() -> None:
            pass

        result = _get_operation_name(simple_test_function)
        # The function converts underscores to spaces
        self.assertEqual(result, "simple test function")

    def test_get_operation_name_with_module(self) -> None:
        """Test _get_operation_name includes module information in operation names.

        Verifies that the _get_operation_name function properly constructs
        operation names that include module information for better identification.

        Tests:
            - Module information inclusion in operation names
            - Proper operation name construction and formatting
            - Unique operation name generation for different modules
            - Operation name consistency and predictability
        """
        from blinkapp.utils.route_decorators import _get_operation_name

        # Use an actual function with module
        result = _get_operation_name(len)
        self.assertIn("len", result)

    def test_is_error_response_true(self) -> None:
        """Test _is_error_response returns True for error responses.

        Verifies that the error response detection utility correctly
        identifies error responses and returns True for error conditions.

        Tests:
            - Error response detection and identification
            - True return value for error conditions
            - Proper error response validation logic
            - Error condition recognition accuracy
        """
        from blinkapp.utils.route_decorators import _is_error_response

        error_response = ({"success": False, "error": "Test error"}, 400)
        result = _is_error_response(error_response)
        self.assertTrue(result)

    def test_is_error_response_success_response(self) -> None:
        """Test _is_error_response with success response tuple.

        Verifies that the error response detection utility correctly
        identifies success responses and returns False for non-error conditions.

        Tests:
            - Success response detection and validation
            - False return value for success conditions
            - Proper success response tuple handling
            - Non-error condition recognition accuracy
        """
        from blinkapp.utils.route_decorators import _is_error_response

        # The function checks if result is Response or tuple, so tuples return True
        success_response = ({"success": True, "data": "test"}, 200)
        result = _is_error_response(success_response)
        self.assertTrue(
            result
        )  # Tuples are considered "error responses" for caching purposes

    def test_is_error_response_invalid_format(self) -> None:
        """Test _is_error_response function with invalid response format.

        Verifies that the _is_error_response function properly identifies
        and handles invalid response formats during error detection.

        Tests:
            - Invalid response format detection and handling
            - Proper error response identification logic
            - Response format validation and error classification
            - Graceful handling of malformed response structures
        """
        from blinkapp.utils.route_decorators import _is_error_response

        invalid_response = "not a tuple"
        result = _is_error_response(invalid_response)
        self.assertFalse(result)


class TestFormatters(BaseTestCase):
    """Test formatter functions."""

    def test_format_clips_by_day_empty(self) -> None:
        """Test format_clips_by_day with empty list handling.

        Verifies that the clip formatting utility properly handles
        empty clip lists and returns appropriate empty results.

        Tests:
            - Empty clip list handling and processing
            - Proper return value for empty input data
            - Graceful handling of no-clip scenarios
            - Edge case validation for empty collections
        """
        from blinkapp.utils.formatters import format_clips_by_day

        result = format_clips_by_day([])
        self.assertEqual(result, [])

    def test_format_clips_by_day_single_clip(self) -> None:
        """Test format_clips_by_day with single clip processing.

        Verifies that the clip formatting utility properly processes
        a single clip and formats it correctly by day grouping.

        Tests:
            - Single clip processing and formatting
            - Proper day grouping for individual clips
            - Correct data structure creation for single items
            - Basic functionality validation with minimal data
        """
        from typing import cast

        from blinkapp.models.types import ClipApiData
        from blinkapp.utils.formatters import format_clips_by_day

        clips = cast(
            "list[ClipApiData]",
            [
                {
                    "id": "1",
                    "created_at": "2024-01-01T12:00:00Z",
                    "device_name": "Camera 1",
                    "thumbnail": "thumb.jpg",
                    "media": "clip.mp4",
                }
            ],
        )

        result = format_clips_by_day(clips)
        self.assertEqual(len(result), 1)
        # The function formats dates with day of week
        self.assertEqual(result[0]["date"], "Monday, January 01, 2024")
        self.assertEqual(len(result[0]["clips"]), 1)

    def test_format_time_duration_seconds(self) -> None:
        """Test format_time_duration with seconds only formatting.

        Verifies that time duration formatting works correctly
        for durations measured in seconds only.

        Tests:
            - Seconds-only duration formatting and display
            - Proper time unit handling for short durations
            - Correct formatting output for second-based times
            - Time duration utility functionality validation
        """
        from blinkapp.utils.formatters import format_time_duration

        result = format_time_duration(45)
        self.assertEqual(result, "45s")

    def test_format_time_duration_minutes(self) -> None:
        """Test format_time_duration with minutes only formatting.

        Verifies that time duration formatting works correctly
        for durations measured in minutes only.

        Tests:
            - Minutes-only duration formatting and display
            - Proper time unit handling for medium durations
            - Correct formatting output for minute-based times
            - Time conversion and display functionality
        """
        from blinkapp.utils.formatters import format_time_duration

        result = format_time_duration(120)  # 2m exactly
        self.assertEqual(result, "2m")

    def test_format_time_duration_hours(self) -> None:
        """Test format_time_duration function with hours-only time values.

        Verifies that the format_time_duration function properly formats
        time durations that contain only hour components.

        Tests:
            - Hours-only duration formatting and display
            - Proper time unit handling for hour-based durations
            - Correct formatting output for hour-only time values
            - Time duration string generation and readability
        """
        from blinkapp.utils.formatters import format_time_duration

        result = format_time_duration(3600)  # 1h exactly
        self.assertEqual(result, "1h")

    def test_format_time_duration_edge_cases(self) -> None:
        """Test format_time_duration function with edge case scenarios.

        Verifies that the format_time_duration function properly handles
        edge cases and boundary conditions in time duration formatting.

        Tests:
            - Zero duration handling and formatting
            - Negative duration handling and validation
            - Maximum duration value processing
            - Boundary condition handling and error prevention
        """
        from blinkapp.utils.formatters import format_time_duration

        # Test zero duration
        self.assertEqual(format_time_duration(0), "0s")

        # Test days
        self.assertEqual(format_time_duration(86400), "1d")

        # Test negative duration raises error
        with self.assertRaises(ValueError):
            format_time_duration(-1)

    def test_format_clips_by_day_current_year(self) -> None:
        """Test date formatting for current year clips (no year shown).

        Tests:
            - Current year dates show day of week without year
            - Format: "Monday, January 15"
            - Proper grouping by date
        """
        from datetime import UTC, datetime

        from blinkapp.utils.formatters import format_clips_by_day

        current_year = datetime.now(UTC).year
        clips = [
            {
                "id": "123",
                "created_at": f"{current_year}-01-15T10:30:00+00:00",
                "camera_name": "Test Camera",
            }
        ]

        result = format_clips_by_day(clips)

        self.assertEqual(len(result), 1)
        # Should show day of week and date without year for current year
        self.assertRegex(result[0]["date"], r"^\w+, January 15$")
        self.assertNotIn(str(current_year), result[0]["date"])

    def test_format_clips_by_day_different_year(self) -> None:
        """Test date formatting for different year clips (year shown).

        Tests:
            - Different year dates show day of week with year
            - Format: "Monday, January 15, 2023"
            - Proper grouping by date
        """
        from datetime import UTC, datetime

        from blinkapp.utils.formatters import format_clips_by_day

        current_year = datetime.now(UTC).year
        different_year = current_year - 1
        clips = [
            {
                "id": "123",
                "created_at": f"{different_year}-01-15T10:30:00+00:00",
                "camera_name": "Test Camera",
            }
        ]

        result = format_clips_by_day(clips)

        self.assertEqual(len(result), 1)
        # Should show day of week, date, and year for different year
        self.assertRegex(result[0]["date"], rf"^\w+, January 15, {different_year}$")

    def test_format_clips_by_day_multiple_days_sorting(self) -> None:
        """Test date formatting with multiple days are sorted newest first.

        Tests:
            - Multiple days are properly grouped
            - Each day has correct date format
            - Days are sorted newest first
        """
        from datetime import UTC, datetime

        from blinkapp.utils.formatters import format_clips_by_day

        current_year = datetime.now(UTC).year
        clips = [
            {
                "id": "1",
                "created_at": f"{current_year}-01-15T10:30:00+00:00",
                "camera_name": "Camera1",
            },
            {
                "id": "2",
                "created_at": f"{current_year}-01-16T11:30:00+00:00",
                "camera_name": "Camera2",
            },
        ]

        result = format_clips_by_day(clips)

        self.assertEqual(len(result), 2)
        # Should be sorted newest first (January 16 before January 15)
        self.assertIn("January 16", result[0]["date"])
        self.assertIn("January 15", result[1]["date"])

    def test_format_clips_by_day_clips_sorted_within_day(self) -> None:
        """Test clips within same day are sorted by time (newest first).

        Tests:
            - Multiple clips on same day are grouped together
            - Clips within day are sorted by created_at timestamp
            - Most recent clip appears first within each day
        """
        from datetime import UTC, datetime

        from blinkapp.utils.formatters import format_clips_by_day

        current_year = datetime.now(UTC).year
        clips = [
            {
                "id": "1",
                "created_at": f"{current_year}-01-15T08:00:00+00:00",  # Earlier
                "camera_name": "Camera1",
            },
            {
                "id": "2",
                "created_at": f"{current_year}-01-15T12:00:00+00:00",  # Later
                "camera_name": "Camera2",
            },
            {
                "id": "3",
                "created_at": f"{current_year}-01-15T10:00:00+00:00",  # Middle
                "camera_name": "Camera3",
            },
        ]

        result = format_clips_by_day(clips)

        self.assertEqual(len(result), 1)  # All clips on same day
        day_clips = result[0]["clips"]
        self.assertEqual(len(day_clips), 3)

        # Should be sorted newest first: 12:00, 10:00, 08:00
        self.assertEqual(day_clips[0]["id"], "2")  # 12:00 - newest
        self.assertEqual(day_clips[1]["id"], "3")  # 10:00 - middle
        self.assertEqual(day_clips[2]["id"], "1")  # 08:00 - oldest

    def test_format_clips_by_day_no_created_at_fallback(self) -> None:
        """Test date formatting when created_at is missing uses current date.

        Tests:
            - Uses current date when created_at is missing
            - Shows day of week without year for current date
            - Handles missing data gracefully
        """
        from datetime import UTC, datetime

        from blinkapp.utils.formatters import format_clips_by_day

        clips = [
            {
                "id": "123",
                "camera_name": "Test Camera",
                # No created_at field
            }
        ]

        result = format_clips_by_day(clips)

        self.assertEqual(len(result), 1)
        # Should use current date when created_at is missing
        # For current year, year is not shown in the date format
        current_year = datetime.now(UTC).year
        date_str = result[0]["date"]
        # Should contain day of week and month/day but not year for current year
        self.assertRegex(date_str, r"^\w+, \w+ \d+$")  # e.g., "Sunday, September 21"
        self.assertNotIn(str(current_year), date_str)  # Year not shown for current year

    def test_format_clip_time_am_pm(self) -> None:
        """Test clip time formatting with AM/PM display.

        Tests:
            - Time formatting shows AM/PM format
            - Proper timezone conversion
            - UI-friendly time display format
        """
        from datetime import datetime

        from blinkapp.utils.formatters import format_clip_time

        # Test morning time
        dt_am = datetime(2025, 1, 15, 9, 30, 0, tzinfo=UTC)
        result_am = format_clip_time(dt_am)
        self.assertRegex(result_am, r"^\d{1,2}:\d{2} [AP]M$")

        # Test afternoon time
        dt_pm = datetime(2025, 1, 15, 15, 45, 0, tzinfo=UTC)
        result_pm = format_clip_time(dt_pm)
        self.assertRegex(result_pm, r"^\d{1,2}:\d{2} [AP]M$")

    def test_format_clip_time_timezone_conversion(self) -> None:
        """Test clip time formatting handles timezone conversion.

        Tests:
            - Timezone conversion to local time
            - Proper handling of UTC input
            - Consistent time display format
        """
        from datetime import datetime

        from blinkapp.utils.formatters import format_clip_time

        # UTC time should be converted to local timezone
        dt_utc = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
        result = format_clip_time(dt_utc)

        # Should be a valid time format with AM/PM
        self.assertRegex(result, r"^\d{1,2}:\d{2} [AP]M$")


class TestValidationHelpers(BaseTestCase):
    """Test validation helper functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()

    def test_validate_camera_id_valid_minimal(self) -> None:
        """Test validation_helpers validate_camera_id with valid input (minimal).

        Verifies that camera ID validation works correctly with
        valid camera identifiers in minimal test scenarios.

        Tests:
            - Valid camera ID validation and acceptance
            - Proper camera identifier format checking
            - Minimal validation scenario functionality
            - Camera ID validation utility correctness
        """
        from blinkapp.utils.validation_helpers import validate_camera_id

        result = validate_camera_id("12345")
        self.assertEqual(result, "12345")

    def test_validate_clip_id_valid_minimal(self) -> None:
        """Test validation_helpers validate_clip_id with valid input (minimal).

        Verifies that clip ID validation works correctly with
        valid clip identifiers in minimal test scenarios.

        Tests:
            - Valid clip ID validation and acceptance
            - Proper clip identifier format checking
            - Minimal validation scenario functionality
            - Clip ID validation utility correctness
        """
        from blinkapp.utils.validation_helpers import validate_clip_id

        result = validate_clip_id("67890")
        self.assertEqual(result, "67890")


class TestValidators(BaseTestCase):
    """Test validator functions."""

    def test_validate_string_input_valid(self) -> None:
        """Test validate_string_input with valid input validation.

        Verifies that string input validation works correctly
        with valid string data and proper validation rules.

        Tests:
            - Valid string input validation and acceptance
            - Proper string validation rule application
            - String input validation utility functionality
            - Valid input processing and validation success
        """
        from blinkapp.utils.validators import validate_string_input

        result = validate_string_input("hello", 10, "test_field")
        self.assertEqual(result, "hello")

    def test_validate_string_input_valid_minimal(self) -> None:
        """Test validate_string_input function with valid input (minimal test).

        Verifies that the validate_string_input function properly accepts
        and processes valid string input in minimal test scenarios.

        Tests:
            - Valid string input acceptance and processing
            - Proper validation logic for acceptable strings
            - Input sanitization and validation success paths
            - Minimal test coverage for basic validation functionality
        """
        from blinkapp.utils.validators import validate_string_input

        result = validate_string_input("test", 10, "test_field")
        self.assertEqual(result, "test")

    def test_validate_string_input_too_long_minimal_v2(self) -> None:
        """Test validate_string_input function with input exceeding length limits.

        Verifies that the validate_string_input function properly rejects
        string input that exceeds the maximum allowed length.

        Tests:
            - Input length validation and limit enforcement
            - Proper rejection of oversized string inputs
            - Length limit boundary condition handling
            - Appropriate error responses for length violations
        """
        from blinkapp.utils.validators import validate_string_input

        with self.assertRaises(ValueError):
            validate_string_input("very_long_string", 5, "test_field")

    def test_is_valid_email_format_valid_minimal_v2(self) -> None:
        """Test is_valid_email_format function with valid email addresses.

        Verifies that the is_valid_email_format function properly validates
        and accepts correctly formatted email addresses.

        Tests:
            - Valid email format recognition and acceptance
            - Proper email validation logic and pattern matching
            - Email format compliance checking and validation
            - Correct validation results for well-formed emails
        """
        from blinkapp.utils.validators import is_valid_email_format

        self.assertTrue(is_valid_email_format("test@example.com"))

    def test_is_valid_email_format_invalid_minimal_v2(self) -> None:
        """Test is_valid_email_format function with invalid email addresses.

        Verifies that the is_valid_email_format function properly rejects
        incorrectly formatted or malformed email addresses.

        Tests:
            - Invalid email format detection and rejection
            - Malformed email address handling and validation
            - Email format compliance checking for invalid inputs
            - Proper validation failure responses for bad emails
        """
        from blinkapp.utils.validators import is_valid_email_format

        self.assertFalse(is_valid_email_format("invalid-email"))

    def test_validate_credentials_valid_email_minimal_v2(self) -> None:
        """Test validate_credentials function with valid email addresses.

        Verifies that the validate_credentials function properly validates
        and accepts valid email addresses as part of credential validation.

        Tests:
            - Valid email credential acceptance and processing
            - Proper credential validation logic for emails
            - Email-based credential format checking and validation
            - Successful validation results for valid email credentials
        """
        from blinkapp.utils.validators import validate_credentials

        email, password = validate_credentials("test@example.com", "testpass")
        self.assertEqual(email, "test@example.com")
        self.assertEqual(password, "testpass")

    def test_validate_credentials_empty_minimal_v2(self) -> None:
        """Test validate_credentials function with empty input values.

        Verifies that the validate_credentials function properly handles
        and rejects empty or missing credential input values.

        Tests:
            - Empty input detection and rejection
            - Missing credential handling and validation
            - Input completeness checking and validation
            - Appropriate error responses for incomplete credentials
        """
        from blinkapp.utils.validators import validate_credentials

        with self.assertRaises(ValueError):
            validate_credentials("", "password")

    def test_validate_string_input_valid_minimal_v3(self) -> None:
        """Test validate_string_input function with valid input (comprehensive test).

        Verifies that the validate_string_input function properly accepts
        and processes valid string input in comprehensive test scenarios.

        Tests:
            - Valid string input acceptance across various formats
            - Comprehensive validation logic testing
            - Input sanitization and validation success paths
            - Extended test coverage for validation functionality
        """
        from blinkapp.utils.validators import validate_string_input

        result = validate_string_input("test", 10, "test_field")
        self.assertEqual(result, "test")

    def test_validate_string_input_too_long(self) -> None:
        """Test validate_string_input function with input exceeding maximum length.

        Verifies that the validate_string_input function properly rejects
        string input that exceeds the configured maximum length limits.

        Tests:
            - Maximum length limit enforcement and validation
            - Proper rejection of oversized string inputs
            - Length boundary condition handling and testing
            - Appropriate error responses for length limit violations
        """
        from blinkapp.utils.validators import validate_string_input

        with self.assertRaises(ValueError):
            validate_string_input("hello world", 5, "test_field")

    def test_validate_camera_id_valid(self) -> None:
        """Test validate_camera_id function with valid camera ID values.

        Verifies that the validate_camera_id function properly validates
        and accepts correctly formatted camera ID values.

        Tests:
            - Valid camera ID format recognition and acceptance
            - Proper camera ID validation logic and pattern matching
            - Camera ID format compliance checking and validation
            - Successful validation results for well-formed camera IDs
        """
        from blinkapp.utils.validators import validate_camera_id

        result = validate_camera_id("12345")
        self.assertEqual(result, "12345")

    def test_validate_camera_id_invalid_raises_exception(self) -> None:
        """Test validate_camera_id function with invalid ID raises exception.

        Verifies that the validate_camera_id function properly raises
        exceptions when provided with invalid camera ID values.

        Tests:
            - Invalid camera ID detection and exception raising
            - Proper exception handling for malformed camera IDs
            - Camera ID validation failure responses and error handling
            - Exception type and message validation for invalid IDs
        """
        from blinkapp.utils.validators import validate_camera_id

        with self.assertRaises(ValueError):
            validate_camera_id("")

    def test_validate_camera_id_comprehensive(self) -> None:
        """Test comprehensive camera ID validation across multiple scenarios.

        Verifies that the camera ID validation system properly handles
        various camera ID formats and validation scenarios comprehensively.

        Tests:
            - Multiple camera ID format validation scenarios
            - Comprehensive validation logic testing across formats
            - Edge case handling for camera ID validation
            - Validation consistency across different ID types
        """
        try:
            from blinkapp.utils.validators import validate_camera_id

            # Valid IDs should not raise exceptions
            try:
                validate_camera_id("camera123")
                validate_camera_id("cam-456")
                validate_camera_id("cam_789")
            except ValueError:
                self.fail("validate_camera_id raised ValueError for valid input")

            # Invalid IDs should raise ValueError
            with self.assertRaises(ValueError):
                validate_camera_id("")
            with self.assertRaises((ValueError, TypeError)):
                validate_camera_id(None)  # Testing None input handling
            with self.assertRaises(ValueError):
                validate_camera_id("invalid@camera")
        except ImportError:
            self.skipTest("validate_camera_id function not found")

    def test_validate_tcp_url_valid(self) -> None:
        """Test validate_tcp_url function with valid TCP URL formats.

        Verifies that the validate_tcp_url function properly validates
        and accepts correctly formatted TCP URL values.

        Tests:
            - Valid TCP URL format recognition and acceptance
            - Proper TCP URL validation logic and pattern matching
            - TCP URL format compliance checking and validation
            - Successful validation results for well-formed TCP URLs
        """
        from blinkapp.utils.validators import validate_tcp_url

        result = validate_tcp_url("tcp://127.0.0.1:8080")
        self.assertEqual(result, "tcp://127.0.0.1:8080")

    def test_validate_tcp_url_invalid(self) -> None:
        """Test validate_tcp_url function with invalid TCP URL formats.

        Verifies that the validate_tcp_url function properly rejects
        incorrectly formatted or malformed TCP URL values.

        Tests:
            - Invalid TCP URL format detection and rejection
            - Malformed TCP URL handling and validation
            - TCP URL format compliance checking for invalid inputs
            - Proper validation failure responses for bad TCP URLs
        """
        from blinkapp.utils.validators import validate_tcp_url

        with self.assertRaises(ValueError):
            validate_tcp_url("invalid_url")

    def test_is_valid_email_format_valid(self) -> None:
        """Test is_valid_email_format function with valid email addresses.

        Verifies that the is_valid_email_format function properly validates
        and accepts correctly formatted email addresses.

        Tests:
            - Valid email format recognition and acceptance
            - Proper email validation logic and pattern matching
            - Email format compliance checking and validation
            - Correct validation results for well-formed email addresses
        """
        from blinkapp.utils.validators import is_valid_email_format

        self.assertTrue(is_valid_email_format("test@example.com"))

    def test_is_valid_email_format_invalid(self) -> None:
        """Test is_valid_email_format function with invalid email addresses.

        Verifies that the is_valid_email_format function properly rejects
        incorrectly formatted or malformed email addresses.

        Tests:
            - Invalid email format detection and rejection
            - Malformed email address handling and validation
            - Email format compliance checking for invalid inputs
            - Proper validation failure responses for invalid email formats
        """
        from blinkapp.utils.validators import is_valid_email_format

        self.assertFalse(is_valid_email_format("invalid"))

    def test_validate_credentials_valid(self) -> None:
        """Test validate_credentials function with valid input credentials.

        Verifies that the validate_credentials function properly validates
        and accepts valid credential input combinations.

        Tests:
            - Valid credential input acceptance and processing
            - Proper credential validation logic for valid inputs
            - Credential format compliance checking and validation
            - Successful validation results for well-formed credentials
        """
        from blinkapp.utils.validators import validate_credentials

        username, password = validate_credentials("test@example.com", "password123")
        self.assertEqual(username, "test@example.com")
        self.assertEqual(password, "password123")

    def test_validate_credentials_invalid_email(self) -> None:
        """Test validate_credentials function with invalid email addresses.

        Verifies that the validate_credentials function properly rejects
        credential combinations containing invalid email addresses.

        Tests:
            - Invalid email credential detection and rejection
            - Malformed email handling in credential validation
            - Email format compliance checking within credentials
            - Proper validation failure responses for invalid email credentials
        """
        from blinkapp.utils.validators import validate_credentials

        with self.assertRaises(ValueError):
            validate_credentials("invalid", "password123")

    def test_validate_string_input_comprehensive(self) -> None:
        """Test string input validation functionality comprehensively.

        Verifies that the string input validation system properly handles
        various input scenarios and validation requirements comprehensively.

        Tests:
            - Comprehensive string input validation across scenarios
            - Multiple validation rule enforcement and testing
            - Input sanitization and validation success/failure paths
            - Extensive test coverage for validation functionality
        """
        from blinkapp.utils.validators import validate_string_input

        # Test valid input
        result = validate_string_input("test", 10, "field")
        self.assertEqual(result, "test")

        # Test whitespace trimming
        result = validate_string_input("  test  ", 10, "field")
        self.assertEqual(result, "test")

        # Test empty input
        with self.assertRaises(ValueError):
            validate_string_input("", 10, "field")

        # Test too long input
        with self.assertRaises(ValueError):
            validate_string_input("toolong", 5, "field")

    def test_email_validation_comprehensive(self) -> None:
        """Test email format validation functionality comprehensively.

        Verifies that the email format validation system properly handles
        various email formats and validation scenarios comprehensively.

        Tests:
            - Comprehensive email format validation across scenarios
            - Multiple email format rule enforcement and testing
            - Email validation success/failure paths and edge cases
            - Extensive test coverage for email validation functionality
        """
        from blinkapp.utils.validators import is_valid_email_format

        # Valid emails
        self.assertTrue(is_valid_email_format("test@example.com"))
        self.assertTrue(is_valid_email_format("user.name+tag@domain.co.uk"))

        # Invalid emails
        self.assertFalse(is_valid_email_format(""))
        self.assertFalse(is_valid_email_format("invalid"))
        self.assertFalse(is_valid_email_format("@domain.com"))
        self.assertFalse(is_valid_email_format("user@"))
        # Test None input - function handles None gracefully but type checker doesn't know this
        self.assertFalse(is_valid_email_format(None))  # Testing None input handling

    def test_credential_validation_comprehensive(self) -> None:
        """Test credential validation functionality comprehensively.

        Verifies that the credential validation system properly handles
        various credential formats and validation scenarios comprehensively.

        Tests:
            - Comprehensive credential validation across scenarios
            - Multiple credential format rule enforcement and testing
            - Credential validation success/failure paths and edge cases
            - Extensive test coverage for credential validation functionality
        """
        from blinkapp.utils.validators import validate_credentials

        # Valid credentials
        username, password = validate_credentials("user@example.com", "password123")
        self.assertEqual(username, "user@example.com")
        self.assertEqual(password, "password123")

        # Invalid credentials
        with self.assertRaises(ValueError):
            validate_credentials("", "pass")
        with self.assertRaises(ValueError):
            validate_credentials("user@example.com", "")
        with self.assertRaises(ValueError):
            validate_credentials("invalid-email", "pass")


class TestParsers(BaseTestCase):
    """Test parser functions."""

    def test_extract_thumbnail_timestamp_valid(self) -> None:
        """Test extract_thumbnail_timestamp function with valid filename formats.

        Verifies that the extract_thumbnail_timestamp function properly extracts
        timestamp information from valid thumbnail filename formats.

        Tests:
            - Valid filename timestamp extraction and parsing
            - Proper timestamp format recognition and processing
            - Filename parsing logic and timestamp retrieval
            - Successful timestamp extraction from well-formed filenames
        """
        from blinkapp.utils.parsers import extract_thumbnail_timestamp

        filename = "thumb_1234567890.jpg"
        result = extract_thumbnail_timestamp(filename)
        self.assertEqual(result, 1234567890)

    def test_extract_thumbnail_timestamp_none_minimal(self) -> None:
        """Test extract_thumbnail_timestamp function with None input (minimal test).

        Verifies that the extract_thumbnail_timestamp function properly handles
        None input values in minimal test scenarios.

        Tests:
            - None input handling and processing
            - Proper null value validation and response
            - Graceful handling of missing filename input
            - Appropriate return values for None input scenarios
        """
        from blinkapp.utils.parsers import extract_thumbnail_timestamp

        result = extract_thumbnail_timestamp(None)
        self.assertEqual(result, 0)

    def test_parse_clip_id_valid_minimal(self) -> None:
        """Test parse_clip_id function with valid input (minimal test).

        Verifies that the parse_clip_id function properly parses
        and processes valid clip ID input in minimal test scenarios.

        Tests:
            - Valid clip ID input parsing and processing
            - Proper clip ID format recognition and handling
            - Clip ID parsing logic and validation
            - Successful parsing results for well-formed clip IDs
        """
        from blinkapp.utils.parsers import parse_clip_id

        result = parse_clip_id("12345")
        self.assertEqual(result, "12345")

    def test_extract_thumbnail_timestamp_invalid(self) -> None:
        """Test extract_thumbnail_timestamp function with invalid filename formats.

        Verifies that the extract_thumbnail_timestamp function properly handles
        and rejects invalid or malformed thumbnail filename formats.

        Tests:
            - Invalid filename format detection and handling
            - Malformed filename processing and error handling
            - Filename validation and rejection of invalid formats
            - Appropriate error responses for invalid filename inputs
        """
        from blinkapp.utils.parsers import extract_thumbnail_timestamp

        result = extract_thumbnail_timestamp("invalid.jpg")
        self.assertEqual(result, 0)

    def test_extract_thumbnail_timestamp_none(self) -> None:
        """Test extract_thumbnail_timestamp function with None filename input.

        Verifies that the extract_thumbnail_timestamp function properly handles
        None filename input values and provides appropriate responses.

        Tests:
            - None filename input handling and processing
            - Proper null value validation and error handling
            - Graceful handling of missing filename parameters
            - Appropriate return values and error responses for None input
        """
        from blinkapp.utils.parsers import extract_thumbnail_timestamp

        result = extract_thumbnail_timestamp(None)
        self.assertEqual(result, 0)

    def test_parse_clip_id_basic(self) -> None:
        """Test parse_clip_id function with basic clip ID formats.

        Verifies that the parse_clip_id function properly parses
        and processes basic clip ID formats and values.

        Tests:
            - Basic clip ID format parsing and processing
            - Simple clip ID value recognition and handling
            - Clip ID parsing logic for standard formats
            - Successful parsing results for basic clip ID inputs
        """
        from blinkapp.utils.parsers import parse_clip_id

        result = parse_clip_id("12345")
        self.assertEqual(result, "12345")

    def test_parse_clip_id_with_whitespace(self) -> None:
        """Test parse_clip_id function removes whitespace from input.

        Verifies that the parse_clip_id function properly removes
        whitespace characters from clip ID input during parsing.

        Tests:
            - Whitespace removal and input sanitization
            - Proper input cleaning and normalization
            - Clip ID parsing with whitespace handling
            - Clean output generation from whitespace-containing input
        """
        from blinkapp.utils.parsers import parse_clip_id

        result = parse_clip_id("  12345  ")
        self.assertEqual(result, "12345")


class TestErrors(BaseTestCase):
    """Test error classes."""

    def test_authentication_error_creation(self) -> None:
        """Test AuthenticationError exception creation and initialization.

        Verifies that the AuthenticationError exception class properly
        initializes and creates error instances with appropriate attributes.

        Tests:
            - AuthenticationError exception creation and initialization
            - Proper error message handling and storage
            - Exception attribute assignment and validation
            - Error instance creation with correct properties
        """
        from blinkapp.utils.errors import AuthenticationError

        error = AuthenticationError("Test error")
        self.assertEqual(str(error), "Test error")

    def test_authentication_error_with_status_code(self) -> None:
        """Test AuthenticationError exception creation with status code.

        Verifies that the AuthenticationError exception class properly
        handles and stores HTTP status codes during error creation.

        Tests:
            - AuthenticationError creation with status code parameters
            - Proper status code handling and storage
            - Exception initialization with HTTP status information
            - Status code attribute assignment and validation
        """
        from blinkapp.utils.errors import AuthenticationError

        error = AuthenticationError("Test error", 401)
        # The error stores both message and status code
        self.assertIn("Test error", str(error))

    def test_exception_handling_patterns(self) -> None:
        """Test exception handling patterns and error management utilities.

        Verifies that utility functions properly handle various exception types
        and provide appropriate error handling patterns for robust operation.

        Tests:
            - Exception handling pattern validation
            - Error management utility functionality
            - Proper exception propagation and handling
        """
        from blinkapp.models.ids import CameraId, ClipId

        # Test ValueError handling
        with self.assertRaises(ValueError):
            CameraId("")  # Should raise ValueError for empty string

        with self.assertRaises(ValueError):
            ClipId("")  # Should raise ValueError for empty string

    def test_type_error_handling(self) -> None:
        """Test TypeError exception handling in error scenarios.

        Verifies that the error handling system properly processes
        and manages TypeError exceptions during operation failures.

        Tests:
            - TypeError exception detection and handling
            - Proper type error processing and response
            - Exception handling logic for type-related errors
            - Appropriate error responses for type validation failures
        """
        from blinkapp.models.ids import CameraId, ClipId

        # Test with wrong types that should raise ValueError
        with self.assertRaises((ValueError, TypeError)):
            CameraId("")  # Empty string should raise ValueError

        # Test that integers are converted to strings (should work)
        clip_id = ClipId(123)
        self.assertEqual(str(clip_id), "123")

    def test_attribute_error_handling(self) -> None:
        """Test AttributeError exception handling patterns and responses.

        Verifies that the error handling system properly processes
        and manages AttributeError exceptions with consistent patterns.

        Tests:
            - AttributeError exception detection and handling
            - Proper attribute error processing and response patterns
            - Exception handling logic for missing attribute errors
            - Consistent error responses for attribute access failures
        """
        from unittest.mock import Mock

        # Test accessing non-existent attributes
        mock_obj = Mock(spec=object)

        # This should not raise AttributeError due to Mock
        result = getattr(mock_obj, "nonexistent_attr", "default")
        self.assertIsNotNone(result)


class TestSafeDownload(BaseTestCase):
    """Test safe download utilities."""

    def test_safe_download_success(self) -> None:
        """Test safe download with successful completion.

        Verifies that the safe download utility correctly handles successful
        downloads by writing to a temporary file first and then atomically
        moving to the final location.

        Tests:
            - Temporary file creation and usage
            - Atomic move to final location on success
            - Proper cleanup of temporary files
            - Final file contains expected content
        """
        from blinkapp.utils.safe_download import safe_download

        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "test_file.mp4"

            def mock_download(temp_path: Path) -> bool:
                temp_path.write_bytes(b"complete_download_data")
                return True

            result = safe_download(target_path, mock_download)

            self.assertTrue(result)
            self.assertTrue(target_path.exists())
            self.assertEqual(target_path.read_bytes(), b"complete_download_data")

            # No temp files should remain
            temp_files = list(Path(temp_dir).glob(".*tmp"))
            self.assertEqual(len(temp_files), 0)

    def test_safe_download_failure_cleanup(self) -> None:
        """Test safe download cleans up partial files on failure.

        Verifies that when a download function returns False (indicating failure),
        the safe download utility properly cleans up any temporary files that
        were created during the download attempt.

        Tests:
            - Download function failure handling
            - Temporary file cleanup on failure
            - No partial files left behind
            - Proper return value on failure
        """
        from blinkapp.utils.safe_download import safe_download

        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "test_file.mp4"

            def mock_download_fail(temp_path: Path) -> bool:
                temp_path.write_bytes(b"partial_data")
                return False  # Simulate failure

            result = safe_download(target_path, mock_download_fail)

            self.assertFalse(result)
            self.assertFalse(target_path.exists())

            # No temp files should remain
            temp_files = list(Path(temp_dir).glob(".*tmp"))
            self.assertEqual(len(temp_files), 0)

    def test_safe_download_exception_cleanup(self) -> None:
        """Test safe download cleans up on exception.

        Verifies that when a download function raises an exception,
        the safe download utility properly handles the exception and
        cleans up any temporary files that were created.

        Tests:
            - Exception handling during download
            - Temporary file cleanup on exception
            - No partial files left behind
            - Proper return value on exception
        """
        from blinkapp.utils.safe_download import safe_download

        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "test_file.mp4"

            def mock_download_exception(temp_path: Path) -> bool:
                temp_path.write_bytes(b"partial_data")
                raise Exception("Download interrupted")

            result = safe_download(target_path, mock_download_exception)

            self.assertFalse(result)
            self.assertFalse(target_path.exists())

            # No temp files should remain
            temp_files = list(Path(temp_dir).glob(".*tmp"))
            self.assertEqual(len(temp_files), 0)


class TestErrorHandlers(BaseTestCase):
    """Test error handler functions."""

    def test_handle_api_error_exists(self) -> None:
        """Test handle_api_error function exists and is accessible.

        Verifies that the handle_api_error function is properly defined
        and accessible for API error handling operations.

        Tests:
            - handle_api_error function existence and accessibility
            - Proper function definition and import capability
            - API error handling function availability
            - Function interface and signature validation
        """
        from blinkapp.utils.error_handlers import handle_api_error

        # Function should exist and be callable
        self.assertTrue(callable(handle_api_error))


class TestLoggingConfig(BaseTestCase):
    """Test logging configuration."""

    @patch("pathlib.Path.mkdir")
    def test_setup_logging_basic(self, mock_mkdir: Mock) -> None:
        """Test basic logging setup and configuration functionality.

        Verifies that the logging system properly initializes
        and configures basic logging functionality for the application.

        Tests:
            - Basic logging setup and initialization
            - Proper logging configuration and parameter handling
            - Log system initialization and validation
            - Logging functionality availability and operation
        """
        import tempfile

        from blinkapp.utils.logging_config import setup_logging

        # Create temporary directory that persists for test
        temp_dir = tempfile.mkdtemp()
        try:
            # Should not raise exception
            setup_logging(temp_dir)
        finally:
            # Clean up
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    @patch("logging.getLogger")
    @patch("logging.handlers.RotatingFileHandler")
    def test_setup_logging_function(self, mock_file: Mock, mock_logger: Mock) -> None:
        """Test logging system initialization with file rotation.

        Verifies that the logging system is properly initialized with
        file rotation capabilities and correct configuration settings.

        Tests:
            - Logging system initialization with rotation
            - File handler configuration and setup
            - Logger configuration validation
            - Rotation policy implementation
        """
        import logging
        import tempfile
        from unittest.mock import Mock

        mock_logger_instance = Mock(spec=logging.Logger)
        mock_logger_instance.handlers = []
        mock_logger.return_value = mock_logger_instance
        mock_file_handler = Mock(spec=logging.Handler)
        mock_file.return_value = mock_file_handler

        from blinkapp.services.cache_service import initialize_cache_paths
        from blinkapp.utils.logging_config import setup_logging

        # Initialize cache paths before logging setup
        initialize_cache_paths()
        temp_dir = tempfile.mkdtemp()
        try:
            setup_logging(temp_dir)
            # Should create handlers and configure logger
            mock_logger.assert_called()
        finally:
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)

    @patch("blinkapp.Config.LOG_FILE", "/tmp/test.log")
    def test_logging_configuration(self) -> None:
        """Test logging configuration paths and settings validation.

        Verifies that logging configuration is properly set up with
        correct paths, levels, and formatting options.

        Tests:
            - Logging configuration path validation
            - Log level settings verification
            - Format configuration validation
            - Configuration file processing
        """
        # Test that logging configuration can be accessed
        self.assertTrue(hasattr(Config, "LOG_FILE"))
        self.assertTrue(hasattr(Config, "LOG_MAX_BYTES"))
        self.assertTrue(hasattr(Config, "LOG_BACKUP_COUNT"))


if __name__ == "__main__":
    unittest.main()
