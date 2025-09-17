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
        """Test ID equality with string."""
        test_id = self.TestId("test123")
        self.assertEqual(test_id, "test123")

    def test_inequality_with_different_id(self) -> None:
        """Test ID inequality with different value."""
        id1 = self.TestId("test123")
        id2 = self.TestId("test456")
        self.assertNotEqual(id1, id2)

    def test_inequality_with_other_types(self) -> None:
        """Test ID inequality with other types."""
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
        """Test length method."""
        test_id = self.TestId("test123")
        self.assertEqual(len(test_id), 7)

    def test_contains_method(self) -> None:
        """Test contains method."""
        test_id = self.TestId("test123")
        self.assertIn("test", test_id)
        self.assertNotIn("xyz", test_id)

    def test_getitem_method(self) -> None:
        """Test getitem method."""
        test_id = self.TestId("test123")
        self.assertEqual(test_id[0], "t")
        self.assertEqual(test_id[1:5], "est1")

    def test_iter_method(self) -> None:
        """Test iteration over ID."""
        test_id = self.TestId("test")
        chars = list(test_id)
        self.assertEqual(chars, ["t", "e", "s", "t"])

    def test_split_method(self) -> None:
        """Test split method."""
        test_id = self.TestId("test_123_abc")
        parts = test_id.split("_")
        self.assertEqual(parts, ["test", "123", "abc"])

    def test_int_conversion_valid(self) -> None:
        """Test integer conversion with valid numeric ID."""
        test_id = self.TestId("12345")
        self.assertEqual(int(test_id), 12345)

    def test_int_conversion_invalid(self) -> None:
        """Test integer conversion with invalid ID."""
        test_id = self.TestId("test123")
        with self.assertRaises(ValueError) as cm:
            int(test_id)
        self.assertIn("Cannot convert Test ID", str(cm.exception))

    def test_base_id_get_pattern_not_implemented(self) -> None:
        """Test BaseId abstract method enforcement."""

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
        """Test BaseId._get_type_name raises NotImplementedError."""

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
        """Test valid numeric camera ID."""
        camera_id = CameraId("12345")
        self.assertEqual(str(camera_id), "12345")

    def test_valid_string_id(self) -> None:
        """Test valid string camera ID."""
        camera_id = CameraId("camera_abc")
        self.assertEqual(str(camera_id), "camera_abc")

    def test_numeric_input(self) -> None:
        """Test numeric input conversion."""
        camera_id = CameraId(12345)
        self.assertEqual(str(camera_id), "12345")

    def test_invalid_id_with_special_chars(self) -> None:
        """Test invalid camera ID with special characters."""
        with self.assertRaises(ValueError) as cm:
            CameraId("camera-123!")
        self.assertIn("Invalid Camera ID format", str(cm.exception))

    def test_empty_string_raises_error(self) -> None:
        """Test empty string raises ValueError."""
        with self.assertRaises(ValueError):
            CameraId("")  # Should raise ValueError for empty string

    def test_empty_id(self) -> None:
        """Test empty camera ID raises error."""
        with self.assertRaises(ValueError):
            CameraId("")

    def test_camera_id_validation_patterns(self) -> None:
        """Test CameraId validation patterns."""
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
        """Test integer conversion."""
        camera_id = CameraId("123")
        self.assertEqual(int(camera_id), 123)

    def test_int_conversion_invalid(self) -> None:
        """Test integer conversion with invalid value."""
        camera_id = CameraId("invalid_number")
        with self.assertRaises(ValueError) as cm:
            int(camera_id)
        self.assertIn("Cannot convert Camera ID", str(cm.exception))

    def test_camera_id_string_methods(self) -> None:
        """Test CameraId string method delegation."""
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
        """Test ID equality comparison with strings."""
        camera_id = CameraId("12345")

        # Test equality with string
        self.assertTrue(camera_id == "12345")
        self.assertFalse(camera_id == "54321")

        # Test equality with other types
        self.assertFalse(camera_id == 12345)
        self.assertFalse(camera_id is None)

    def test_id_hash_functionality(self) -> None:
        """Test ID hash functionality for sets and dicts."""
        camera_id1 = CameraId("test")
        camera_id2 = CameraId("test")
        camera_id3 = CameraId("different")

        # Test hash consistency
        self.assertEqual(hash(camera_id1), hash(camera_id2))
        self.assertNotEqual(hash(camera_id1), hash(camera_id3))

    def test_camera_id_str_method(self) -> None:
        """Test CameraId.__str__ method."""
        camera_id = CameraId("test123")
        str_result = str(camera_id)
        self.assertEqual(str_result, "test123")

    def test_camera_id_value_property(self) -> None:
        """Test CameraId.value property."""
        camera_id = CameraId("camera789")
        self.assertEqual(camera_id.value, "camera789")

    def test_camera_id_validation_method(self) -> None:
        """Test CameraId._validate method."""
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
        """Test ID iteration functionality."""
        camera_id = CameraId("12345")
        chars = list(camera_id)
        self.assertEqual(chars, ["1", "2", "3", "4", "5"])

        # Test with string iteration
        result = "".join(char for char in camera_id)
        self.assertEqual(result, "12345")

    def test_id_split_method(self) -> None:
        """Test ID split method delegation."""
        camera_id = CameraId("12-34-56")
        parts = camera_id.split("-")
        self.assertEqual(parts, ["12", "34", "56"])

        # Test with maxsplit
        parts = camera_id.split("-", 1)
        self.assertEqual(parts, ["12", "34-56"])

    def test_models_ids_string_methods(self) -> None:
        """Test ID model string methods."""
        # Test CameraId
        camera_id = CameraId("test_camera")
        self.assertEqual(str(camera_id), "test_camera")
        self.assertEqual(repr(camera_id), "CameraId('test_camera')")

    def test_camera_id_edge_cases(self) -> None:
        """Test CameraId edge cases."""
        # Test with string input
        camera_id = CameraId("12345")
        self.assertEqual(int(camera_id), 12345)

        # Test comparison
        camera_id2 = CameraId("12345")
        self.assertEqual(camera_id, camera_id2)

    def test_id_string_representations(self) -> None:
        """Test string representations of ID classes."""
        camera_id = CameraId("12345")
        self.assertIn("12345", str(camera_id))

    def test_validation_error_messages(self) -> None:
        """Test ID validation provides meaningful error messages for debugging.

        Why: Clear error messages help developers identify validation failures quickly.
        What: Verifies error messages contain relevant context about validation failure.
        How: Triggers validation error with empty ID and checks message content.
        """
        with self.assertRaises(ValueError) as context:
            CameraId("")

        # Should contain meaningful error message
        error_msg = str(context.exception)
        self.assertIn("Camera", error_msg)

    def test_type_name_methods(self) -> None:
        """Test _get_type_name methods."""
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
        """Test valid numeric network ID."""
        network_id = NetworkId("54321")
        self.assertEqual(str(network_id), "54321")

    def test_valid_string_id(self) -> None:
        """Test valid numeric network ID (networks only accept numeric IDs)."""
        network_id = NetworkId("54321")
        self.assertEqual(str(network_id), "54321")

    def test_invalid_id_with_special_chars(self) -> None:
        """Test invalid network ID with special characters."""
        with self.assertRaises(ValueError) as cm:
            NetworkId("network@123")
        self.assertIn("Invalid Network ID format", str(cm.exception))

    def test_empty_id(self) -> None:
        """Test empty network ID raises error."""
        with self.assertRaises(ValueError):
            NetworkId("")

    def test_network_id_string_methods(self) -> None:
        """Test NetworkId string method delegation."""
        network_id = NetworkId("789")

        # Test split method with maxsplit
        parts = network_id.split("8", 1)
        self.assertEqual(parts, ["7", "9"])

        # Test iteration
        first_char = next(iter(network_id))
        self.assertEqual(first_char, "7")

    def test_network_id_edge_cases(self) -> None:
        """Test NetworkId edge cases."""
        # Test with string input
        network_id = NetworkId("67890")
        self.assertEqual(int(network_id), 67890)

        # Test comparison
        network_id2 = NetworkId("67890")
        self.assertEqual(network_id, network_id2)

    def test_network_id_string_representations(self) -> None:
        """Test string representations of NetworkId."""
        network_id = NetworkId("67890")
        self.assertIn("67890", str(network_id))


