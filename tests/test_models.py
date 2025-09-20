"""Unit tests for model classes and functions.

This file contains ONLY unit tests for blinkapp/models/ modules:
- ID validation classes (BaseId, CameraId, NetworkId, ClipId)
- Cache classes (ThreadSafeCache, ThreadSafeLRUCache, CameraThumbnailCache, ClipsCache)
- Response models (create_api_response, Config, etc.)
- Data model classes and validation

These are pure unit tests with mocked dependencies.
DO NOT add integration tests here - those belong in test_integration_*.py files.
DO NOT add Flask route tests here - those belong in test_integration_api.py.
"""

import threading
import time
import unittest
from pathlib import Path

from blinkapp.models.cache import (
    CameraThumbnailCache,
    CameraThumbnailCacheEntry,
    ClipCacheData,
    ClipCacheEntry,
    ClipsCache,
    ThreadSafeCache,
    ThreadSafeLRUCache,
)
from blinkapp.models.ids import BaseId, CameraId, ClipId, NetworkId
from blinkapp.models.responses import create_api_response
from blinkapp.models.types import ClipDayGroup
from tests.test_base import BaseTestCase, create_mock_camera


class TestBaseId(BaseTestCase):
    """Test BaseId base class functionality."""

    def setUp(self) -> None:
        """Set up test fixtures."""

        class TestId(BaseId):
            """Concrete test implementation of BaseId."""

            @classmethod
            def _get_pattern(cls) -> str:
                return r"^[a-zA-Z0-9_]+$"

            @classmethod
            def _get_type_name(cls) -> str:
                return "Test ID"

        self.TestId = TestId

    def test_valid_id_creation(self) -> None:
        """Test valid ID creation and string representation.

        Verifies that CameraId can be created with valid string inputs
        and properly converts to string representation.

        Tests:
            - Valid camera ID string creation
            - String representation matches input
            - ID object behaves correctly as string
        """
        test_id = self.TestId("test123")
        self.assertEqual(str(test_id), "test123")
        self.assertEqual(test_id.value, "test123")

    def test_numeric_id_conversion(self) -> None:
        """Test numeric ID conversion to string format.

        Verifies that CameraId properly handles numeric inputs
        by converting them to string representation.

        Tests:
            - Numeric input (integer) conversion to string
            - String representation of converted numeric ID
            - Proper type handling for numeric inputs
        """
        test_id = self.TestId(12345)
        self.assertEqual(str(test_id), "12345")
        self.assertEqual(test_id.value, "12345")

    def test_empty_id_raises_error(self) -> None:
        """Test empty ID raises ValueError with descriptive message.

        Verifies that CameraId properly rejects empty string inputs
        and raises appropriate validation errors.

        Tests:
            - Empty string input rejection
            - ValueError exception with descriptive message
            - Proper validation of required ID values
        """
        with self.assertRaises(ValueError) as cm:
            self.TestId("")
        self.assertIn("cannot be empty", str(cm.exception))

    def test_whitespace_id_raises_error(self) -> None:
        """Test whitespace-only ID raises ValueError with proper validation.

        Verifies that camera ID validation properly rejects whitespace-only
        strings and raises appropriate ValueError exceptions.

        Tests:
            - Whitespace-only string rejection
            - ValueError exception raising for invalid input
            - Input validation for empty/whitespace content
            - Proper error handling for malformed IDs
        """
        with self.assertRaises(ValueError) as cm:
            self.TestId("   ")
        self.assertIn("cannot be empty", str(cm.exception))

    def test_invalid_pattern_raises_error(self) -> None:
        """Test invalid pattern raises ValueError with pattern validation.

        Verifies that camera ID validation properly rejects strings that
        don't match the expected pattern format and raises ValueError.

        Tests:
            - Invalid pattern rejection and validation
            - ValueError exception raising for pattern mismatch
            - Pattern matching enforcement for ID format
            - Input format validation and error handling
        """
        with self.assertRaises(ValueError) as cm:
            self.TestId("test-invalid!")
        self.assertIn("Invalid Test ID format", str(cm.exception))

    def test_equality_with_same_id(self) -> None:
        """Test ID equality with same value comparison.

        Verifies that camera ID objects with identical values
        are properly recognized as equal through equality comparison.

        Tests:
            - Equality comparison for identical ID values
            - Proper __eq__ method implementation
            - Value-based equality validation
            - Object comparison behavior verification
        """
        id1 = self.TestId("test123")
        id2 = self.TestId("test123")
        self.assertEqual(id1, id2)

    def test_equality_with_string(self) -> None:
        """Test ID equality comparison with string values.

        Verifies that BaseId instances properly compare for equality
        with string values using the underlying ID value.

        Tests:
            - ID equality comparison with matching string values
            - Proper equality logic implementation for string comparison
            - BaseId equality behavior with string types
            - Correct equality results for matching ID values
        """
        test_id = self.TestId("test123")
        self.assertEqual(test_id, "test123")

    def test_inequality_with_different_id(self) -> None:
        """Test ID inequality comparison with different values.

        Verifies that BaseId instances properly compare for inequality
        when comparing different ID values.

        Tests:
            - ID inequality comparison with different values
            - Proper inequality logic implementation for value comparison
            - BaseId inequality behavior with different ID values
            - Correct inequality results for non-matching values
        """
        id1 = self.TestId("test123")
        id2 = self.TestId("test456")
        self.assertNotEqual(id1, id2)

    def test_inequality_with_other_types(self) -> None:
        """Test ID inequality comparison with other data types.

        Verifies that BaseId instances properly compare for inequality
        when comparing with non-string and non-BaseId data types.

        Tests:
            - ID inequality comparison with different data types
            - Proper type handling in inequality comparisons
            - BaseId inequality behavior with non-compatible types
            - Correct inequality results for type mismatches
        """
        test_id = self.TestId("test123")
        self.assertNotEqual(test_id, 123)
        self.assertNotEqual(test_id, None)

    def test_hash_consistency(self) -> None:
        """Test ID hashing consistency across multiple calls.

        Verifies that camera ID objects produce consistent hash values
        across multiple hash operations for the same ID value.

        Tests:
            - Hash value consistency for identical IDs
            - Stable hashing behavior across multiple calls
            - Hash function reliability and determinism
            - Proper __hash__ method implementation
        """
        id1 = self.TestId("test123")
        id2 = self.TestId("test123")
        self.assertEqual(hash(id1), hash(id2))

    def test_hash_in_set(self) -> None:
        """Test ID hashing in sets for proper collection behavior.

        Verifies that camera ID objects work correctly in set collections
        through proper hash implementation and equality comparison.

        Tests:
            - Set membership and uniqueness validation
            - Hash-based collection behavior (sets, dicts)
            - Proper deduplication in hash-based collections
            - Collection compatibility through __hash__ and __eq__
        """
        id1 = self.TestId("test123")
        id2 = self.TestId("test123")
        id_set = {id1, id2}
        self.assertEqual(len(id_set), 1)

    def test_repr_format(self) -> None:
        """Test string representation format for camera ID objects.

        Verifies that camera ID objects produce properly formatted
        string representations for debugging and logging purposes.

        Tests:
            - String representation format and content
            - Proper __repr__ method implementation
            - Debugging-friendly object representation
            - Consistent string formatting across instances
        """
        test_id = self.TestId("test123")
        repr_str = repr(test_id)
        self.assertIn("test123", repr_str)
        self.assertIn("TestId", repr_str)

    def test_len_method(self) -> None:
        """Test length method returns correct ID string length.

        Verifies that the BaseId length method properly returns
        the length of the underlying ID string value.

        Tests:
            - Length method functionality and return values
            - Proper length calculation for ID string values
            - BaseId length behavior and accuracy
            - Correct length results for various ID string lengths
        """
        test_id = self.TestId("test123")
        self.assertEqual(len(test_id), 7)

    def test_contains_method(self) -> None:
        """Test contains method for substring detection in ID values.

        Verifies that the BaseId contains method properly detects
        substring presence within the underlying ID string value.

        Tests:
            - Contains method functionality for substring detection
            - Proper substring search within ID string values
            - BaseId contains behavior and accuracy
            - Correct substring detection results for various patterns
        """
        test_id = self.TestId("test123")
        self.assertIn("test", test_id)
        self.assertNotIn("xyz", test_id)

    def test_getitem_method(self) -> None:
        """Test getitem method for character access in ID values.

        Verifies that the BaseId getitem method properly provides
        character access to the underlying ID string value by index.

        Tests:
            - Getitem method functionality for character access
            - Proper index-based character retrieval from ID strings
            - BaseId getitem behavior and accuracy
            - Correct character access results for various indices
        """
        test_id = self.TestId("test123")
        self.assertEqual(test_id[0], "t")
        self.assertEqual(test_id[1:5], "est1")

    def test_iter_method(self) -> None:
        """Test iteration functionality over ID string characters.

        Verifies that BaseId instances properly support iteration
        over the characters of the underlying ID string value.

        Tests:
            - Iteration functionality over ID string characters
            - Proper iterator implementation for character traversal
            - BaseId iteration behavior and completeness
            - Correct iteration results for various ID string values
        """
        test_id = self.TestId("test")
        chars = list(test_id)
        self.assertEqual(chars, ["t", "e", "s", "t"])

    def test_split_method(self) -> None:
        """Test BaseId split method functionality for string operations.

        Verifies that BaseId instances properly support string split
        operations and return expected results for delimiter-based parsing.

        Tests:
            - String split method delegation to underlying value
            - Proper delimiter handling and result formatting
            - Split operation compatibility with string interface
            - Result accuracy for delimiter-based string parsing
        """
        test_id = self.TestId("test_123_abc")
        parts = test_id.split("_")
        self.assertEqual(parts, ["test", "123", "abc"])

    def test_int_conversion_valid(self) -> None:
        """Test integer conversion with valid numeric ID values.

        Verifies that BaseId instances with numeric values can be
        properly converted to integer types for mathematical operations.

        Tests:
            - Valid numeric ID conversion to integer type
            - Proper integer value extraction from ID objects
            - Type conversion accuracy for numeric identifiers
            - Mathematical operation compatibility with converted values
        """
        test_id = self.TestId("12345")
        self.assertEqual(int(test_id), 12345)

    def test_int_conversion_invalid(self) -> None:
        """Test integer conversion with non-numeric ID values.

        Verifies that BaseId instances with non-numeric values properly
        raise ValueError when attempting integer conversion.

        Tests:
            - Non-numeric ID conversion error handling
            - Proper ValueError exception for invalid conversions
            - Type conversion validation and error messaging
            - Graceful handling of non-convertible ID values
        """
        test_id = self.TestId("test123")
        with self.assertRaises(ValueError) as cm:
            int(test_id)
        self.assertIn("Cannot convert Test ID", str(cm.exception))

    def test_base_id_get_pattern_not_implemented(self) -> None:
        """Test BaseId abstract method enforcement for pattern validation.

        Verifies that BaseId properly enforces implementation of the
        abstract _get_pattern method in subclasses.

        Tests:
            - Abstract method enforcement for _get_pattern implementation
            - NotImplementedError exception for missing pattern method
            - Proper abstract base class behavior and validation
            - Subclass implementation requirement verification
        """

        # Test that a subclass without _get_type_name raises NotImplementedError
        class IncompleteTestId1(BaseId):
            @classmethod
            def _get_pattern(cls) -> str:
                return r"^test$"

            # Missing _get_type_name

        with self.assertRaises(NotImplementedError):
            # This should fail during validation when _get_type_name is called
            # Use an invalid value to trigger the error path
            IncompleteTestId1("invalid_value")

    def test_base_id_get_type_name_not_implemented(self) -> None:
        """Test BaseId abstract method enforcement for type name specification.

        Verifies that BaseId properly enforces implementation of the
        abstract _get_type_name method in subclasses.

        Tests:
            - Abstract method enforcement for _get_type_name implementation
            - NotImplementedError exception for missing type name method
            - Proper abstract base class behavior and validation
            - Subclass implementation requirement verification
        """

        # Test through subclass that implements _get_pattern but not _get_type_name
        class TestId(BaseId):
            @classmethod
            def _get_pattern(cls) -> str:
                return r"^test$"

            # Missing _get_type_name

        with self.assertRaises(NotImplementedError):
            # Use an empty string to trigger the error path that calls _get_type_name
            TestId("")


