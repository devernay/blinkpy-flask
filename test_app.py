#!/usr/bin/env python3
"""Unit tests for Blink Flask application.

Comprehensive test suite covering core functionality including:
- ID validation classes
- API endpoints
- Cache operations
- Error handling
- Authentication flow
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from app import (
    BaseId,
    CameraId,
    ClipId,
    Config,
    NetworkId,
    app,
    create_api_response,
    extract_thumbnail_timestamp,
    format_time_ago,
    validate_string_input,
)


class TestBaseId(unittest.TestCase):
    """Test BaseId base class functionality."""

    def setUp(self):
        """Set up test fixtures."""

        class TestId(BaseId):
            def _get_pattern(self):
                return r"^[a-zA-Z0-9]+$"

            def _get_type_name(self):
                return "Test ID"

        self.TestId = TestId

    def test_valid_id(self):
        """Test valid ID creation."""
        test_id = self.TestId("test123")
        self.assertEqual(str(test_id), "test123")
        self.assertEqual(test_id.value, "test123")

    def test_empty_id_raises_error(self):
        """Test empty ID raises ValueError."""
        with self.assertRaises(ValueError) as cm:
            self.TestId("")
        self.assertIn("cannot be empty", str(cm.exception))

    def test_invalid_pattern_raises_error(self):
        """Test invalid pattern raises ValueError."""
        with self.assertRaises(ValueError) as cm:
            self.TestId("test-invalid!")
        self.assertIn("Invalid Test ID format", str(cm.exception))

    def test_equality(self):
        """Test ID equality comparison."""
        id1 = self.TestId("test123")
        id2 = self.TestId("test123")
        id3 = self.TestId("test456")

        self.assertEqual(id1, id2)
        self.assertNotEqual(id1, id3)

    def test_hash(self):
        """Test ID hashing for use in sets/dicts."""
        id1 = self.TestId("test123")
        id2 = self.TestId("test123")

        self.assertEqual(hash(id1), hash(id2))
        self.assertEqual(len({id1, id2}), 1)  # Should be same in set


class TestCameraId(unittest.TestCase):
    """Test CameraId validation."""

    def test_valid_camera_id(self):
        """Test valid camera ID."""
        camera_id = CameraId("camera123")
        self.assertEqual(str(camera_id), "camera123")

    def test_camera_id_with_underscore(self):
        """Test camera ID with underscore."""
        camera_id = CameraId("camera_123")
        self.assertEqual(str(camera_id), "camera_123")


class TestNetworkId(unittest.TestCase):
    """Test NetworkId validation."""

    def test_valid_network_id(self):
        """Test valid network ID."""
        network_id = NetworkId("12345")
        self.assertEqual(str(network_id), "12345")

    def test_invalid_network_id(self):
        """Test invalid network ID with letters."""
        with self.assertRaises(ValueError):
            NetworkId("abc123")


class TestClipId(unittest.TestCase):
    """Test ClipId validation and local clip handling."""

    def test_cloud_clip_id(self):
        """Test cloud clip ID."""
        clip_id = ClipId("123456")
        self.assertEqual(str(clip_id), "123456")
        self.assertFalse(clip_id.is_local())

    def test_local_clip_id(self):
        """Test local clip ID."""
        clip_id = ClipId("sync1~789")
        self.assertEqual(str(clip_id), "sync1~789")
        self.assertTrue(clip_id.is_local())

    def test_from_local_constructor(self):
        """Test ClipId.from_local constructor."""
        clip_id = ClipId.from_local("sync_module", 123)
        self.assertEqual(str(clip_id), "sync_module~123")
        self.assertTrue(clip_id.is_local())

    def test_get_local_parts(self):
        """Test extracting local clip parts."""
        clip_id = ClipId("sync1~456")
        sync_name, item_id = clip_id.get_local_parts()
        self.assertEqual(sync_name, "sync1")
        self.assertEqual(item_id, 456)

    def test_get_local_parts_cloud_clip_error(self):
        """Test get_local_parts raises error for cloud clips."""
        clip_id = ClipId("123456")
        with self.assertRaises(ValueError):
            clip_id.get_local_parts()


class TestValidation(unittest.TestCase):
    """Test input validation functions."""

    def test_validate_string_input_valid(self):
        """Test valid string input."""
        result = validate_string_input("test@example.com", 50, "Email")
        self.assertEqual(result, "test@example.com")

    def test_validate_string_input_strips_whitespace(self):
        """Test string input strips whitespace."""
        result = validate_string_input("  test  ", 50, "Field")
        self.assertEqual(result, "test")

    def test_validate_string_input_empty_error(self):
        """Test empty string raises error."""
        with self.assertRaises(ValueError) as cm:
            validate_string_input("", 50, "Field")
        self.assertIn("cannot be empty", str(cm.exception))

    def test_validate_string_input_too_long_error(self):
        """Test too long string raises error."""
        with self.assertRaises(ValueError) as cm:
            validate_string_input("x" * 51, 50, "Field")
        self.assertIn("too long", str(cm.exception))

    def test_validate_string_input_xss_prevention(self):
        """Test XSS prevention."""
        with self.assertRaises(ValueError) as cm:
            validate_string_input("<script>alert('xss')</script>", 50, "Field")
        self.assertIn("invalid characters", str(cm.exception))


class TestApiResponse(unittest.TestCase):
    """Test API response creation."""

    def test_success_response(self):
        """Test successful API response."""
        response, status_code = create_api_response(success=True, data={"test": "data"})

        self.assertTrue(response["success"])
        self.assertEqual(response["data"], {"test": "data"})
        self.assertIsNone(response["error"])
        self.assertEqual(status_code, 200)
        self.assertIn("timestamp", response)

    def test_error_response(self):
        """Test error API response."""
        response, status_code = create_api_response(
            success=False, error="Test error", status_code=400
        )

        self.assertFalse(response["success"])
        self.assertEqual(response["error"], "Test error")
        self.assertIsNone(response["data"])
        self.assertEqual(status_code, 400)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions."""

    def test_extract_thumbnail_timestamp_valid(self):
        """Test extracting timestamp from thumbnail URL."""
        url = "/api/v3/media/accounts/200995/networks/440889/lotus/148021/thumbnail/thumbnail.jpg?ts=1742459551&ext="
        timestamp = extract_thumbnail_timestamp(url)
        self.assertEqual(timestamp, 1742459551)

    def test_extract_thumbnail_timestamp_no_ts(self):
        """Test extracting timestamp from URL without ts parameter."""
        url = "/api/v3/media/thumbnail.jpg"
        timestamp = extract_thumbnail_timestamp(url)
        self.assertEqual(timestamp, 0)

    def test_extract_thumbnail_timestamp_none(self):
        """Test extracting timestamp from None URL."""
        timestamp = extract_thumbnail_timestamp(None)
        self.assertEqual(timestamp, 0)

    def test_format_time_ago_days(self):
        """Test formatting time ago for days."""
        from datetime import datetime, timedelta

        past_time = datetime.now() - timedelta(days=5)
        result = format_time_ago(past_time.isoformat())
        self.assertEqual(result, "5d ago")

    def test_format_time_ago_hours(self):
        """Test formatting time ago for hours."""
        from datetime import datetime, timedelta

        past_time = datetime.now() - timedelta(hours=3)
        result = format_time_ago(past_time.isoformat())
        self.assertEqual(result, "3h ago")

    def test_format_time_ago_none(self):
        """Test formatting time ago for None."""
        result = format_time_ago(None)
        self.assertEqual(result, "Unknown")