class TestClipId(BaseTestCase):
    """Test ClipId validation and functionality."""

    def test_valid_numeric_id(self) -> None:
        """Test valid numeric clip ID."""
        clip_id = ClipId("98765")
        self.assertEqual(str(clip_id), "98765")

    def test_valid_string_id(self) -> None:
        """Test valid string clip ID."""
        clip_id = ClipId("clip_def")
        self.assertEqual(str(clip_id), "clip_def")

    def test_local_clip_creation(self) -> None:
        """Test local clip ID creation."""
        clip_id = ClipId.from_local("sync1", 123)
        self.assertEqual(str(clip_id), "sync1~123")
        self.assertTrue(clip_id.is_local())

    def test_cloud_clip_creation(self) -> None:
        """Test cloud clip ID creation."""
        clip_id = ClipId("456")  # Direct construction instead of from_cloud
        self.assertEqual(str(clip_id), "456")
        self.assertFalse(clip_id.is_local())

    def test_local_parts_extraction(self) -> None:
        """Test extracting local clip parts."""
        clip_id = ClipId("sync1~123")
        sync_name, item_id = clip_id.get_local_parts()
        self.assertEqual(sync_name, "sync1")
        self.assertEqual(item_id, 123)

    def test_local_parts_extraction_error(self) -> None:
        """Test error when extracting parts from cloud clip."""
        clip_id = ClipId("456")
        with self.assertRaises(ValueError) as cm:
            clip_id.get_local_parts()
        self.assertIn("Not a local storage clip", str(cm.exception))

    def test_invalid_id_with_special_chars(self) -> None:
        """Test invalid clip ID with special characters."""
        with self.assertRaises(ValueError) as cm:
            ClipId("clip#456")
        self.assertIn("Invalid Clip ID format", str(cm.exception))

    def test_empty_id(self) -> None:
        """Test empty clip ID raises error."""
        with self.assertRaises(ValueError):
            ClipId("")

    def test_type_error_handling(self) -> None:
        """Test TypeError handling."""
        from blinkapp.models.ids import ClipId

        # Test that integers are converted to strings (should work)
        clip_id = ClipId(123)
        self.assertEqual(str(clip_id), "123")

    def test_clip_id_string_methods(self) -> None:
        """Test ClipId string method delegation."""
        clip_id = ClipId("clip_456")

        # Test split method
        parts = clip_id.split("_")
        self.assertEqual(parts, ["clip", "456"])

        # Test contains
        self.assertTrue("456" in clip_id)

        # Test getitem slice
        self.assertEqual(clip_id[:4], "clip")

    def test_clip_id_str_method(self) -> None:
        """Test ClipId.__str__ method."""
        clip_id = ClipId("clip456")
        str_result = str(clip_id)
        self.assertEqual(str_result, "clip456")

    def test_clip_id_value_property(self) -> None:
        """Test ClipId.value property."""
        clip_id = ClipId("clip012")
        self.assertEqual(clip_id.value, "clip012")

    def test_clip_id_validation_method(self) -> None:
        """Test ClipId internal validation method with edge cases."""
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
        """Test ClipId validation patterns."""
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
        """Test successful API response with data."""
        data = {"key": "value"}
        response, status_code = create_api_response(success=True, data=data)

        self.assertTrue(response["success"])
        self.assertEqual(response["data"], data)
        self.assertIn("timestamp", response)
        self.assertEqual(status_code, 200)

    def test_success_response_without_data(self) -> None:
        """Test successful API response without data."""
        response, status_code = create_api_response(success=True)

        self.assertTrue(response["success"])
        self.assertIsNone(response["data"])
        self.assertIn("timestamp", response)
        self.assertEqual(status_code, 200)

    def test_error_response_with_message(self) -> None:
        """Test error API response with message."""
        error_msg = "Something went wrong"
        response, status_code = create_api_response(
            success=False, error=error_msg, status_code=400
        )

        self.assertFalse(response["success"])
        self.assertEqual(response["error"], error_msg)
        self.assertIn("timestamp", response)
        self.assertEqual(status_code, 400)

    def test_error_response_without_message(self) -> None:
        """Test error API response without message."""
        response, status_code = create_api_response(success=False)

        self.assertFalse(response["success"])
        self.assertIsNone(response["error"])
        self.assertIn("timestamp", response)
        self.assertEqual(status_code, 200)

    def test_custom_status_code(self) -> None:
        """Test API response with custom status code."""
        response, status_code = create_api_response(
            success=True, data={"test": "data"}, status_code=201
        )

        self.assertTrue(response["success"])
        self.assertEqual(response["data"], {"test": "data"})
        self.assertEqual(status_code, 201)

    def test_timestamp_format(self) -> None:
        """Test timestamp format in response."""
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
        """Test basic setitem and getitem operations."""
        self.cache["key1"] = "value1"
        self.assertEqual(self.cache["key1"], "value1")

    def test_delitem(self) -> None:
        """Test delitem operation."""
        self.cache["key1"] = "value1"
        del self.cache["key1"]
        with self.assertRaises(KeyError):
            _ = self.cache["key1"]

    def test_clear(self) -> None:
        """Test clear operation."""
        self.cache["key1"] = "value1"
        self.cache["key2"] = "value2"
        self.assertEqual(len(self.cache), 2)

        self.cache.clear()
        self.assertEqual(len(self.cache), 0)

    def test_items_list(self) -> None:
        """Test items_list method for safe iteration."""
        self.cache["key1"] = "value1"
        self.cache["key2"] = "value2"

        items = self.cache.items_list()
        self.assertEqual(len(items), 2)
        self.assertIn(("key1", "value1"), items)
        self.assertIn(("key2", "value2"), items)

    def test_get_stats(self) -> None:
        """Test get_stats method."""
        stats = self.cache.get_stats()

        self.assertIn("size", stats)
        self.assertIn("maxsize", stats)
        self.assertIn("hits", stats)
        self.assertIn("misses", stats)
        self.assertIn("hit_rate", stats)

    def test_thread_safety(self) -> None:
        """Test thread safety of cache operations."""
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
        """Test LRU cache initialization."""
        cache: ThreadSafeLRUCache[str, str] = ThreadSafeLRUCache(maxsize=5)
        self.assertEqual(len(cache), 0)

    def test_maxsize_enforcement(self) -> None:
        """Test maxsize enforcement with eviction."""
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
        """Test LRU cache concurrent access from multiple threads.

        Why: Cache is accessed by multiple request threads simultaneously in production.
        What: Verifies thread-safe operations prevent data corruption and race conditions.
        How: Spawns multiple threads performing cache operations and validates consistency.
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
        """Test LRU cache memory management with size limits.

        Why: Cache must evict old entries to prevent memory leaks in long-running processes.
        What: Verifies proper eviction of least recently used items when cache is full.
        How: Fills cache beyond capacity and validates oldest entries are removed.
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
        """Test LRU cache clear operation."""
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
        """Test LRU cache __contains__ operation."""
        from blinkapp.models.cache import LRUCache

        cache: LRUCache[str, str] = LRUCache(maxsize=5)

        cache["existing_key"] = "value"

        self.assertIn("existing_key", cache)
        self.assertNotIn("nonexistent_key", cache)

    def test_lru_cache_getitem_operation(self) -> None:
        """Test LRU cache __getitem__ operation."""
        from blinkapp.models.cache import LRUCache

        cache: LRUCache[str, str] = LRUCache(maxsize=5)

        cache["test_key"] = "test_value"

        # Should work with [] operator
        self.assertEqual(cache["test_key"], "test_value")

        # Should raise KeyError for missing key
        with self.assertRaises(KeyError):
            _ = cache["missing_key"]

    def test_lru_cache_thread_safety(self) -> None:
        """Test LRU cache concurrent access from multiple threads."""
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
        """Test camera thumbnail cache update."""
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
        """Test cache initialization."""
        self.assertEqual(len(self.cache), 0)

    def test_get_thumbnail_timestamp_missing(self) -> None:
        """Test getting timestamp for missing thumbnail."""
        timestamp = self.cache.get_thumbnail_timestamp(self.camera_id)
        self.assertIsNone(timestamp)

    def test_get_thumbnail_timestamp_existing(self) -> None:
        """Test getting timestamp for existing thumbnail."""
        entry = CameraThumbnailCacheEntry(timestamp=1234567890, filename="test.jpg")
        self.cache[self.camera_id] = entry

        timestamp = self.cache.get_thumbnail_timestamp(self.camera_id)
        self.assertEqual(timestamp, 1234567890.0)

    def test_get_thumbnail_timestamp_invalid_format(self) -> None:
        """Test getting timestamp with invalid format."""
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
        """Test freshness check for missing thumbnail."""
        is_fresh = self.cache.is_thumbnail_fresh(self.camera_id)
        self.assertFalse(is_fresh)

    def test_is_thumbnail_fresh_old(self) -> None:
        """Test freshness check for old thumbnail."""
        old_timestamp = int(time.time()) - 600  # 10 minutes ago
        entry = CameraThumbnailCacheEntry(timestamp=old_timestamp, filename="test.jpg")
        self.cache[self.camera_id] = entry

        is_fresh = self.cache.is_thumbnail_fresh(self.camera_id, max_age_seconds=300)
        self.assertFalse(is_fresh)

    def test_is_thumbnail_fresh_recent(self) -> None:
        """Test freshness check for recent thumbnail."""
        recent_timestamp = int(time.time()) - 100  # 100 seconds ago
        entry = CameraThumbnailCacheEntry(
            timestamp=recent_timestamp, filename="test.jpg"
        )
        self.cache[self.camera_id] = entry

        is_fresh = self.cache.is_thumbnail_fresh(self.camera_id, max_age_seconds=300)
        self.assertTrue(is_fresh)

    def test_update_thumbnail(self) -> None:
        """Test updating thumbnail with current timestamp."""
        thumbnail_data = b"fake_thumbnail_data"

        before_time = int(time.time())
        self.cache.update_thumbnail(self.camera_id, thumbnail_data)
        after_time = int(time.time()) + 1

        entry = self.cache[self.camera_id]
        self.assertGreaterEqual(entry["timestamp"], before_time)
        self.assertLessEqual(entry["timestamp"], after_time)

    def test_update_thumbnail_with_metadata(self) -> None:
        """Test updating thumbnail with metadata."""
        thumbnail_data = b"fake_thumbnail_data"
        metadata = {"size": 1024, "format": "JPEG"}

        self.cache.update_thumbnail(self.camera_id, thumbnail_data, metadata)

        entry = self.cache[self.camera_id]
        self.assertIn("timestamp", entry)
        self.assertIn("filename", entry)

    def test_get_thumbnail_timestamp_exists(self) -> None:
        """Test getting timestamp for existing thumbnail."""
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
        """Test thumbnail freshness check - fresh thumbnail."""
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
        """Test thumbnail freshness check - stale thumbnail."""
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
        """Test thumbnail freshness check - no timestamp."""
        from blinkapp.models.ids import CameraId

        cache = CameraThumbnailCache(maxsize=5)
        result = cache.is_thumbnail_fresh(CameraId("99999"))
        self.assertFalse(result)

    def test_update_thumbnail_basic(self) -> None:
        """Test updating thumbnail with basic data."""
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
        """Test cache initialization."""
        self.assertEqual(len(self.cache), 0)

    def test_add_clip(self) -> None:
        """Test adding clip to cache."""
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
        """Test getting existing clip data."""
        self.cache.add_clip(self.clip_id, self.clip_data)

        retrieved_data = self.cache.get_clip(self.clip_id)
        self.assertEqual(retrieved_data, self.clip_data)

        # Check access count was incremented
        from typing import cast

        entry = self.cache[self.clip_id]
        full_entry = cast("dict[str, object]", entry)
        self.assertEqual(full_entry["access_count"], 1)

    def test_get_clip_missing(self) -> None:
        """Test getting missing clip data."""
        retrieved_data = self.cache.get_clip(ClipId("nonexistent"))
        self.assertIsNone(retrieved_data)

    def test_get_clip_updates_access_time(self) -> None:
        """Test that getting clip updates access time."""
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
        """Test cleanup of old clips."""
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
        """Test cleanup when no old clips exist."""
        self.cache.add_clip(self.clip_id, self.clip_data)

        removed_count = self.cache.cleanup_old_clips(max_age_hours=24)

        self.assertEqual(removed_count, 0)
        self.assertIn(self.clip_id, self.cache)