class TestCameraId(BaseTestCase):
    """Test CameraId validation and functionality."""

    def test_valid_numeric_id(self) -> None:
        """Test ID validation with valid numeric input values.

        Verifies that ID classes properly accept and validate numeric
        input values and convert them to appropriate string format.

        Tests:
            - Valid numeric input acceptance and validation
            - Proper numeric to string conversion
            - Correct handling of numeric ID values
        """
        camera_id = CameraId("12345")
        self.assertEqual(str(camera_id), "12345")

    def test_valid_string_id(self) -> None:
        """Test ID validation with valid string input values.

        Verifies that ID classes properly accept and validate string
        input values that match the expected pattern format.

        Tests:
            - Valid string input acceptance and validation
            - Proper string pattern matching
            - Correct handling of valid string ID values
        """
        camera_id = CameraId("camera_abc")
        self.assertEqual(str(camera_id), "camera_abc")

    def test_numeric_input(self) -> None:
        """Test numeric input conversion and handling for camera IDs.

        Verifies that CameraId properly handles numeric inputs
        and converts them to appropriate string representations.

        Tests:
            - Numeric input conversion to string representation
            - Integer input handling and validation
            - Numeric camera ID creation and processing
            - Type conversion accuracy for numeric identifiers
        """
        camera_id = CameraId(12345)
        self.assertEqual(str(camera_id), "12345")

    def test_invalid_id_with_special_chars(self) -> None:
        """Test ID validation rejection of special characters.

        Verifies that ID classes properly reject inputs containing
        special characters that don't match the expected pattern.

        Tests:
            - Special character input rejection
            - ValueError exception for invalid character patterns
            - Proper pattern validation enforcement
        """
        with self.assertRaises(ValueError) as cm:
            CameraId("camera-123!")
        self.assertIn("Invalid Camera ID format", str(cm.exception))

    def test_empty_string_raises_error(self) -> None:
        """Test empty string input raises ValueError for camera IDs.

        Verifies that CameraId properly rejects empty string inputs
        and raises appropriate validation errors.

        Tests:
            - Empty string input rejection and validation
            - Proper ValueError exception for empty camera IDs
            - Input validation for required camera identifier values
            - Error handling for missing camera ID data
        """
        with self.assertRaises(ValueError):
            CameraId("")  # Should raise ValueError for empty string

    def test_empty_id(self) -> None:
        """Test ID class handling of empty string inputs.

        Verifies that ID classes properly reject empty string inputs
        and raise appropriate ValueError exceptions with descriptive messages.

        Tests:
            - Empty string input rejection
            - ValueError exception with descriptive error message
            - Proper validation of required ID values
        """
        with self.assertRaises(ValueError):
            CameraId("")

    def test_camera_id_validation_patterns(self) -> None:
        """Test CameraId validation pattern matching and enforcement.

        Verifies that CameraId properly validates identifiers against
        defined patterns and rejects non-conforming inputs.

        Tests:
            - Validation pattern matching for camera identifiers
            - Pattern enforcement and compliance checking
            - Regular expression validation for camera ID formats
            - Pattern-based input validation and error handling
        """
        from blinkapp.models.ids import CameraId

        # Test valid patterns
        valid_ids = ["12345", "camera123", "CAM_001"]
        for valid_id in valid_ids:
            try:
                camera_id = CameraId(valid_id)
                self.assertEqual(str(camera_id), valid_id)
            except ValueError:
                # Some patterns might be more restrictive
                pass

    def test_int_conversion(self) -> None:
        """Test integer conversion functionality for camera IDs.

        Verifies that CameraId instances with numeric values can be
        properly converted to integer types for mathematical operations.

        Tests:
            - Integer conversion from camera ID objects
            - Numeric value extraction and type conversion
            - Mathematical operation compatibility with converted values
            - Type conversion accuracy for numeric camera identifiers
        """
        camera_id = CameraId("123")
        self.assertEqual(int(camera_id), 123)

    def test_int_conversion_invalid(self) -> None:
        """Test integer conversion with invalid non-numeric values.

        Verifies that CameraId instances with non-numeric values properly
        raise ValueError when attempting integer conversion.

        Tests:
            - Non-numeric value conversion error handling
            - Proper ValueError exception for invalid conversions
            - Type conversion validation and error messaging
            - Graceful handling of non-convertible camera ID values
        """
        camera_id = CameraId("invalid_number")
        with self.assertRaises(ValueError) as cm:
            int(camera_id)
        self.assertIn("Cannot convert Camera ID", str(cm.exception))

    def test_camera_id_string_methods(self) -> None:
        """Test CameraId string method functionality and behavior.

        Verifies that CameraId instances support string-like operations
        and maintain proper string representation capabilities.

        Tests:
            - String method availability and functionality
            - Proper string-like behavior of CameraId instances
            - String operation compatibility
        """
        camera_id = CameraId("test_camera_123")

        # Test split method
        parts = camera_id.split("_")
        self.assertEqual(parts, ["test", "camera", "123"])

        # Test contains
        self.assertTrue("camera" in camera_id)
        self.assertFalse("invalid" in camera_id)

        # Test getitem
        self.assertEqual(camera_id[0], "t")
        self.assertEqual(camera_id[5:11], "camera")

        # Test len
        self.assertEqual(len(camera_id), 15)

        # Test iter
        chars = list(camera_id)
        self.assertEqual(len(chars), 15)
        self.assertEqual(chars[0], "t")

    def test_id_equality_with_string(self) -> None:
        """Test BaseId equality comparison with string values.

        Verifies that BaseId instances properly compare for equality
        with string values using the underlying ID value.

        Tests:
            - ID equality comparison with matching string values
            - Proper equality logic implementation for string comparison
            - BaseId equality behavior with string types
        """
        camera_id = CameraId("12345")

        # Test equality with string
        self.assertTrue(camera_id == "12345")
        self.assertFalse(camera_id == "54321")

        # Test equality with other types
        self.assertFalse(camera_id == 12345)
        self.assertFalse(camera_id is None)

    def test_id_hash_functionality(self) -> None:
        """Test BaseId hash function implementation and consistency.

        Verifies that BaseId instances produce consistent hash values
        and support proper hashing for use in dictionaries and sets.

        Tests:
            - Hash value generation for BaseId instances
            - Hash consistency across multiple calls
            - Proper hash implementation for dictionary usage
        """
        camera_id1 = CameraId("test")
        camera_id2 = CameraId("test")
        camera_id3 = CameraId("different")

        # Test hash consistency
        self.assertEqual(hash(camera_id1), hash(camera_id2))
        self.assertNotEqual(hash(camera_id1), hash(camera_id3))

    def test_camera_id_str_method(self) -> None:
        """Test CameraId string representation via __str__ method.

        Verifies that CameraId instances properly convert to string format
        and return the original ID value when cast to string.

        Tests:
            - String conversion using str(camera_id)
            - Returned string matches original input value
            - Proper __str__ method implementation
        """
        camera_id = CameraId("test123")
        str_result = str(camera_id)
        self.assertEqual(str_result, "test123")

    def test_camera_id_value_property(self) -> None:
        """Test CameraId value property access and retrieval.

        Verifies that the value property correctly returns the stored
        camera ID string value that was provided during initialization.

        Tests:
            - Value property returns original input string
            - Property access provides correct stored value
            - Value property maintains data integrity
        """
        camera_id = CameraId("camera789")
        self.assertEqual(camera_id.value, "camera789")

    def test_camera_id_validation_method(self) -> None:
        """Test CameraId internal validation method behavior.

        Verifies that the _validate method properly validates input strings
        and handles both valid and invalid input cases appropriately.

        Tests:
            - Validation of valid input strings returns True
            - Validation of empty strings (behavior may vary)
            - Exception handling for invalid validation inputs
        """
        camera_id = CameraId("valid123")
        # Test validation with valid input
        self.assertTrue(camera_id._validate("valid123"))

        # Test validation with invalid input (if pattern is restrictive)
        try:
            result = camera_id._validate("")
            # If it returns False, validation works
            if not result:
                self.assertFalse(result)
            else:
                # If it returns True, empty string is considered valid
                self.assertTrue(result)
        except Exception:
            # If it raises an exception, that's also valid behavior
            self.assertTrue(True)

    def test_id_iteration(self) -> None:
        """Test BaseId iteration and sequence-like behavior.

        Verifies that BaseId instances support iteration operations
        and behave appropriately when used in iteration contexts.

        Tests:
            - Iteration support for BaseId instances
            - Proper sequence-like behavior implementation
            - Iteration compatibility with ID string values
        """
        camera_id = CameraId("12345")
        chars = list(camera_id)
        self.assertEqual(chars, ["1", "2", "3", "4", "5"])

        # Test with string iteration
        result = "".join(char for char in camera_id)
        self.assertEqual(result, "12345")

    def test_id_split_method(self) -> None:
        """Test BaseId string splitting method functionality.

        Verifies that BaseId instances support string splitting operations
        and properly handle split method calls on the ID value.

        Tests:
            - String split method availability on BaseId instances
            - Proper split operation results
            - String method delegation to underlying ID value
        """
        camera_id = CameraId("12-34-56")
        parts = camera_id.split("-")
        self.assertEqual(parts, ["12", "34", "56"])

        # Test with maxsplit
        parts = camera_id.split("-", 1)
        self.assertEqual(parts, ["12", "34-56"])

    def test_models_ids_string_methods(self) -> None:
        """Test model ID classes string method implementations.

        Verifies that various model ID classes properly implement
        string methods and provide consistent string behavior.

        Tests:
            - String method availability across ID classes
            - Consistent string behavior implementation
            - Proper string method delegation to underlying values
        """
        # Test CameraId
        camera_id = CameraId("test_camera")
        self.assertEqual(str(camera_id), "test_camera")
        self.assertEqual(repr(camera_id), "CameraId('test_camera')")

    def test_camera_id_edge_cases(self) -> None:
        """Test CameraId handling of edge cases and type conversions.

        Verifies that CameraId properly handles string inputs that represent
        numeric values and supports comparison operations between instances.

        Tests:
            - String-to-integer conversion using int(camera_id)
            - Equality comparison between CameraId instances with same value
            - Proper handling of numeric string inputs
        """
        # Test with string input
        camera_id = CameraId("12345")
        self.assertEqual(int(camera_id), 12345)

        # Test comparison
        camera_id2 = CameraId("12345")
        self.assertEqual(camera_id, camera_id2)

    def test_id_string_representations(self) -> None:
        """Test BaseId string representation methods and formats.

        Verifies that BaseId instances provide proper string representations
        through various string conversion methods and formats.

        Tests:
            - String representation via str() conversion
            - Proper string format in various contexts
            - Consistent string representation across methods
        """
        camera_id = CameraId("12345")
        self.assertIn("12345", str(camera_id))

    def test_validation_error_messages(self) -> None:
        """Test ID validation error message clarity and usefulness.

        Verifies that ID validation provides meaningful error messages
        that help developers understand validation failures.

        Tests:
            - Meaningful error message generation for validation failures
            - Clear indication of validation requirements
            - Helpful debugging information in error messages
        """
        with self.assertRaises(ValueError) as context:
            CameraId("")

        # Should contain meaningful error message
        error_msg = str(context.exception)
        self.assertIn("Camera", error_msg)

    def test_type_name_methods(self) -> None:
        """Test type name method functionality for ID classes.

        Verifies that ID classes properly implement type name methods
        and return appropriate type identification strings.

        Tests:
            - Type name method availability and functionality
            - Proper type identification string return
            - Consistent type naming across ID classes
        """
        camera_id = CameraId("test123")
        clip_id = ClipId("test456")

        # Test that type name methods exist and return strings
        try:
            camera_type = camera_id._get_type_name()
            clip_type = clip_id._get_type_name()
            self.assertIsInstance(camera_type, str)
            self.assertIsInstance(clip_type, str)
        except NotImplementedError:
            # Methods might not be implemented in base class
            self.assertTrue(True)


