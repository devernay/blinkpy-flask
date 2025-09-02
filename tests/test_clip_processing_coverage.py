"""Comprehensive tests for clip processing service to improve coverage.

Tests focus on background clip processing functions which are the main
uncovered areas in clip_processing.py.
"""

import unittest
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import requests

from blinkapp.models.ids import ClipId
from blinkapp.services.clip_processing import (
    download_and_cache_cloud_thumbnail,
    process_cloud_clip_background,
    process_cloud_clip_thumbnail_only,
    process_local_clip_background,
)
from tests.test_base import BaseTestCase


class TestCloudClipProcessing(BaseTestCase):
    """Test cloud clip processing functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()
        self.clip_id = ClipId("123456")
        self.clips_cache_dir = Path("/tmp/test_clips")

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    def test_process_cloud_clip_background_thumbnail_exists(
        self, mock_exists: Mock
    ) -> None:
        """Test cloud clip processing when thumbnail already exists."""
        mock_exists.return_value = True

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_cloud_clip_background(self.clip_id)

            mock_logger.debug.assert_called_with(
                f"Thumbnail already cached for clip {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.blink_service.blink", None)
    def test_process_cloud_clip_background_no_blink(self, mock_exists: Mock) -> None:
        """Test cloud clip processing when blink is not available."""
        mock_exists.return_value = False

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_cloud_clip_background(self.clip_id)

            mock_logger.warning.assert_called_with(
                f"Blink not available for processing clip {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.blink_service.blink")
    def test_process_cloud_clip_background_blink_unavailable(
        self, mock_blink: Mock, mock_exists: Mock
    ) -> None:
        """Test cloud clip processing when blink is unavailable."""
        mock_exists.return_value = False
        mock_blink.available = False

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_cloud_clip_background(self.clip_id)

            mock_logger.warning.assert_called_with(
                f"Blink not available for processing clip {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.clip_processing.ensure_clips_cache_initialized")
    def test_process_cloud_clip_background_no_media_url(
        self,
        mock_cache_init: Mock,
        mock_blink: Mock,
        mock_mkdir: Mock,
        mock_exists: Mock,
    ) -> None:
        """Test cloud clip processing when no media URL found."""
        mock_exists.side_effect = [False, False]  # thumbnail and clip don't exist
        mock_blink.available = True

        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache_init.return_value = mock_cache

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_cloud_clip_background(self.clip_id)

            mock_logger.error.assert_called_with(
                f"No media URL found for cloud clip {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.clip_processing.ensure_clips_cache_initialized")
    @patch("requests.get")
    @patch("builtins.open", new_callable=mock_open)
    @patch("blinkapp.services.clip_processing.process_cloud_clip_thumbnail_only")
    def test_process_cloud_clip_background_success(
        self,
        mock_thumbnail_proc: Mock,
        mock_file: Mock,
        mock_requests: Mock,
        mock_cache_init: Mock,
        mock_blink: Mock,
        mock_mkdir: Mock,
        mock_exists: Mock,
    ) -> None:
        """Test successful cloud clip processing."""
        mock_exists.side_effect = [
            False,
            False,
            True,
        ]  # thumbnail doesn't exist, clip doesn't exist, then thumbnail exists
        mock_blink.available = True

        # Mock cache with media URL
        mock_cache = Mock()
        cached_clip = {"media_url": "http://example.com/clip.mp4"}
        mock_cache.get.return_value = cached_clip
        mock_cache_init.return_value = mock_cache

        # Mock successful download
        mock_response = Mock()
        mock_response.content = b"video content"
        mock_requests.return_value = mock_response

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_cloud_clip_background(self.clip_id)

            mock_requests.assert_called_once()
            mock_file.assert_called_once()
            mock_thumbnail_proc.assert_called_once_with(self.clip_id)
            mock_logger.info.assert_called()

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.clip_processing.ensure_clips_cache_initialized")
    @patch("requests.get")
    def test_process_cloud_clip_background_download_error(
        self,
        mock_requests: Mock,
        mock_cache_init: Mock,
        mock_blink: Mock,
        mock_mkdir: Mock,
        mock_exists: Mock,
    ) -> None:
        """Test cloud clip processing with download error."""
        mock_exists.side_effect = [False, False]  # thumbnail and clip don't exist
        mock_blink.available = True

        # Mock cache with media URL
        mock_cache = Mock()
        cached_clip = {"media_url": "http://example.com/clip.mp4"}
        mock_cache.get.return_value = cached_clip
        mock_cache_init.return_value = mock_cache

        # Mock failed download
        mock_requests.side_effect = requests.RequestException("Network error")

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_cloud_clip_background(self.clip_id)

            mock_logger.error.assert_called()

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    def test_process_cloud_clip_background_exception(self) -> None:
        """Test cloud clip processing with general exception."""
        with patch("pathlib.Path.exists", side_effect=Exception("Filesystem error")):
            with patch("blinkapp.services.clip_processing.logger") as mock_logger:
                process_cloud_clip_background(self.clip_id)

                mock_logger.error.assert_called()


class TestLocalClipProcessing(BaseTestCase):
    """Test local clip processing functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()
        self.clip_id = ClipId.from_local("test_sync", 123456)
        self.sync_name = "test_sync"
        self.filename = "test_clip.mp4"

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    def test_process_local_clip_background_thumbnail_exists(
        self, mock_exists: Mock
    ) -> None:
        """Test local clip processing when thumbnail already exists."""
        mock_exists.return_value = True

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_local_clip_background(self.clip_id, self.sync_name, self.filename)

            mock_logger.debug.assert_called_with(
                f"Thumbnail already cached for local clip {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.blink_service.blink", None)
    def test_process_local_clip_background_no_blink(self, mock_exists: Mock) -> None:
        """Test local clip processing when blink is not available."""
        mock_exists.return_value = False

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_local_clip_background(self.clip_id, self.sync_name, self.filename)

            mock_logger.warning.assert_called_with(
                f"Blink not available for processing local clip {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.blink_service.blink")
    def test_process_local_clip_background_sync_not_found(
        self, mock_blink: Mock, mock_exists: Mock
    ) -> None:
        """Test local clip processing when sync module not found."""
        mock_exists.return_value = False
        mock_blink.available = True
        mock_blink.sync = {}  # Empty sync dict

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_local_clip_background(self.clip_id, self.sync_name, self.filename)

            mock_logger.error.assert_called_with(
                f"Sync module '{self.sync_name}' not found for clip {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.blink_service.blink")
    def test_process_local_clip_background_no_local_storage(
        self, mock_blink: Mock, mock_exists: Mock
    ) -> None:
        """Test local clip processing when no local storage available."""
        mock_exists.return_value = False
        mock_blink.available = True

        mock_sync = Mock()
        mock_sync.local_storage = None
        mock_blink.sync = {self.sync_name: mock_sync}

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_local_clip_background(self.clip_id, self.sync_name, self.filename)

            mock_logger.warning.assert_called_with(
                f"Local storage not available for clip {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("blinkapp.services.blink_service.blink")
    def test_process_local_clip_background_not_implemented(
        self, mock_blink: Mock, mock_mkdir: Mock, mock_exists: Mock
    ) -> None:
        """Test local clip processing - not fully implemented."""
        mock_exists.side_effect = [False, False]  # thumbnail and clip don't exist
        mock_blink.available = True

        mock_sync = Mock()
        mock_sync.local_storage = Mock()  # Has local storage
        mock_blink.sync = {self.sync_name: mock_sync}

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_local_clip_background(self.clip_id, self.sync_name, self.filename)

            mock_logger.warning.assert_any_call(
                f"Local clip processing not fully implemented for {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    def test_process_local_clip_background_exception(self) -> None:
        """Test local clip processing with general exception."""
        with patch("pathlib.Path.exists", side_effect=Exception("Filesystem error")):
            with patch("blinkapp.services.clip_processing.logger") as mock_logger:
                process_local_clip_background(
                    self.clip_id, self.sync_name, self.filename
                )

                mock_logger.error.assert_called()


class TestThumbnailDownload(BaseTestCase):
    """Test thumbnail download functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()
        self.clip_id = ClipId("123456")
        self.thumbnail_url = "http://example.com/thumbnail.jpg"

    def test_download_and_cache_cloud_thumbnail_local_clip_error(self) -> None:
        """Test download thumbnail with local clip raises error."""
        # Create a local clip ID that will return True for is_local()
        local_clip_id = ClipId.from_local("test_sync", 123456)

        with self.assertRaises(ValueError) as context:
            download_and_cache_cloud_thumbnail(local_clip_id, self.thumbnail_url)

        self.assertIn("called on local clip", str(context.exception))

    def test_download_and_cache_cloud_thumbnail_no_url(self) -> None:
        """Test download thumbnail with no URL."""
        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            result = download_and_cache_cloud_thumbnail(self.clip_id, "")

            self.assertIsNone(result)
            mock_logger.error.assert_called_with(
                f"No thumbnail URL provided for clip {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_download_and_cache_cloud_thumbnail_success(
        self, mock_file: Mock, mock_requests: Mock, mock_mkdir: Mock, mock_exists: Mock
    ) -> None:
        """Test successful thumbnail download."""
        mock_exists.return_value = False  # Thumbnail doesn't exist

        # Mock successful download
        mock_response = Mock()
        mock_response.content = b"thumbnail content"
        mock_requests.return_value = mock_response

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            result = download_and_cache_cloud_thumbnail(
                self.clip_id, self.thumbnail_url
            )

            self.assertIsNotNone(result)
            self.assertEqual(result.name, f"{self.clip_id}.jpg")
            mock_requests.assert_called_once_with(self.thumbnail_url, timeout=30)
            mock_file.assert_called_once()
            mock_logger.debug.assert_called_with(
                f"Downloaded thumbnail for clip {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    def test_download_and_cache_cloud_thumbnail_already_exists(
        self, mock_mkdir: Mock, mock_exists: Mock
    ) -> None:
        """Test thumbnail download when file already exists."""
        mock_exists.return_value = True  # Thumbnail exists

        result = download_and_cache_cloud_thumbnail(self.clip_id, self.thumbnail_url)

        self.assertIsNotNone(result)
        self.assertEqual(result.name, f"{self.clip_id}.jpg")

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("requests.get")
    def test_download_and_cache_cloud_thumbnail_download_error(
        self, mock_requests: Mock, mock_mkdir: Mock, mock_exists: Mock
    ) -> None:
        """Test thumbnail download with network error."""
        mock_exists.return_value = False
        mock_requests.side_effect = requests.RequestException("Network error")

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            result = download_and_cache_cloud_thumbnail(
                self.clip_id, self.thumbnail_url
            )

            self.assertIsNone(result)
            mock_logger.error.assert_called()

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    def test_download_and_cache_cloud_thumbnail_exception(self) -> None:
        """Test thumbnail download with general exception."""
        with patch("pathlib.Path.mkdir", side_effect=Exception("Filesystem error")):
            with patch("blinkapp.services.clip_processing.logger") as mock_logger:
                result = download_and_cache_cloud_thumbnail(
                    self.clip_id, self.thumbnail_url
                )

                self.assertIsNone(result)
                mock_logger.error.assert_called()


class TestCloudThumbnailProcessing(BaseTestCase):
    """Test cloud thumbnail processing functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()
        self.clip_id = ClipId("123456")

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    def test_process_cloud_clip_thumbnail_only_exists(self, mock_exists: Mock) -> None:
        """Test thumbnail processing when thumbnail already exists."""
        mock_exists.return_value = True

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_cloud_clip_thumbnail_only(self.clip_id)

            mock_logger.debug.assert_called_with(
                f"Thumbnail already cached for clip {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("blinkapp.services.clip_processing.ensure_clips_cache_initialized")
    def test_process_cloud_clip_thumbnail_only_no_cache_entry(
        self, mock_cache_init: Mock, mock_mkdir: Mock, mock_exists: Mock
    ) -> None:
        """Test thumbnail processing when no cache entry found."""
        mock_exists.return_value = False

        mock_cache = Mock()
        mock_cache.get.return_value = None
        mock_cache_init.return_value = mock_cache

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_cloud_clip_thumbnail_only(self.clip_id)

            mock_logger.debug.assert_called_with(
                f"No thumbnail URL found for cloud clip {self.clip_id} - skipping thumbnail download"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("blinkapp.services.clip_processing.ensure_clips_cache_initialized")
    def test_process_cloud_clip_thumbnail_only_no_thumbnail_url(
        self, mock_cache_init: Mock, mock_mkdir: Mock, mock_exists: Mock
    ) -> None:
        """Test thumbnail processing when no thumbnail URL in cache."""
        mock_exists.return_value = False

        mock_cache = Mock()
        cached_clip = {"media_url": "http://example.com/clip.mp4"}  # No thumbnail URL
        mock_cache.get.return_value = cached_clip
        mock_cache_init.return_value = mock_cache

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_cloud_clip_thumbnail_only(self.clip_id)

            mock_logger.debug.assert_called_with(
                f"No thumbnail URL found for cloud clip {self.clip_id} - skipping thumbnail download"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("blinkapp.services.clip_processing.ensure_clips_cache_initialized")
    def test_process_cloud_clip_thumbnail_only_empty_url(
        self, mock_cache_init: Mock, mock_mkdir: Mock, mock_exists: Mock
    ) -> None:
        """Test thumbnail processing when thumbnail URL is empty."""
        mock_exists.return_value = False

        mock_cache = Mock()
        cached_clip = {"cloud_thumbnail_url": ""}  # Empty URL
        mock_cache.get.return_value = cached_clip
        mock_cache_init.return_value = mock_cache

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_cloud_clip_thumbnail_only(self.clip_id)

            # Empty URL falls through to "No thumbnail URL found" case
            mock_logger.debug.assert_called_with(
                f"No thumbnail URL found for cloud clip {self.clip_id} - skipping thumbnail download"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("blinkapp.services.clip_processing.ensure_clips_cache_initialized")
    @patch("blinkapp.services.clip_processing.download_and_cache_cloud_thumbnail")
    def test_process_cloud_clip_thumbnail_only_success(
        self,
        mock_download: Mock,
        mock_cache_init: Mock,
        mock_mkdir: Mock,
        mock_exists: Mock,
    ) -> None:
        """Test successful thumbnail processing."""
        mock_exists.return_value = False

        mock_cache = Mock()
        cached_clip = {"cloud_thumbnail_url": "http://example.com/thumb.jpg"}
        mock_cache.get.return_value = cached_clip
        mock_cache_init.return_value = mock_cache

        mock_download.return_value = Path("/tmp/test_clips/123456.jpg")

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_cloud_clip_thumbnail_only(self.clip_id)

            mock_download.assert_called_once_with(
                self.clip_id, "http://example.com/thumb.jpg"
            )
            mock_logger.info.assert_called_with(
                f"Downloaded thumbnail for cloud clip {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("blinkapp.services.clip_processing.ensure_clips_cache_initialized")
    @patch("blinkapp.services.clip_processing.download_and_cache_cloud_thumbnail")
    def test_process_cloud_clip_thumbnail_only_download_failed(
        self,
        mock_download: Mock,
        mock_cache_init: Mock,
        mock_mkdir: Mock,
        mock_exists: Mock,
    ) -> None:
        """Test thumbnail processing when download fails."""
        mock_exists.return_value = False

        mock_cache = Mock()
        cached_clip = {"cloud_thumbnail_url": "http://example.com/thumb.jpg"}
        mock_cache.get.return_value = cached_clip
        mock_cache_init.return_value = mock_cache

        mock_download.return_value = None  # Download failed

        with patch("blinkapp.services.clip_processing.logger") as mock_logger:
            process_cloud_clip_thumbnail_only(self.clip_id)

            mock_logger.warning.assert_called_with(
                f"Failed to download thumbnail for cloud clip {self.clip_id}"
            )

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("blinkapp.services.clip_processing.ensure_clips_cache_initialized")
    def test_process_cloud_clip_thumbnail_only_download_exception(
        self, mock_cache_init: Mock, mock_mkdir: Mock, mock_exists: Mock
    ) -> None:
        """Test thumbnail processing with download exception."""
        mock_exists.return_value = False

        mock_cache = Mock()
        cached_clip = {"cloud_thumbnail_url": "http://example.com/thumb.jpg"}
        mock_cache.get.return_value = cached_clip
        mock_cache_init.return_value = mock_cache

        with patch(
            "blinkapp.services.clip_processing.download_and_cache_cloud_thumbnail",
            side_effect=Exception("Download error"),
        ):
            with patch("blinkapp.services.clip_processing.logger") as mock_logger:
                process_cloud_clip_thumbnail_only(self.clip_id)

                mock_logger.error.assert_called()

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    def test_process_cloud_clip_thumbnail_only_exception(self) -> None:
        """Test thumbnail processing with general exception."""
        with patch("pathlib.Path.exists", side_effect=Exception("Filesystem error")):
            with patch("blinkapp.services.clip_processing.logger") as mock_logger:
                process_cloud_clip_thumbnail_only(self.clip_id)

                mock_logger.error.assert_called()


if __name__ == "__main__":
    unittest.main()
