"""Tests for clip_service module."""

from unittest.mock import patch

from test_base import BaseTestCase

from blinkapp.models.ids import ClipId


class TestClipService(BaseTestCase):
    """Test clip service functions."""

    def test_process_cloud_clips_basic(self):
        """Test process_cloud_clips with basic input."""
        from blinkapp.services.clip_service import process_cloud_clips

        videos_metadata = [
            {"id": "123", "name": "test.mp4", "size": 1024},
            {"id": "456", "name": "test2.mp4", "size": 2048},
        ]

        result = process_cloud_clips(videos_metadata)
        self.assertIsInstance(result, list)

    def test_process_cloud_clips_empty(self):
        """Test process_cloud_clips with empty input."""
        from blinkapp.services.clip_service import process_cloud_clips

        result = process_cloud_clips([])
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @patch("blinkapp.services.clip_service.get_blink_connection")
    def test_process_local_clips_no_connection(self, mock_conn):
        """Test process_local_clips without connection."""
        from blinkapp.services.clip_service import process_local_clips

        mock_conn.return_value = None

        with self.assertRaises(AssertionError):
            process_local_clips()

    def test_download_cloud_clip_basic(self):
        """Test download_cloud_clip basic functionality."""
        from blinkapp.services.clip_service import download_cloud_clip

        clip_id = ClipId("test_clip")

        with patch(
            "blinkapp.services.clip_service.get_blink_connection", return_value=None
        ):
            result = download_cloud_clip(clip_id)
            self.assertIsInstance(result, (dict, tuple))

    def test_download_local_clip_basic(self):
        """Test download_local_clip basic functionality."""
        from blinkapp.services.clip_service import download_local_clip

        clip_id = ClipId("test_clip")

        result = download_local_clip(clip_id, "sync_name", 123)
        self.assertIsInstance(result, (dict, tuple))

    def test_process_cloud_clip_background_basic(self):
        """Test process_cloud_clip_background basic functionality."""
        from blinkapp.services.clip_service import process_cloud_clip_background

        clip_id = ClipId("test_clip")

        # Should not raise exception
        process_cloud_clip_background(clip_id)

    def test_process_local_clip_background_basic(self):
        """Test process_local_clip_background basic functionality."""
        from blinkapp.services.clip_service import process_local_clip_background

        clip_id = ClipId("test_clip")

        # Should not raise exception
        process_local_clip_background(clip_id, "sync_name", 123)


if __name__ == "__main__":
    import unittest

    unittest.main()