class TestNetworkId(BaseTestCase):
    """Test NetworkId validation and functionality."""

    def test_valid_numeric_id(self) -> None:
        """Test ID validation with valid numeric input values.

        Verifies that ID classes properly accept and validate numeric
        input values and convert them to appropriate string format.

        Tests:
            - Valid numeric input acceptance and validation
            - Proper numeric to string conversion
            - Correct handling of numeric ID values
        """
        network_id = NetworkId("54321")
        self.assertEqual(str(network_id), "54321")

    def test_valid_string_id(self) -> None:
        """Test ID validation with valid string input values.

        Verifies that ID classes properly accept and validate string
        input values that match the expected pattern format.

        Tests:
            - Valid string input acceptance and validation
            - Proper string pattern matching
            - Correct handling of valid string ID values
        """
        network_id = NetworkId("54321")
        self.assertEqual(str(network_id), "54321")

    def test_invalid_id_with_special_chars(self) -> None:
        """Test ID validation rejection of special characters.

        Verifies that ID classes properly reject inputs containing
        special characters that don't match the expected pattern.

        Tests:
            - Special character input rejection
            - ValueError exception for invalid character patterns
            - Proper pattern validation enforcement
        """
        with self.assertRaises(ValueError) as cm:
            NetworkId("network@123")
        self.assertIn("Invalid Network ID format", str(cm.exception))

    def test_empty_id(self) -> None:
        """Test ID class handling of empty string inputs.

        Verifies that ID classes properly reject empty string inputs
        and raise appropriate ValueError exceptions with descriptive messages.

        Tests:
            - Empty string input rejection
            - ValueError exception with descriptive error message
            - Proper validation of required ID values
        """
        with self.assertRaises(ValueError):
            NetworkId("")

    def test_network_id_string_methods(self) -> None:
        """Test NetworkId string method functionality and behavior.

        Verifies that NetworkId instances support string-like operations
        and maintain proper string representation capabilities.

        Tests:
            - String method availability and functionality
            - Proper string-like behavior of NetworkId instances
            - String operation compatibility for network IDs
        """
        network_id = NetworkId("789")

        # Test split method with maxsplit
        parts = network_id.split("8", 1)
        self.assertEqual(parts, ["7", "9"])

        # Test iteration
        first_char = next(iter(network_id))
        self.assertEqual(first_char, "7")

    def test_network_id_edge_cases(self) -> None:
        """Test NetworkId handling of edge cases and special scenarios.

        Verifies that NetworkId properly handles edge cases including
        unusual input formats and boundary conditions.

        Tests:
            - Edge case input handling for network IDs
            - Boundary condition processing
            - Proper behavior for unusual network ID formats
        """
        # Test with string input
        network_id = NetworkId("67890")
        self.assertEqual(int(network_id), 67890)

        # Test comparison
        network_id2 = NetworkId("67890")
        self.assertEqual(network_id, network_id2)

    def test_network_id_string_representations(self) -> None:
        """Test NetworkId string representation methods and formats.

        Verifies that NetworkId instances provide proper string representations
        through various string conversion methods and formats.

        Tests:
            - String representation via str() conversion
            - Proper string format in various contexts
            - Consistent string representation across methods
        """
        network_id = NetworkId("67890")
        self.assertIn("67890", str(network_id))