class TestFlaskApp(unittest.TestCase):
    """Test Flask application endpoints."""

    def setUp(self):
        """Set up test client."""
        app.config["TESTING"] = True
        app.config["CACHE_DIR"] = tempfile.mkdtemp()
        self.client = app.test_client()
        self.temp_dir = app.config["CACHE_DIR"]

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_index_redirect_to_login(self):
        """Test index redirects to login when not authenticated."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

    def test_login_page_get(self):
        """Test login page GET request."""
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Blink Camera System", response.data)

    def test_login_page_post_validation_error(self):
        """Test login POST with validation error."""
        response = self.client.post(
            "/login",
            data={
                "username": "",  # Empty username
                "password": "test",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"cannot be empty", response.data)

    def test_placeholder_endpoint(self):
        """Test placeholder endpoint."""
        response = self.client.get("/placeholder")
        self.assertEqual(response.status_code, 501)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("not yet available", data["error"])

    @patch("app.blink", None)
    def test_api_systems_no_blink(self):
        """Test systems API when Blink not available."""
        response = self.client.get("/api/system/list")
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("not initialized", data["error"])

    @patch("app.blink")
    @patch("app.blink_connection")
    def test_api_systems_success(self, mock_connection, mock_blink):
        """Test successful systems API call."""
        # Mock Blink system
        mock_sync = Mock()
        mock_sync.network_id = 12345
        mock_sync.arm = False
        mock_sync.online = True

        mock_blink.available = True
        mock_blink.sync = {"Test System": mock_sync}

        response = self.client.get("/api/system/list")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 1)
        self.assertEqual(data["data"][0]["name"], "Test System")

    def test_api_devices_invalid_network_id(self):
        """Test devices API with invalid network ID."""
        response = self.client.get("/api/system/invalid_id/devices")
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("Invalid Network ID format", data["error"])


class TestCacheOperations(unittest.TestCase):
    """Test cache-related operations."""

    def setUp(self):
        """Set up test fixtures."""
        from cachetools import LRUCache

        from app import ThreadSafeCache

        self.cache = ThreadSafeCache(LRUCache(maxsize=10))

    def test_cache_set_get(self):
        """Test cache set and get operations."""
        self.cache["key1"] = "value1"
        self.assertEqual(self.cache.get("key1"), "value1")

    def test_cache_get_default(self):
        """Test cache get with default value."""
        result = self.cache.get("nonexistent", "default")
        self.assertEqual(result, "default")

    def test_cache_contains(self):
        """Test cache contains operation."""
        self.cache["key1"] = "value1"
        self.assertIn("key1", self.cache)
        self.assertNotIn("key2", self.cache)

    def test_cache_pop(self):
        """Test cache pop operation."""
        self.cache["key1"] = "value1"
        result = self.cache.pop("key1")
        self.assertEqual(result, "value1")
        self.assertNotIn("key1", self.cache)

    def test_cache_clear(self):
        """Test cache clear operation."""
        self.cache["key1"] = "value1"
        self.cache["key2"] = "value2"
        self.cache.clear()
        self.assertEqual(len(self.cache), 0)


class TestErrorHandling(unittest.TestCase):
    """Test error handling mechanisms."""

    def test_error_context_manager(self):
        """Test error context manager."""
        from app import BlinkError, error_context

        with self.assertRaises(BlinkError):
            with error_context("test operation"):
                raise ValueError("Test error")

    def test_safe_execute_success(self):
        """Test safe_execute with successful function."""
        from app import safe_execute

        def success_func():
            return "success"

        result = safe_execute(success_func, "default")
        self.assertEqual(result, "success")

    def test_safe_execute_failure(self):
        """Test safe_execute with failing function."""
        from app import safe_execute

        def fail_func():
            raise ValueError("Test error")

        result = safe_execute(fail_func, "default", log_error=False)
        self.assertEqual(result, "default")


class TestConfig(unittest.TestCase):
    """Test configuration constants."""

    def test_config_constants_exist(self):
        """Test that all expected config constants exist."""
        required_constants = [
            "CLIPS_CACHE_SIZE",
            "THUMBNAIL_CACHE_SIZE",
            "HTTP_TIMEOUT",
            "DOWNLOAD_TIMEOUT",
            "FFMPEG_TIMEOUT",
            "MAX_USERNAME_LENGTH",
            "VALID_CAMERA_ID_PATTERN",
            "DEFAULT_SYSTEM_NAME",
        ]

        for constant in required_constants:
            self.assertTrue(hasattr(Config, constant))
            self.assertIsNotNone(getattr(Config, constant))

    def test_config_values_reasonable(self):
        """Test that config values are reasonable."""
        self.assertGreater(Config.CLIPS_CACHE_SIZE, 0)
        self.assertGreater(Config.HTTP_TIMEOUT, 0)
        self.assertGreater(Config.MAX_USERNAME_LENGTH, 10)
        self.assertIsInstance(Config.DEFAULT_SYSTEM_NAME, str)


if __name__ == "__main__":
    # Create test suite
    test_suite = unittest.TestSuite()

    # Add test classes
    test_classes = [
        TestBaseId,
        TestCameraId,
        TestNetworkId,
        TestClipId,
        TestValidation,
        TestApiResponse,
        TestUtilityFunctions,
        TestFlaskApp,
        TestCacheOperations,
        TestErrorHandling,
        TestConfig,
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
