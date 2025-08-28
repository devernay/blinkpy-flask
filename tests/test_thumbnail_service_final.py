#!/usr/bin/env python3
"""Final targeted tests for thumbnail_service.py - covering remaining missed lines."""

import unittest
from unittest.mock import Mock, patch

from blinkapp.models.cache import CameraThumbnailCache
from blinkapp.services.thumbnail_service import get_camera_thumbnail_cache_stats


class TestThumbnailServiceFinal(unittest.TestCase):
    """Test remaining uncovered thumbnail service functions."""

    @patch("blinkapp.services.cache_service.ensure_camera_thumbnail_cache_initialized")
    def test_get_camera_thumbnail_cache_stats_success(
        self, mock_ensure_cache: Mock
    ) -> None:
        """Test get_camera_thumbnail_cache_stats successful execution."""
        mock_cache = Mock(spec=CameraThumbnailCache)
        mock_cache.__len__ = Mock(return_value=10)
        mock_cache.max_size = 100
        mock_cache.hit_rate = 0.85
        mock_ensure_cache.return_value = mock_cache

        result = get_camera_thumbnail_cache_stats()

        self.assertEqual(result["size"], 10)
        self.assertEqual(result["max_size"], 100)
        self.assertEqual(result["hit_rate"], 0.85)

    @patch("blinkapp.services.cache_service.ensure_camera_thumbnail_cache_initialized")
    @patch("blinkapp.services.thumbnail_service.logger")
    def test_get_camera_thumbnail_cache_stats_exception(
        self, mock_logger: Mock, mock_ensure_cache: Mock
    ) -> None:
        """Test get_camera_thumbnail_cache_stats exception handling."""
        mock_ensure_cache.side_effect = Exception("Cache error")

        result = get_camera_thumbnail_cache_stats()

        self.assertIn("error", result)
        self.assertEqual(result["error"], "Cache error")
        mock_logger.error.assert_called_once()

    @patch("blinkapp.services.cache_service.ensure_camera_thumbnail_cache_initialized")
    def test_get_camera_thumbnail_cache_stats_missing_attributes(
        self, mock_ensure_cache: Mock
    ) -> None:
        """Test get_camera_thumbnail_cache_stats with missing cache attributes."""
        mock_cache = Mock(spec=CameraThumbnailCache)
        mock_cache.__len__ = Mock(return_value=5)
        # Don't set max_size or hit_rate attributes
        del mock_cache.max_size
        del mock_cache.hit_rate
        mock_ensure_cache.return_value = mock_cache

        result = get_camera_thumbnail_cache_stats()

        self.assertEqual(result["size"], 5)
        self.assertEqual(result["max_size"], "unknown")
        self.assertEqual(result["hit_rate"], "unknown")