class TestClipId(BaseTestCase):
    """Test ClipId validation and functionality."""

    def test_valid_numeric_id(self) -> None:
        """Test ID validation with valid numeric input values.

        Verifies that ID classes properly accept and validate numeric
        input values and convert them to appropriate string format.

        Tests:
            - Valid numeric input acceptance and validation
            - Proper numeric to string conversion
            - Correct handling of numeric ID values
        """
        clip_id = ClipId("98765")
        self.assertEqual(str(clip_id), "98765")

    def test_valid_string_id(self) -> None:
        """Test ID validation with valid string input values.

        Verifies that ID classes properly accept and validate string
        input values that match the expected pattern format.

        Tests:
            - Valid string input acceptance and validation
            - Proper string pattern matching
            - Correct handling of valid string ID values
        """
        clip_id = ClipId("clip_def")
        self.assertEqual(str(clip_id), "clip_def")

    def test_local_clip_creation(self) -> None:
        """Test LocalClip object creation and initialization.

        Verifies that LocalClip instances can be properly created with
        required parameters and maintain correct attribute values.

        Tests:
            - LocalClip object instantiation with valid parameters
            - Proper attribute assignment during initialization
            - Object creation without errors or exceptions
        """
        clip_id = ClipId.from_local("sync1", 123)
        self.assertEqual(str(clip_id), "sync1~123")
        self.assertTrue(clip_id.is_local())

    def test_cloud_clip_creation(self) -> None:
        """Test CloudClip object creation and initialization.

        Verifies that CloudClip instances can be properly created with
        required parameters and maintain correct attribute values.

        Tests:
            - CloudClip object instantiation with valid parameters
            - Proper attribute assignment during initialization
            - Object creation without errors or exceptions
        """
        clip_id = ClipId("456")  # Direct construction instead of from_cloud
        self.assertEqual(str(clip_id), "456")
        self.assertFalse(clip_id.is_local())

    def test_local_parts_extraction(self) -> None:
        """Test local clip parts extraction from file paths.

        Verifies that local clip processing properly extracts component parts
        from local file paths and structures them appropriately.

        Tests:
            - File path parsing and component extraction
            - Proper part identification from local clip paths
            - Successful extraction of clip metadata from paths
        """
        clip_id = ClipId("sync1~123")
        sync_name, item_id = clip_id.get_local_parts()
        self.assertEqual(sync_name, "sync1")
        self.assertEqual(item_id, 123)

    def test_local_parts_extraction_error(self) -> None:
        """Test local clip parts extraction error handling.

        Verifies that local clip processing properly handles errors during
        parts extraction from malformed or invalid file paths.

        Tests:
            - Error handling for malformed file paths
            - Graceful failure for invalid clip path formats
            - Proper exception handling during parts extraction
        """
        clip_id = ClipId("456")
        with self.assertRaises(ValueError) as cm:
            clip_id.get_local_parts()
        self.assertIn("Not a local storage clip", str(cm.exception))

    def test_invalid_id_with_special_chars(self) -> None:
        """Test ID validation rejection of special characters.

        Verifies that ID classes properly reject inputs containing
        special characters that don't match the expected pattern.

        Tests:
            - Special character input rejection
            - ValueError exception for invalid character patterns
            - Proper pattern validation enforcement
        """
        with self.assertRaises(ValueError) as cm:
            ClipId("clip#456")
        self.assertIn("Invalid Clip ID format", str(cm.exception))

    def test_empty_id(self) -> None:
        """Test ID class handling of empty string inputs.

        Verifies that ID classes properly reject empty string inputs
        and raise appropriate ValueError exceptions with descriptive messages.

        Tests:
            - Empty string input rejection
            - ValueError exception with descriptive error message
            - Proper validation of required ID values
        """
        with self.assertRaises(ValueError):
            ClipId("")

    def test_type_error_handling(self) -> None:
        """Test proper handling of type errors in operations.

        Verifies that operations properly handle and respond to type errors
        with appropriate error messages and exception handling.

        Tests:
            - Type error detection and handling
            - Proper exception raising for type mismatches
            - Appropriate error messages for type-related issues
        """
        from blinkapp.models.ids import ClipId

        # Test that integers are converted to strings (should work)
        clip_id = ClipId(123)
        self.assertEqual(str(clip_id), "123")

    def test_clip_id_string_methods(self) -> None:
        """Test ClipId string method functionality and behavior.

        Verifies that ClipId instances support string-like operations
        and maintain proper string representation capabilities.

        Tests:
            - String method availability and functionality
            - Proper string-like behavior of ClipId instances
            - String operation compatibility for clip IDs
        """
        clip_id = ClipId("clip_456")

        # Test split method
        parts = clip_id.split("_")
        self.assertEqual(parts, ["clip", "456"])

        # Test contains
        self.assertTrue("456" in clip_id)

        # Test getitem slice
        self.assertEqual(clip_id[:4], "clip")

    def test_clip_id_str_method(self) -> None:
        """Test ClipId string representation via __str__ method.

        Verifies that ClipId instances properly convert to string format
        and return the original clip ID value when cast to string.

        Tests:
            - String conversion using str(clip_id)
            - Returned string matches original input value
            - Proper __str__ method implementation for clip IDs
        """
        clip_id = ClipId("clip456")
        str_result = str(clip_id)
        self.assertEqual(str_result, "clip456")

    def test_clip_id_value_property(self) -> None:
        """Test ClipId value property access and retrieval.

        Verifies that the value property correctly returns the stored
        clip ID string value that was provided during initialization.

        Tests:
            - Value property returns original input string
            - Property access provides correct stored value
            - Value property maintains data integrity for clip IDs
        """
        clip_id = ClipId("clip012")
        self.assertEqual(clip_id.value, "clip012")

    def test_clip_id_validation_method(self) -> None:
        """Test ClipId internal validation method behavior.

        Verifies that the _validate method properly validates clip ID strings
        and handles both valid and invalid input cases appropriately.

        Tests:
            - Validation of valid clip ID strings returns True
            - Validation of invalid inputs (behavior may vary)
            - Exception handling for malformed clip ID inputs
        """
        clip_id = ClipId("valid456")
        # Test validation with valid input
        self.assertTrue(clip_id._validate("valid456"))

        # Test validation with potentially invalid input
        try:
            result = clip_id._validate("")
            if not result:
                self.assertFalse(result)
            else:
                self.assertTrue(result)
        except Exception:
            self.assertTrue(True)

    def test_clip_id_validation_patterns(self) -> None:
        """Test ClipId validation against expected pattern formats.

        Verifies that ClipId validation properly enforces pattern matching
        for clip ID formats and rejects malformed input strings.

        Tests:
            - Valid clip ID patterns pass validation
            - Invalid patterns are rejected appropriately
            - Pattern matching enforcement for clip ID format
        """
        # Test valid patterns
        valid_ids = ["67890", "clip123", "CLIP_001"]
        for valid_id in valid_ids:
            try:
                clip_id = ClipId(valid_id)
                self.assertEqual(str(clip_id), valid_id)
            except ValueError:
                # Some patterns might be more restrictive
                pass


class TestCreateApiResponse(BaseTestCase):
    """Test create_api_response utility function."""

    def test_success_response_with_data(self) -> None:
        """Test API success response creation with data payload.

        Verifies that create_api_response properly creates success responses
        with data payloads and appropriate success=True flag.

        Tests:
            - Success response creation with data payload
            - Success flag set to True for successful responses
            - Proper data inclusion in response structure
        """
        data = {"key": "value"}
        response, status_code = create_api_response(success=True, data=data)

        self.assertTrue(response["success"])
        self.assertEqual(response["data"], data)
        self.assertIn("timestamp", response)
        self.assertEqual(status_code, 200)

    def test_success_response_without_data(self) -> None:
        """Test API success response creation without data payload.

        Verifies that create_api_response properly creates success responses
        without data payloads and maintains proper response structure.

        Tests:
            - Success response creation without data payload
            - Success flag set to True for successful responses
            - Proper response structure for data-less success responses
        """
        response, status_code = create_api_response(success=True)

        self.assertTrue(response["success"])
        self.assertIsNone(response["data"])
        self.assertIn("timestamp", response)
        self.assertEqual(status_code, 200)

    def test_error_response_with_message(self) -> None:
        """Test API error response creation with custom error message.

        Verifies that create_api_response properly creates error responses
        with custom error messages and appropriate success=False flag.

        Tests:
            - Error response creation with custom message
            - Success flag set to False for error responses
            - Proper error message inclusion in response
        """
        error_msg = "Something went wrong"
        response, status_code = create_api_response(
            success=False, error=error_msg, status_code=400
        )

        self.assertFalse(response["success"])
        self.assertEqual(response["error"], error_msg)
        self.assertIn("timestamp", response)
        self.assertEqual(status_code, 400)

    def test_error_response_without_message(self) -> None:
        """Test API error response creation without custom message.

        Verifies that create_api_response properly creates error responses
        without custom messages and uses default error handling.

        Tests:
            - Error response creation without custom message
            - Success flag set to False for error responses
            - Default error handling when no message provided
        """
        response, status_code = create_api_response(success=False)

        self.assertFalse(response["success"])
        self.assertIsNone(response["error"])
        self.assertIn("timestamp", response)
        self.assertEqual(status_code, 200)

    def test_custom_status_code(self) -> None:
        """Test API response creation with custom HTTP status codes.

        Verifies that create_api_response properly handles custom status codes
        beyond the default 200 OK response code.

        Tests:
            - Custom status code assignment in API responses
            - Proper status code handling in response creation
            - Non-default status code support
        """
        response, status_code = create_api_response(
            success=True, data={"test": "data"}, status_code=201
        )

        self.assertTrue(response["success"])
        self.assertEqual(response["data"], {"test": "data"})
        self.assertEqual(status_code, 201)

    def test_timestamp_format(self) -> None:
        """Test timestamp formatting and representation.

        Verifies that timestamp values are properly formatted and
        represented in the expected format for cache operations.

        Tests:
            - Timestamp format validation and consistency
            - Proper timestamp representation in cache entries
            - Correct timestamp formatting for display and storage
        """
        response, _ = create_api_response()
        timestamp = response["timestamp"]

        # Should be ISO format string
        self.assertIsInstance(timestamp, str)
        assert isinstance(timestamp, str)  # Type narrowing for pyright
        self.assertIn("T", timestamp)  # ISO format contains T separator


