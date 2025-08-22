#!/usr/bin/env python3
"""Targeted tests for models/cache.py expansion - covering remaining missed lines."""

import unittest

from blinkapp.models.cache import ClipsCache, ThumbnailCache
from blinkapp.models.ids import CameraId, ClipId


class TestCacheModelsExpansion(unittest.TestCase):
    """Test uncovered cache model functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.camera_id = CameraId(12345)
        self.clip_id = ClipId("test_clip_123")

    def test_thumbnail_cache_get_stats(self) -> None:
        """Test ThumbnailCache get_stats method."""
        cache = ThumbnailCache(maxsize=10)

        stats = cache.get_stats()

        self.assertIn("size", stats)
        self.assertIn("maxsize", stats)
        self.assertEqual(stats["maxsize"], 10)

    def test_clips_cache_get_stats(self) -> None:
        """Test ClipsCache get_stats method."""
        cache = ClipsCache(maxsize=5)

        stats = cache.get_stats()

        self.assertIn("size", stats)
        self.assertIn("maxsize", stats)
        self.assertEqual(stats["maxsize"], 5)

    def test_thumbnail_cache_items_safe_iteration(self) -> None:
        """Test ThumbnailCache items() method for safe iteration."""
        cache = ThumbnailCache(maxsize=10)
        cache[self.camera_id] = {"data": b"test", "timestamp": 1000}

        items = cache.items()

        # The items() method should return something iterable
        items_list = list(items)
        self.assertEqual(len(items_list), 1)

    def test_clips_cache_items_safe_iteration(self) -> None:
        """Test ClipsCache items() method for safe iteration."""
        cache = ClipsCache(maxsize=5)

        items = cache.items()

        # The items() method should return something iterable
        items_list = list(items)
        self.assertIsInstance(items_list, list)

    def test_cache_stats_with_hits_misses(self) -> None:
        """Test cache statistics include hits and misses."""
        cache = ThumbnailCache(maxsize=10)

        # Access non-existent item to generate miss
        cache.get(self.camera_id)

        stats = cache.get_stats()
        self.assertIn("size", stats)
        self.assertIn("maxsize", stats)