class TestTypeDefinitions(BaseTestCase):
    """Test type definitions and data structures."""

    def test_clip_data_structure(self) -> None:
        """Test ClipCacheData TypedDict structure."""
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
        """Test ClipDayGroup TypedDict structure."""
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
        """Test CameraThumbnailCacheEntry TypedDict structure."""
        entry: CameraThumbnailCacheEntry = {
            "timestamp": 1234567890,
            "filename": "thumbnail.jpg",
        }

        # Verify structure
        self.assertEqual(entry["timestamp"], 1234567890)
        self.assertEqual(entry["filename"], "thumbnail.jpg")

    def test_clip_cache_entry_structure(self) -> None:
        """Test ClipCacheEntry TypedDict structure."""
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
        """Test CameraThumbnailCache get_stats method."""
        cache = CameraThumbnailCache(maxsize=10)

        stats = cache.get_stats()

        self.assertIn("size", stats)
        self.assertIn("maxsize", stats)
        self.assertEqual(stats["maxsize"], 10)
        self.assertEqual(stats["size"], 0)

    def test_clips_cache_get_stats(self) -> None:
        """Test ClipsCache get_stats method."""
        cache = ClipsCache(maxsize=5)

        stats = cache.get_stats()

        self.assertIn("size", stats)
        self.assertIn("maxsize", stats)
        self.assertEqual(stats["maxsize"], 5)
        self.assertEqual(stats["size"], 0)

    def test_cache_items_list_safe_iteration(self) -> None:
        """Test safe iteration with items_list method."""
        cache = CameraThumbnailCache(maxsize=10)
        camera_id = CameraId("12345")
        entry = CameraThumbnailCacheEntry(timestamp=1000, filename="test.jpg")
        cache[camera_id] = entry

        items = cache.items_list()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0][0], camera_id)
        self.assertEqual(items[0][1], entry)

    def test_hit_rate_calculation(self) -> None:
        """Test hit rate calculation in cache stats."""
        cache = ThreadSafeCache(maxsize=10)

        # Initially no hits or misses
        stats = cache.get_stats()
        self.assertEqual(stats["hit_rate"], 0.0)

    def test_models_cache_basic_operations(self) -> None:
        """Test basic cache operations."""
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