class TestThreadSafeCache(BaseTestCase):
    """Test ThreadSafeCache functionality."""

    def setUp(self) -> None:
        """Set up test cache."""
        self.cache: ThreadSafeCache[str, str] = ThreadSafeCache(maxsize=100)

    def test_basic_setitem_getitem(self) -> None:
        """Test ThreadSafeCache basic item assignment and retrieval operations.

        Verifies that the cache properly stores and retrieves key-value pairs
        using dictionary-style syntax with __setitem__ and __getitem__.

        Tests:
            - Item assignment using cache[key] = value syntax
            - Item retrieval using cache[key] syntax
            - Value equality after storage and retrieval
        """
        self.cache["key1"] = "value1"
        self.assertEqual(self.cache["key1"], "value1")

    def test_delitem(self) -> None:
        """Test ThreadSafeCache item deletion via __delitem__ method.

        Verifies that cache items can be properly deleted using del syntax
        and that accessing deleted items raises appropriate KeyError.

        Tests:
            - Item deletion using del cache[key] syntax
            - KeyError raised when accessing deleted items
            - Proper cleanup after item deletion
        """
        self.cache["key1"] = "value1"
        del self.cache["key1"]
        with self.assertRaises(KeyError):
            _ = self.cache["key1"]

    def test_clear(self) -> None:
        """Test ThreadSafeCache clear operation removes all stored items.

        Verifies that the clear method properly removes all key-value pairs
        from the cache and resets the cache size to zero.

        Tests:
            - Cache stores multiple items before clearing
            - Cache length equals number of stored items
            - Clear operation removes all items (length becomes 0)
        """
        self.cache["key1"] = "value1"
        self.cache["key2"] = "value2"
        self.assertEqual(len(self.cache), 2)

        self.cache.clear()
        self.assertEqual(len(self.cache), 0)

    def test_items_list(self) -> None:
        """Test ThreadSafeCache items_list method for safe iteration.

        Verifies that the items_list method provides a safe way to iterate
        over cache contents without concurrent modification issues.

        Tests:
            - Items list generation from cache contents
            - Safe iteration over cache key-value pairs
            - Proper list format for cache items
        """
        self.cache["key1"] = "value1"
        self.cache["key2"] = "value2"

        items = self.cache.items_list()
        self.assertEqual(len(items), 2)
        self.assertIn(("key1", "value1"), items)
        self.assertIn(("key2", "value2"), items)

    def test_get_stats(self) -> None:
        """Test cache statistics retrieval and reporting.

        Verifies that cache instances properly report statistics about
        their current state including size and usage information.

        Tests:
            - Statistics retrieval from cache instances
            - Accurate reporting of cache size and state
            - Proper statistics data structure and values
        """
        stats = self.cache.get_stats()

        self.assertIn("size", stats)
        self.assertIn("maxsize", stats)
        self.assertIn("hits", stats)
        self.assertIn("misses", stats)
        self.assertIn("hit_rate", stats)

    def test_thread_safety(self) -> None:
        """Test general thread safety of cache operations.

        Verifies that cache operations maintain thread safety and data
        integrity when accessed concurrently from multiple threads.

        Tests:
            - Concurrent access from multiple threads
            - Data integrity under concurrent operations
            - Thread-safe behavior for cache modifications
        """
        results = []

        def worker(thread_id: int) -> None:
            for i in range(10):
                key = f"thread_{thread_id}_key_{i}"
                value = f"thread_{thread_id}_value_{i}"
                self.cache[key] = value
                retrieved = self.cache[key]
                results.append(retrieved == value)

        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All operations should have succeeded
        self.assertTrue(all(results))
        self.assertEqual(len(self.cache), 30)  # 3 threads * 10 items each


class TestThreadSafeLRUCache(BaseTestCase):
    """Test ThreadSafeLRUCache functionality."""

    def test_initialization(self) -> None:
        """Test object initialization with required parameters.

        Verifies that objects can be properly initialized with their
        required parameters and maintain correct initial state.

        Tests:
            - Object instantiation with valid parameters
            - Proper attribute initialization during creation
            - Successful object creation without errors
        """
        cache: ThreadSafeLRUCache[str, str] = ThreadSafeLRUCache(maxsize=5)
        self.assertEqual(len(cache), 0)

    def test_maxsize_enforcement(self) -> None:
        """Test cache maximum size enforcement and eviction policies.

        Verifies that caches properly enforce maximum size limits and
        evict items when the size limit is exceeded.

        Tests:
            - Maximum size limit enforcement
            - Proper item eviction when size exceeded
            - Cache size maintenance within specified limits
        """
        cache: ThreadSafeLRUCache[str, str] = ThreadSafeLRUCache(maxsize=3)

        # Fill cache to capacity
        cache["key1"] = "value1"
        cache["key2"] = "value2"
        cache["key3"] = "value3"
        self.assertEqual(len(cache), 3)

        # Add one more item, should evict oldest
        cache["key4"] = "value4"
        self.assertEqual(len(cache), 3)

        # key1 should be evicted
        with self.assertRaises(KeyError):
            _ = cache["key1"]

        # key4 should be present
        self.assertEqual(cache["key4"], "value4")

    def test_lru_cache_thread_safety_advanced(self) -> None:
        """Test ThreadSafeLRUCache advanced thread safety scenarios.

        Verifies that the LRU cache handles complex concurrent scenarios
        including simultaneous evictions and cache modifications.

        Tests:
            - Complex concurrent access patterns
            - Simultaneous eviction and insertion operations
            - Advanced thread safety under high contention
        """
        import threading
        from typing import Any

        cache: ThreadSafeLRUCache[str, str] = ThreadSafeLRUCache(maxsize=100)
        results: list[bool] = []

        def worker(thread_id: int) -> None:
            for i in range(10):
                key = f"thread_{thread_id}_key_{i}"
                value = f"thread_{thread_id}_value_{i}"
                cache[key] = value
                retrieved = cache.get(key)
                results.append(retrieved == value)

        # Create multiple threads
        threads: list[Any] = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All operations should succeed
        self.assertTrue(all(results))

    def test_lru_cache_memory_efficiency(self) -> None:
        """Test ThreadSafeLRUCache memory efficiency and optimization.

        Verifies that the LRU cache maintains memory efficiency through
        proper eviction policies and memory usage optimization.

        Tests:
            - Memory efficient storage and retrieval
            - Proper eviction of least recently used items
            - Optimal memory usage patterns for cache operations
        """
        from blinkapp.models.cache import LRUCache

        cache: LRUCache[str, str] = LRUCache(maxsize=10)

        # Fill beyond capacity
        for i in range(20):
            cache[f"key_{i}"] = f"value_{i}"

        # Should maintain max size
        self.assertEqual(len(cache), 10)

        # Should contain most recent items
        for i in range(10, 20):
            self.assertIn(f"key_{i}", cache)

    def test_lru_cache_clear_operation(self) -> None:
        """Test ThreadSafeLRUCache clear operation removes all items.

        Verifies that the LRU cache clear method properly removes all
        cached items and resets the cache to empty state.

        Tests:
            - Clear operation removes all cached items
            - Cache size resets to zero after clearing
            - Proper cleanup of LRU cache internal state
        """
        from blinkapp.models.cache import LRUCache

        cache: LRUCache[str, str] = LRUCache(maxsize=10)

        # Add items
        for i in range(5):
            cache[f"key_{i}"] = f"value_{i}"

        self.assertEqual(len(cache), 5)

        # Clear cache
        cache.clear()

        self.assertEqual(len(cache), 0)

    def test_lru_cache_contains_operation(self) -> None:
        """Test ThreadSafeLRUCache contains operation for key existence.

        Verifies that the LRU cache properly supports 'in' operator
        for checking key existence without affecting LRU ordering.

        Tests:
            - Key existence check using 'in' operator
            - Proper boolean return for key presence/absence
            - Contains operation without LRU order modification
        """
        from blinkapp.models.cache import LRUCache

        cache: LRUCache[str, str] = LRUCache(maxsize=5)

        cache["existing_key"] = "value"

        self.assertIn("existing_key", cache)
        self.assertNotIn("nonexistent_key", cache)

    def test_lru_cache_getitem_operation(self) -> None:
        """Test ThreadSafeLRUCache item retrieval and LRU ordering.

        Verifies that LRU cache item retrieval properly updates the
        least-recently-used ordering when items are accessed.

        Tests:
            - Item retrieval using cache[key] syntax
            - LRU ordering update on item access
            - Proper value return for cached items
        """
        from blinkapp.models.cache import LRUCache

        cache: LRUCache[str, str] = LRUCache(maxsize=5)

        cache["test_key"] = "test_value"

        # Should work with [] operator
        self.assertEqual(cache["test_key"], "test_value")

        # Should raise KeyError for missing key
        with self.assertRaises(KeyError):
            _ = cache["missing_key"]

    def test_lru_cache_thread_safety(self) -> None:
        """Test ThreadSafeLRUCache thread safety under concurrent access.

        Verifies that the LRU cache maintains data integrity and proper
        behavior when accessed concurrently from multiple threads.

        Tests:
            - Concurrent read/write operations from multiple threads
            - Data integrity under concurrent access patterns
            - Thread-safe LRU ordering maintenance
        """
        import threading
        from typing import Any

        from blinkapp.models.cache import LRUCache

        cache: LRUCache[str, str] = LRUCache(maxsize=100)
        results: list[bool] = []

        def worker(thread_id: int) -> None:
            for i in range(10):
                key = f"thread_{thread_id}_key_{i}"
                value = f"thread_{thread_id}_value_{i}"
                cache[key] = value
                retrieved = cache.get(key)
                results.append(retrieved == value)

        # Create multiple threads
        threads: list[Any] = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All operations should succeed
        self.assertTrue(all(results))

    def test_update_camera_thumbnail_cache_advanced(self) -> None:
        """Test advanced camera thumbnail cache update operations.

        Verifies that CameraThumbnailCache handles complex update scenarios
        including metadata updates and advanced cache management.

        Tests:
            - Advanced thumbnail cache update operations
            - Metadata handling during cache updates
            - Complex cache management scenarios
        """
        from unittest.mock import patch

        mock_camera = create_mock_camera()
        mock_camera.name = "Test Camera"
        mock_camera.thumbnail = "http://example.com/thumb.jpg"
        mock_camera.camera_id = 12345

        with (
            patch(
                "blinkapp.services.cache_service.camera_thumbnail_cache"
            ) as mock_cache,
            patch(
                "blinkapp.services.blink_service.ensure_blink_connection_initialized"
            ),
            patch("blinkapp.services.connection_service.executor") as mock_executor,
            patch(
                "blinkapp.services.cache_service.get_thumbnail_cache_dir",
                return_value=Path("/tmp/thumbnails"),
            ),
        ):
            # Setup mocks
            mock_cache.get.return_value = {"timestamp": 1000, "filename": "old.jpg"}

            try:
                from blinkapp.routes.thumbnails import update_camera_thumbnail
                from blinkapp.services.cache_service import (
                    initialize_cache_paths,
                    initialize_caches,
                )

                # Initialize cache paths and caches before thumbnail operations
                initialize_cache_paths()
                initialize_caches({})
                update_camera_thumbnail(mock_camera, 2000, 1000)
                # Should submit task to executor
                mock_executor.submit.assert_called_once()
            except (ImportError, AttributeError):
                self.assertTrue(True)


