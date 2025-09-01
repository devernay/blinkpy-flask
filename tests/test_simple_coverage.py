"""Simple tests to improve coverage without complex mocking."""

from .test_base import BaseTestCase


class TestSimpleCoverage(BaseTestCase):
    """Simple coverage improvement tests."""

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

    def test_models_ids_string_methods(self) -> None:
        """Test ID model string methods."""
        from blinkapp.models.ids import CameraId, ClipId, NetworkId

        # Test CameraId
        camera_id = CameraId("test_camera")
        self.assertEqual(str(camera_id), "test_camera")
        self.assertEqual(repr(camera_id), "CameraId('test_camera')")

        # Test NetworkId
        network_id = NetworkId("12345")
        self.assertEqual(str(network_id), "12345")

        # Test ClipId
        clip_id = ClipId("test_clip")
        self.assertEqual(str(clip_id), "test_clip")

    def test_decorators_basic_usage(self) -> None:
        """Test basic decorator usage."""
        from blinkapp.utils.decorators import error_context

        @error_context("test operation")
        def simple_test_function() -> str:
            return "success"

        result = simple_test_function()
        self.assertEqual(result, "success")

    def test_connection_service_basic(self) -> None:
        """Test basic connection service."""
        from blinkapp.services.blink_connection import get_blink_connection

        # Should return None when not initialized
        result = get_blink_connection()
        self.assertIsNone(result)

    def test_cache_service_stats(self) -> None:
        """Test cache service stats."""
        from blinkapp.services.cache_service import get_cache_stats

        stats = get_cache_stats()
        self.assertIsInstance(stats, dict)


if __name__ == "__main__":
    import unittest

    unittest.main()
