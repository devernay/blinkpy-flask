"""Comprehensive tests for clip_processing.py to achieve near 100% coverage."""

from unittest.mock import Mock, patch

import pytest

from blinkapp.models.ids import ClipId
from blinkapp.services import clip_processing


class TestProcessCloudClipBackground:
    """Test process_cloud_clip_background function."""

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    def test_process_cloud_clip_background_thumbnail_exists(self, mock_exists):
        """Test when thumbnail already exists."""
        mock_exists.return_value = True

        # Should return early without processing
        clip_processing.process_cloud_clip_background(ClipId("test_clip"))

        mock_exists.assert_called_once()

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    def test_process_cloud_clip_background_blink_error(self, mock_ensure, mock_exists):
        """Test when blink initialization fails."""
        mock_exists.return_value = False
        mock_ensure.side_effect = RuntimeError("Blink not available")

        # Should handle error gracefully
        clip_processing.process_cloud_clip_background(ClipId("test_clip"))

        mock_ensure.assert_called_once()

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    def test_process_cloud_clip_background_blink_unavailable(
        self, mock_ensure, mock_exists
    ):
        """Test when blink instance is unavailable."""
        mock_exists.return_value = False
        mock_blink = Mock()
        mock_blink.available = False
        mock_ensure.return_value = mock_blink

        # Should return early
        clip_processing.process_cloud_clip_background(ClipId("test_clip"))

        mock_ensure.assert_called_once()


class TestProcessLocalClipBackground:
    """Test process_local_clip_background function."""

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    def test_process_local_clip_background_thumbnail_exists(self, mock_exists):
        """Test when thumbnail already exists."""
        mock_exists.return_value = True

        # Should return early without processing
        clip_processing.process_local_clip_background(
            ClipId("test_clip"), "sync_name", "filename.mp4"
        )

        mock_exists.assert_called_once()

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    def test_process_local_clip_background_blink_error(self, mock_ensure, mock_exists):
        """Test when blink initialization fails."""
        mock_exists.return_value = False
        mock_ensure.side_effect = RuntimeError("Blink not available")

        # Should handle error gracefully
        clip_processing.process_local_clip_background(
            ClipId("test_clip"), "sync_name", "filename.mp4"
        )

        mock_ensure.assert_called_once()


class TestDownloadAndCacheCloudThumbnail:
    """Test download_and_cache_cloud_thumbnail function."""

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    def test_download_and_cache_cloud_thumbnail_local_clip_error(self):
        """Test with local clip ID raises error."""
        # Create a mock local clip ID
        mock_clip_id = Mock()
        mock_clip_id.is_local.return_value = True

        with pytest.raises(
            ValueError, match="download_and_cache_cloud_thumbnail called on local clip"
        ):
            clip_processing.download_and_cache_cloud_thumbnail(
                mock_clip_id, "http://test.url"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    def test_download_and_cache_cloud_thumbnail_already_exists(self, mock_exists):
        """Test when thumbnail already exists."""
        mock_exists.return_value = True

        # Create a mock cloud clip ID
        mock_clip_id = Mock()
        mock_clip_id.is_local.return_value = False
        mock_clip_id.__str__ = Mock(return_value="test_clip")

        result = clip_processing.download_and_cache_cloud_thumbnail(
            mock_clip_id, "http://test.url"
        )

        assert result is not None  # Returns existing path

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("requests.get")
    def test_download_and_cache_cloud_thumbnail_request_error(
        self, mock_get, mock_exists
    ):
        """Test request error handling."""
        mock_exists.return_value = False
        mock_get.side_effect = Exception("Network error")

        # Create a mock cloud clip ID
        mock_clip_id = Mock()
        mock_clip_id.is_local.return_value = False
        mock_clip_id.__str__ = Mock(return_value="test_clip")

        result = clip_processing.download_and_cache_cloud_thumbnail(
            mock_clip_id, "http://test.url"
        )

        assert result is None
