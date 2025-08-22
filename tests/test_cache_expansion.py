#!/usr/bin/env python3
"""Targeted tests for cache.py expansion - focusing on uncovered methods."""

import time
import unittest

from blinkapp.models.cache import ThumbnailCache
from blinkapp.models.ids import CameraId


class TestThumbnailCacheExpansion(unittest.TestCase):
    """Test uncovered ThumbnailCache methods."""

    def setUp(self) -> None:
        """Set up test cache."""
        self.cache = ThumbnailCache(maxsize=5)
        self.camera_id = CameraId(12345)

    def test_get_thumbnail_timestamp_exists(self) -> None:
        """Test getting timestamp for existing thumbnail."""
        timestamp = time.time()
        # Use the correct method name
        self.cache[self.camera_id] = {"data": b"test_data", "timestamp": timestamp}

        result = self.cache.get_thumbnail_timestamp(self.camera_id)
        self.assertEqual(result, timestamp)

    def test_get_thumbnail_timestamp_missing(self) -> None:
        """Test getting timestamp for non-existent thumbnail."""
        result = self.cache.get_thumbnail_timestamp(CameraId(99999))
        self.assertIsNone(result)

    def test_get_thumbnail_timestamp_no_timestamp(self) -> None:
        """Test getting timestamp when thumbnail has no timestamp."""
        self.cache[self.camera_id] = {"data": b"test_data"}

        result = self.cache.get_thumbnail_timestamp(self.camera_id)
        self.assertIsNone(result)

    def test_is_thumbnail_fresh_true(self) -> None:
        """Test thumbnail freshness check - fresh thumbnail."""
        current_time = time.time()
        self.cache[self.camera_id] = {
            "data": b"test_data",
            "timestamp": current_time - 100,  # 100 seconds ago
        }

        result = self.cache.is_thumbnail_fresh(self.camera_id, max_age_seconds=300)
        self.assertTrue(result)

    def test_is_thumbnail_fresh_false(self) -> None:
        """Test thumbnail freshness check - stale thumbnail."""
        current_time = time.time()
        self.cache[self.camera_id] = {
            "data": b"test_data",
            "timestamp": current_time - 400,  # 400 seconds ago
        }

        result = self.cache.is_thumbnail_fresh(self.camera_id, max_age_seconds=300)
        self.assertFalse(result)

    def test_is_thumbnail_fresh_no_timestamp(self) -> None:
        """Test thumbnail freshness check - no timestamp."""
        self.cache[self.camera_id] = {"data": b"test_data"}

        result = self.cache.is_thumbnail_fresh(self.camera_id)
        self.assertFalse(result)

    def test_update_thumbnail_basic(self) -> None:
        """Test updating thumbnail with basic data."""
        thumbnail_data = b"new_thumbnail_data"

        self.cache.update_thumbnail(self.camera_id, thumbnail_data)

        result = self.cache.get(self.camera_id)
        self.assertIsNotNone(result)
        if result:  # Type guard for pyright
            self.assertEqual(result["data"], thumbnail_data)
            self.assertIn("timestamp", result)

    def test_update_thumbnail_with_metadata(self) -> None:
        """Test updating thumbnail with metadata."""
        thumbnail_data = b"new_thumbnail_data"
        metadata = {"width": 640, "height": 480}

        self.cache.update_thumbnail(self.camera_id, thumbnail_data, metadata)

        result = self.cache.get(self.camera_id)
        self.assertIsNotNone(result)
        if result:  # Type guard for pyright
            self.assertEqual(result["data"], thumbnail_data)
            # Metadata should be merged into the cache entry
            self.assertIn("timestamp", result)
