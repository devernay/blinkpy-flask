"""Comprehensive unit tests for all model classes and functions.

Complete test suite covering all classes and functions in blinkapp/models/:
- ID validation classes (BaseId, CameraId, NetworkId, ClipId)
- Cache classes (ThreadSafeCache, ThreadSafeLRUCache, CameraThumbnailCache, ClipsCache)
- Response utilities (create_api_response)
- Type definitions and data structures
"""

import threading
import time
import unittest

from blinkapp.models.cache import (
    CameraThumbnailCache,
    CameraThumbnailCacheEntry,
    ClipCacheEntry,
    ClipData,
    ClipsCache,
    ThreadSafeCache,
    ThreadSafeLRUCache,
)
from blinkapp.models.ids import BaseId, CameraId, ClipId, NetworkId
from blinkapp.models.responses import create_api_response
from blinkapp.models.types import ClipDayGroup
from tests.test_base import BaseTestCase


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
        """Test valid ID creation and string representation."""
        test_id = self.TestId("test123")
        self.assertEqual(str(test_id), "test123")
        self.assertEqual(test_id.value, "test123")

    def test_numeric_id_conversion(self) -> None:
        """Test numeric ID conversion to string."""
        test_id = self.TestId(12345)
        self.assertEqual(str(test_id), "12345")
        self.assertEqual(test_id.value, "12345")

    def test_empty_id_raises_error(self) -> None:
        """Test empty ID raises ValueError."""
        with self.assertRaises(ValueError) as cm:
            self.TestId("")
        self.assertIn("cannot be empty", str(cm.exception))

    def test_whitespace_id_raises_error(self) -> None:
        """Test whitespace-only ID raises ValueError."""
        with self.assertRaises(ValueError) as cm:
            self.TestId("   ")
        self.assertIn("cannot be empty", str(cm.exception))

    def test_invalid_pattern_raises_error(self) -> None:
        """Test invalid pattern raises ValueError."""
        with self.assertRaises(ValueError) as cm:
            self.TestId("test-invalid!")
        self.assertIn("Invalid Test ID format", str(cm.exception))

    def test_equality_with_same_id(self) -> None:
        """Test ID equality with same value."""
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
        """Test ID hashing consistency."""
        id1 = self.TestId("test123")
        id2 = self.TestId("test123")
        self.assertEqual(hash(id1), hash(id2))

    def test_hash_in_set(self) -> None:
        """Test ID hashing in sets."""
        id1 = self.TestId("test123")
        id2 = self.TestId("test123")
        id_set = {id1, id2}
        self.assertEqual(len(id_set), 1)

    def test_repr_format(self) -> None:
        """Test string representation format."""
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

    def test_empty_id(self) -> None:
        """Test empty camera ID raises error."""
        with self.assertRaises(ValueError):
            CameraId("")

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
        clip_id = ClipId.from_cloud(456)
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
        # Create entry with invalid timestamp format
        self.cache[self.camera_id] = {"timestamp": "invalid", "filename": "test.jpg"}

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


class TestClipsCache(BaseTestCase):
    """Test ClipsCache functionality."""

    def setUp(self) -> None:
        """Set up test clips cache."""
        self.cache = ClipsCache(maxsize=3)
        self.clip_id = ClipId("clip123")
        self.clip_data: ClipData = {
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
        before_time = time.time()
        self.cache.add_clip(self.clip_id, self.clip_data)
        after_time = time.time()

        entry = self.cache[self.clip_id]
        self.assertEqual(entry["clip_data"], self.clip_data)
        self.assertGreaterEqual(entry["cached_at"], before_time)
        self.assertLessEqual(entry["cached_at"], after_time)
        self.assertEqual(entry["access_count"], 0)

    def test_get_clip_existing(self) -> None:
        """Test getting existing clip data."""
        self.cache.add_clip(self.clip_id, self.clip_data)

        retrieved_data = self.cache.get_clip(self.clip_id)
        self.assertEqual(retrieved_data, self.clip_data)

        # Check access count was incremented
        entry = self.cache[self.clip_id]
        self.assertEqual(entry["access_count"], 1)

    def test_get_clip_missing(self) -> None:
        """Test getting missing clip data."""
        retrieved_data = self.cache.get_clip(ClipId("nonexistent"))
        self.assertIsNone(retrieved_data)

    def test_get_clip_updates_access_time(self) -> None:
        """Test that getting clip updates access time."""
        self.cache.add_clip(self.clip_id, self.clip_data)

        # Get initial access time
        initial_entry = self.cache[self.clip_id]
        initial_access_time = initial_entry["last_accessed"]

        # Wait a bit and access again
        time.sleep(0.01)
        self.cache.get_clip(self.clip_id)

        # Check access time was updated
        updated_entry = self.cache[self.clip_id]
        self.assertGreater(updated_entry["last_accessed"], initial_access_time)

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
        """Test ClipData TypedDict structure."""
        clip_data: ClipData = {
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
        from blinkapp.models.types import ClipData as TypesClipData

        clip_data: TypesClipData = {
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
        clip_data: ClipData = {
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


if __name__ == "__main__":
    unittest.main()