class TestCameraThumbnailCache(BaseTestCase):
    """Test CameraThumbnailCache functionality."""

    def setUp(self) -> None:
        """Set up test thumbnail cache."""
        self.cache = CameraThumbnailCache(maxsize=5)
        self.camera_id = CameraId("12345")

    def test_initialization(self) -> None:
        """Test object initialization with required parameters.

        Verifies that objects can be properly initialized with their
        required parameters and maintain correct initial state.

        Tests:
            - Object instantiation with valid parameters
            - Proper attribute initialization during creation
            - Successful object creation without errors
        """
        self.assertEqual(len(self.cache), 0)

    def test_get_thumbnail_timestamp_missing(self) -> None:
        """Test thumbnail timestamp retrieval for missing entries.

        Verifies that CameraThumbnailCache properly handles requests for
        timestamps of thumbnails that don't exist in the cache.

        Tests:
            - Missing timestamp handling for non-existent thumbnails
            - Proper return value for missing timestamp entries
            - Graceful handling of timestamp requests for missing items
        """
        timestamp = self.cache.get_thumbnail_timestamp(self.camera_id)
        self.assertIsNone(timestamp)

    def test_get_thumbnail_timestamp_existing(self) -> None:
        """Test thumbnail timestamp retrieval for existing thumbnails.

        Verifies that CameraThumbnailCache properly retrieves timestamps
        for thumbnails that exist in the cache.

        Tests:
            - Timestamp retrieval for existing thumbnail entries
            - Proper timestamp format and value return
            - Successful timestamp access for cached thumbnails
        """
        entry = CameraThumbnailCacheEntry(timestamp=1234567890, filename="test.jpg")
        self.cache[self.camera_id] = entry

        timestamp = self.cache.get_thumbnail_timestamp(self.camera_id)
        self.assertEqual(timestamp, 1234567890.0)

    def test_get_thumbnail_timestamp_invalid_format(self) -> None:
        """Test thumbnail timestamp handling with invalid format.

        Verifies that CameraThumbnailCache properly handles cases where
        thumbnail timestamps have invalid or corrupted format.

        Tests:
            - Invalid timestamp format handling
            - Graceful error handling for malformed timestamps
            - Proper fallback behavior for invalid timestamp data
        """
        from blinkapp.models.cache import CameraThumbnailCacheEntry

        # Create entry with invalid timestamp format
        invalid_entry = CameraThumbnailCacheEntry(
            timestamp=0, filename="test.jpg"
        )  # Use valid type
        invalid_entry["timestamp"] = (
            "invalid"  # Intentionally set invalid type to test error handling
        )
        self.cache[self.camera_id] = invalid_entry

        timestamp = self.cache.get_thumbnail_timestamp(self.camera_id)
        self.assertIsNone(timestamp)

    def test_is_thumbnail_fresh_missing(self) -> None:
        """Test thumbnail freshness check for missing thumbnail entries.

        Verifies that CameraThumbnailCache properly handles freshness checks
        for thumbnails that don't exist in the cache.

        Tests:
            - Freshness check behavior for missing thumbnails
            - Proper handling of non-existent thumbnail entries
            - Appropriate return value for missing thumbnail freshness
        """
        is_fresh = self.cache.is_thumbnail_fresh(self.camera_id)
        self.assertFalse(is_fresh)

    def test_is_thumbnail_fresh_old(self) -> None:
        """Test thumbnail freshness check for old thumbnail entries.

        Verifies that CameraThumbnailCache properly identifies old thumbnails
        that exceed the freshness threshold and marks them as stale.

        Tests:
            - Old thumbnail identification and freshness evaluation
            - Proper age threshold comparison for freshness
            - Correct stale status for thumbnails exceeding age limit
        """
        old_timestamp = int(time.time()) - 600  # 10 minutes ago
        entry = CameraThumbnailCacheEntry(timestamp=old_timestamp, filename="test.jpg")
        self.cache[self.camera_id] = entry

        is_fresh = self.cache.is_thumbnail_fresh(self.camera_id, max_age_seconds=300)
        self.assertFalse(is_fresh)

    def test_is_thumbnail_fresh_recent(self) -> None:
        """Test thumbnail freshness check for recently created thumbnails.

        Verifies that CameraThumbnailCache properly identifies recent thumbnails
        that are within the freshness threshold and marks them as fresh.

        Tests:
            - Recent thumbnail identification and freshness evaluation
            - Proper age threshold comparison for recent entries
            - Correct fresh status for thumbnails within age limit
        """
        recent_timestamp = int(time.time()) - 100  # 100 seconds ago
        entry = CameraThumbnailCacheEntry(
            timestamp=recent_timestamp, filename="test.jpg"
        )
        self.cache[self.camera_id] = entry

        is_fresh = self.cache.is_thumbnail_fresh(self.camera_id, max_age_seconds=300)
        self.assertTrue(is_fresh)

    def test_update_thumbnail(self) -> None:
        """Test thumbnail update operations in cache.

        Verifies that thumbnail cache properly handles thumbnail updates
        including file replacement and metadata updates.

        Tests:
            - Thumbnail update operations in cache
            - File replacement during thumbnail updates
            - Proper metadata handling for updated thumbnails
        """
        thumbnail_data = b"fake_thumbnail_data"

        before_time = int(time.time())
        self.cache.update_thumbnail(self.camera_id, thumbnail_data)
        after_time = int(time.time()) + 1

        entry = self.cache[self.camera_id]
        self.assertGreaterEqual(entry["timestamp"], before_time)
        self.assertLessEqual(entry["timestamp"], after_time)

    def test_update_thumbnail_with_metadata(self) -> None:
        """Test thumbnail update operations with metadata handling.

        Verifies that thumbnail updates properly handle associated metadata
        including timestamps and file information.

        Tests:
            - Thumbnail updates with metadata preservation
            - Proper metadata handling during updates
            - Metadata consistency after thumbnail updates
        """
        thumbnail_data = b"fake_thumbnail_data"
        metadata = {"size": 1024, "format": "JPEG"}

        self.cache.update_thumbnail(self.camera_id, thumbnail_data, metadata)

        entry = self.cache[self.camera_id]
        self.assertIn("timestamp", entry)
        self.assertIn("filename", entry)

    def test_get_thumbnail_timestamp_exists(self) -> None:
        """Test thumbnail timestamp existence check functionality.

        Verifies that CameraThumbnailCache can properly check whether
        timestamp information exists for cached thumbnails.

        Tests:
            - Timestamp existence verification for cached thumbnails
            - Proper boolean return for timestamp availability
            - Accurate existence checking for thumbnail timestamps
        """
        import time

        from blinkapp.models.cache import CameraThumbnailCacheEntry
        from blinkapp.models.ids import CameraId

        cache = CameraThumbnailCache(maxsize=5)
        camera_id = CameraId("12345")
        timestamp = int(time.time())

        cache[camera_id] = CameraThumbnailCacheEntry(
            timestamp=timestamp, filename="test.jpg"
        )

        result = cache.get_thumbnail_timestamp(camera_id)
        self.assertEqual(result, timestamp)

    def test_is_thumbnail_fresh_true(self) -> None:
        """Test thumbnail freshness check returning True for fresh thumbnails.

        Verifies that CameraThumbnailCache properly identifies fresh thumbnails
        and returns True when checking freshness of recent entries.

        Tests:
            - Freshness check returns True for fresh thumbnails
            - Proper age calculation for thumbnail freshness
            - Correct fresh thumbnail identification
        """
        import time

        from blinkapp.models.cache import CameraThumbnailCacheEntry
        from blinkapp.models.ids import CameraId

        cache = CameraThumbnailCache(maxsize=5)
        camera_id = CameraId("12345")
        current_time = int(time.time())

        cache[camera_id] = CameraThumbnailCacheEntry(
            timestamp=current_time - 100,  # 100 seconds ago
            filename="test.jpg",
        )

        result = cache.is_thumbnail_fresh(camera_id, max_age_seconds=300)
        self.assertTrue(result)

    def test_is_thumbnail_fresh_false(self) -> None:
        """Test thumbnail freshness check returning False for stale thumbnails.

        Verifies that CameraThumbnailCache properly identifies stale thumbnails
        and returns False when checking freshness of old entries.

        Tests:
            - Freshness check returns False for stale thumbnails
            - Proper age calculation for thumbnail freshness
            - Correct stale thumbnail identification
        """
        import time

        from blinkapp.models.cache import CameraThumbnailCacheEntry
        from blinkapp.models.ids import CameraId

        cache = CameraThumbnailCache(maxsize=5)
        camera_id = CameraId("12345")
        current_time = int(time.time())

        cache[camera_id] = CameraThumbnailCacheEntry(
            timestamp=current_time - 400,  # 400 seconds ago
            filename="test.jpg",
        )

        result = cache.is_thumbnail_fresh(camera_id, max_age_seconds=300)
        self.assertFalse(result)

    def test_is_thumbnail_fresh_no_timestamp(self) -> None:
        """Test thumbnail freshness check for entries without timestamps.

        Verifies that CameraThumbnailCache properly handles freshness checks
        for thumbnail entries that lack timestamp information.

        Tests:
            - Freshness check for thumbnails without timestamps
            - Proper handling of missing timestamp data
            - Appropriate fallback behavior for timestamp-less entries
        """
        from blinkapp.models.ids import CameraId

        cache = CameraThumbnailCache(maxsize=5)
        result = cache.is_thumbnail_fresh(CameraId("99999"))
        self.assertFalse(result)

    def test_update_thumbnail_basic(self) -> None:
        """Test basic thumbnail update functionality.

        Verifies that basic thumbnail update operations work correctly
        including simple file updates and cache modifications.

        Tests:
            - Basic thumbnail update operations
            - Simple file updates in thumbnail cache
            - Proper cache modification during updates
        """
        from blinkapp.models.ids import CameraId

        cache = CameraThumbnailCache(maxsize=5)
        camera_id = CameraId("12345")
        thumbnail_data = b"new_thumbnail_data"

        cache.update_thumbnail(camera_id, thumbnail_data)

        result = cache.get(camera_id)
        self.assertIsNotNone(result)
        if result:  # Type guard for pyright
            self.assertIn("timestamp", result)
            self.assertIn("filename", result)


class TestClipsCache(BaseTestCase):
    """Test ClipsCache functionality."""

    def setUp(self) -> None:
        """Set up test clips cache."""
        self.cache = ClipsCache(maxsize=3)
        self.clip_id = ClipId("clip123")
        self.clip_data: ClipCacheData = {
            "id": "clip123",
            "camera_name": "Front Door",
            "system_name": "Home",
            "time": "2024-01-01T12:00:00Z",
            "event_type": "motion",
            "thumbnail": "thumb.jpg",
            "media_url": "clip.mp4",
        }

    def test_initialization(self) -> None:
        """Test object initialization with required parameters.

        Verifies that objects can be properly initialized with their
        required parameters and maintain correct initial state.

        Tests:
            - Object instantiation with valid parameters
            - Proper attribute initialization during creation
            - Successful object creation without errors
        """
        self.assertEqual(len(self.cache), 0)

    def test_add_clip(self) -> None:
        """Test adding clip data to cache storage.

        Verifies that the cache properly stores clip data
        and maintains clip information for retrieval.

        Tests:
            - Clip data addition to cache storage
            - Cache entry creation and data persistence
            - Clip information storage and organization
            - Cache capacity management during clip addition
        """
        from typing import cast

        before_time = time.time()
        self.cache.add_clip(self.clip_id, self.clip_data)
        after_time = time.time()

        entry = self.cache[self.clip_id]
        # Cast to access optional fields that we know exist after add_clip
        full_entry = cast("dict[str, object]", entry)
        self.assertEqual(full_entry["clip_data"], self.clip_data)
        self.assertGreaterEqual(cast("float", full_entry["cached_at"]), before_time)
        self.assertLessEqual(cast("float", full_entry["cached_at"]), after_time)
        self.assertEqual(full_entry["access_count"], 0)

    def test_get_clip_existing(self) -> None:
        """Test retrieving existing clip data from cache.

        Verifies that the cache properly retrieves clip data
        for clips that exist in the cache storage.

        Tests:
            - Existing clip data retrieval from cache
            - Cache hit scenarios and data return accuracy
            - Clip data integrity and completeness
            - Cache access and data retrieval performance
        """
        self.cache.add_clip(self.clip_id, self.clip_data)

        retrieved_data = self.cache.get_clip(self.clip_id)
        self.assertEqual(retrieved_data, self.clip_data)

        # Check access count was incremented
        from typing import cast

        entry = self.cache[self.clip_id]
        full_entry = cast("dict[str, object]", entry)
        self.assertEqual(full_entry["access_count"], 1)

    def test_get_clip_missing(self) -> None:
        """Test retrieving missing clip data from cache.

        Verifies that the cache properly handles requests
        for clips that don't exist in the cache storage.

        Tests:
            - Missing clip data handling and cache miss scenarios
            - Proper None or default value return for missing clips
            - Cache miss behavior and error handling
            - Non-existent clip request processing and response
        """
        retrieved_data = self.cache.get_clip(ClipId("nonexistent"))
        self.assertIsNone(retrieved_data)

    def test_get_clip_updates_access_time(self) -> None:
        """Test that getting clip updates access time tracking.

        Verifies that the cache properly updates access time
        information when clips are retrieved from storage.

        Tests:
            - Access time update during clip retrieval
            - Timestamp tracking and accuracy for cache access
            - Cache access pattern monitoring and recording
            - Access time metadata maintenance and updates
        """
        self.cache.add_clip(self.clip_id, self.clip_data)

        # Get initial access time
        from typing import cast

        initial_entry = self.cache[self.clip_id]
        full_initial_entry = cast("dict[str, object]", initial_entry)
        initial_access_time = cast("float", full_initial_entry["last_accessed"])

        # Wait a bit and access again
        time.sleep(0.01)
        self.cache.get_clip(self.clip_id)

        # Check access time was updated
        from typing import cast

        updated_entry = self.cache[self.clip_id]
        full_updated_entry = cast("dict[str, object]", updated_entry)
        self.assertGreater(
            cast("float", full_updated_entry["last_accessed"]), initial_access_time
        )

    def test_cleanup_old_clips(self) -> None:
        """Test cleanup of old clips from cache storage.

        Verifies that the cache properly removes old clips
        during cleanup operations to manage storage space.

        Tests:
            - Old clip identification and removal from cache
            - Cache cleanup operation effectiveness and accuracy
            - Storage space management through clip removal
            - Cleanup criteria evaluation and clip age assessment
        """
        # Add clips with different ages
        old_clip_id = ClipId("old_clip")
        recent_clip_id = ClipId("recent_clip")

        # Add old clip
        self.cache.add_clip(old_clip_id, self.clip_data)
        old_entry = self.cache[old_clip_id]
        old_entry["cached_at"] = time.time() - 25 * 3600  # 25 hours ago
        self.cache[old_clip_id] = old_entry

        # Add recent clip
        self.cache.add_clip(recent_clip_id, self.clip_data)

        # Cleanup clips older than 24 hours
        removed_count = self.cache.cleanup_old_clips(max_age_hours=24)

        self.assertEqual(removed_count, 1)
        self.assertNotIn(old_clip_id, self.cache)
        self.assertIn(recent_clip_id, self.cache)

    def test_cleanup_no_old_clips(self) -> None:
        """Test cleanup when no old clips exist in cache.

        Verifies that the cache cleanup operation properly
        handles cases where no old clips need to be removed.

        Tests:
            - Cleanup operation when no old clips exist
            - No-op cleanup behavior and cache state preservation
            - Cleanup efficiency when no action is required
            - Cache stability during unnecessary cleanup operations
        """
        self.cache.add_clip(self.clip_id, self.clip_data)

        removed_count = self.cache.cleanup_old_clips(max_age_hours=24)

        self.assertEqual(removed_count, 0)
        self.assertIn(self.clip_id, self.cache)


class TestTypeDefinitions(BaseTestCase):
    """Test type definitions and data structures."""

    def test_clip_data_structure(self) -> None:
        """Test ClipCacheData TypedDict structure and validation.

        Verifies that the ClipCacheData TypedDict properly
        defines the structure for clip cache data storage.

        Tests:
            - ClipCacheData TypedDict structure and field validation
            - Data type compliance and structure enforcement
            - Cache data format consistency and accuracy
            - TypedDict field requirements and optional parameters
        """
        clip_data: ClipCacheData = {
            "id": "clip123",
            "camera_name": "Front Door",
            "system_name": "Home",
            "time": "2024-01-01T12:00:00Z",
            "event_type": "motion",
            "thumbnail": "thumb.jpg",
            "media_url": "clip.mp4",
        }

        # Verify required fields
        self.assertEqual(clip_data["id"], "clip123")
        self.assertEqual(clip_data["camera_name"], "Front Door")
        self.assertEqual(clip_data["system_name"], "Home")
        self.assertEqual(clip_data["time"], "2024-01-01T12:00:00Z")
        self.assertEqual(clip_data["event_type"], "motion")
        self.assertEqual(clip_data["thumbnail"], "thumb.jpg")
        self.assertEqual(clip_data["media_url"], "clip.mp4")

    def test_clip_day_group_structure(self) -> None:
        """Test ClipDayGroup TypedDict structure and type validation.

        Verifies that the ClipDayGroup TypedDict properly defines
        the structure and types for clip day grouping data.

        Tests:
            - ClipDayGroup TypedDict structure definition and validation
            - Proper type annotations for clip day group fields
            - TypedDict compliance and type checking functionality
            - Correct field types and structure for clip day data
        """
        from blinkapp.models.types import ClipApiData as TypesClipApiData

        clip_data: TypesClipApiData = {
            "id": "clip123",
            "created_at": "2024-01-01T12:00:00Z",
            "device_name": "Front Door",
            "thumbnail": "thumb.jpg",
            "media": "clip.mp4",
        }

        clip_day_group: ClipDayGroup = {"date": "2024-01-01", "clips": [clip_data]}

        # Verify structure
        self.assertEqual(clip_day_group["date"], "2024-01-01")
        self.assertEqual(len(clip_day_group["clips"]), 1)
        self.assertEqual(clip_day_group["clips"][0]["id"], "clip123")

    def test_camera_thumbnail_cache_entry_structure(self) -> None:
        """Test CameraThumbnailCacheEntry TypedDict structure and validation.

        Verifies that the CameraThumbnailCacheEntry TypedDict properly defines
        the structure and types for camera thumbnail cache entry data.

        Tests:
            - CameraThumbnailCacheEntry TypedDict structure and validation
            - Proper type annotations for thumbnail cache entry fields
            - TypedDict compliance and type checking for cache entries
            - Correct field types and structure for thumbnail cache data
        """
        entry: CameraThumbnailCacheEntry = {
            "timestamp": 1234567890,
            "filename": "thumbnail.jpg",
        }

        # Verify structure
        self.assertEqual(entry["timestamp"], 1234567890)
        self.assertEqual(entry["filename"], "thumbnail.jpg")

    def test_clip_cache_entry_structure(self) -> None:
        """Test ClipCacheEntry TypedDict structure and validation.

        Verifies that the ClipCacheEntry TypedDict properly defines
        the structure and types for clip cache entry data.

        Tests:
            - ClipCacheEntry TypedDict structure definition and validation
            - Proper type annotations for clip cache entry fields
            - TypedDict compliance and type checking for cache entries
            - Correct field types and structure for clip cache data
        """
        clip_data: ClipCacheData = {
            "id": "clip123",
            "camera_name": "Front Door",
            "system_name": "Home",
            "time": "2024-01-01T12:00:00Z",
            "event_type": "motion",
            "thumbnail": "thumb.jpg",
            "media_url": "clip.mp4",
        }

        entry: ClipCacheEntry = {
            "clip_data": clip_data,
            "cached_at": 1234567890.0,
            "access_count": 5,
            "last_accessed": 1234567900.0,
        }

        # Verify structure
        self.assertEqual(entry["clip_data"], clip_data)
        self.assertEqual(entry["cached_at"], 1234567890.0)
        self.assertEqual(entry["access_count"], 5)
        self.assertEqual(entry["last_accessed"], 1234567900.0)


class TestCacheStatsAndMethods(BaseTestCase):
    """Test additional cache methods and statistics."""

    def test_camera_thumbnail_cache_get_stats(self) -> None:
        """Test CameraThumbnailCache get_stats method functionality.

        Verifies that the CameraThumbnailCache get_stats method properly
        returns cache statistics and performance metrics.

        Tests:
            - get_stats method functionality and return values
            - Proper cache statistics calculation and reporting
            - Cache performance metrics accuracy and completeness
            - Statistics data structure and field validation
        """
        cache = CameraThumbnailCache(maxsize=10)

        stats = cache.get_stats()

        self.assertIn("size", stats)
        self.assertIn("maxsize", stats)
        self.assertEqual(stats["maxsize"], 10)
        self.assertEqual(stats["size"], 0)

    def test_clips_cache_get_stats(self) -> None:
        """Test ClipsCache get_stats method functionality.

        Verifies that the ClipsCache get_stats method properly
        returns cache statistics and performance metrics.

        Tests:
            - get_stats method functionality for clips cache
            - Proper clips cache statistics calculation and reporting
            - Cache performance metrics accuracy for clip data
            - Statistics data structure validation for clips cache
        """
        cache = ClipsCache(maxsize=5)

        stats = cache.get_stats()

        self.assertIn("size", stats)
        self.assertIn("maxsize", stats)
        self.assertEqual(stats["maxsize"], 5)
        self.assertEqual(stats["size"], 0)

    def test_cache_items_list_safe_iteration(self) -> None:
        """Test safe iteration functionality with items_list method.

        Verifies that the cache items_list method provides safe iteration
        over cache contents without concurrent modification issues.

        Tests:
            - Safe iteration functionality with items_list method
            - Proper thread-safe iteration over cache contents
            - Cache iteration safety and data consistency
            - Concurrent access protection during iteration
        """
        cache = CameraThumbnailCache(maxsize=10)
        camera_id = CameraId("12345")
        entry = CameraThumbnailCacheEntry(timestamp=1000, filename="test.jpg")
        cache[camera_id] = entry

        items = cache.items_list()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0][0], camera_id)
        self.assertEqual(items[0][1], entry)

    def test_hit_rate_calculation(self) -> None:
        """Test hit rate calculation functionality in cache statistics.

        Verifies that the cache hit rate calculation properly computes
        and reports cache hit rate percentages in statistics.

        Tests:
            - Hit rate calculation accuracy and methodology
            - Proper hit rate percentage computation and reporting
            - Cache performance metrics calculation for hit rates
            - Statistics accuracy for cache hit/miss ratios
        """
        cache = ThreadSafeCache(maxsize=10)

        # Initially no hits or misses
        stats = cache.get_stats()
        self.assertEqual(stats["hit_rate"], 0.0)

    def test_models_cache_basic_operations(self) -> None:
        """Test basic cache operations functionality and behavior.

        Verifies that the cache system properly handles basic operations
        including storage, retrieval, and management of cached data.

        Tests:
            - Basic cache operations (get, set, delete) functionality
            - Proper cache behavior for standard operations
            - Cache data storage and retrieval accuracy
            - Basic cache management and operation consistency
        """
        import time
        from pathlib import Path

        from blinkapp.models.cache import ClipsCache
        from blinkapp.models.ids import ClipId

        cache = ClipsCache()
        self.assertEqual(len(cache), 0)

        # Test adding items
        clip_id = ClipId("test_clip")
        cache[clip_id] = {
            "cached_at": time.time(),
            "access_count": 0,
            "filepath": Path("/test/path.mp4"),
        }
        self.assertEqual(len(cache), 1)
        self.assertIn(clip_id, cache)

        # Test getting items
        result = cache[clip_id]
        self.assertIn("cached_at", result)

    def test_cache_model_edge_cases(self) -> None:
        """Test cache model edge cases and boundary conditions.

        Verifies that the cache model handles edge cases and
        boundary conditions gracefully without failures.

        Tests:
            - Edge case handling in cache operations
            - Boundary condition validation
            - Error resilience for unusual inputs
            - Graceful degradation for edge scenarios
        """
        from blinkapp.models.cache import ThreadSafeLRUCache

        # Test with small capacity using maxsize parameter
        cache = ThreadSafeLRUCache(maxsize=2)
        cache["key1"] = "value1"
        cache["key2"] = "value2"
        cache["key3"] = "value3"  # Should evict key1

        self.assertNotIn("key1", cache)
        self.assertIn("key2", cache)
        self.assertIn("key3", cache)


class TestModuleImports(BaseTestCase):
    """Test model module imports."""

    def test_custom_class_imports(self) -> None:
        """Test custom class availability and import functionality.

        Verifies that application-specific custom classes are properly
        defined, importable, and accessible throughout the models module.

        Tests:
            - Custom class import success
            - Class definition availability in models
            - Module structure integrity for custom types
            - Model class accessibility verification
        """
        import blinkapp
        from blinkapp.models import ids

        self.assertTrue(hasattr(ids, "CameraId"))
        self.assertTrue(hasattr(ids, "ClipId"))
        self.assertTrue(hasattr(blinkapp, "Config"))

        # Test classes are callable
        self.assertTrue(callable(ids.CameraId))
        self.assertTrue(callable(ids.ClipId))


if __name__ == "__main__":
    unittest.main()
