"""Tests for background processing functions in clip_service.py."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

from requests import Response
from test_base import (
    BaseTestCase,
    create_mock_blink_instance,
    create_mock_cache_instance,
)

from blinkapp.models.ids import ClipId


class TestClipServiceBackground(BaseTestCase):
    """Tests for background processing and thumbnail functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()
        self.clip_id = ClipId("123456")

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_download_and_cache_cloud_thumbnail_success(self, mock_cache) -> None:
        """Test download_and_cache_cloud_thumbnail success."""
        from blinkapp.services.clip_processing import download_and_cache_cloud_thumbnail

        mock_response = Mock(spec=Response)
        mock_response.content = b"thumbnail_data"
        mock_response.raise_for_status = Mock()  # No exception

        mock_cache_instance = {}
        mock_cache.return_value = mock_cache_instance

        with patch(
            "blinkapp.services.clip_processing.requests.get", return_value=mock_response
        ):
            with patch(
                "blinkapp.CLIPS_CACHE_DIR",
                "/tmp/cache",
            ):
                with patch("pathlib.Path.mkdir"):
                    with patch(
                        "pathlib.Path.exists", return_value=False
                    ):  # File doesn't exist, need to download
                        with patch("builtins.open", mock_open()):
                            result = download_and_cache_cloud_thumbnail(
                                self.clip_id, "http://example.com/thumb.jpg"
                            )

                            assert result is not None

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_download_and_cache_cloud_thumbnail_http_error(self, mock_cache) -> None:
        """Test download_and_cache_cloud_thumbnail with HTTP error."""
        import requests

        from blinkapp.services.clip_processing import download_and_cache_cloud_thumbnail

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("HTTP Error")

        with patch(
            "blinkapp.services.clip_processing.requests.get", return_value=mock_response
        ):
            with patch(
                "blinkapp.CLIPS_CACHE_DIR",
                "/tmp/cache",
            ):
                with patch("pathlib.Path.mkdir"):
                    with patch("pathlib.Path.exists", return_value=False):
                        with patch(
                            "blinkapp.services.clip_processing.logger"
                        ) as mock_logger:
                            result = download_and_cache_cloud_thumbnail(
                                self.clip_id, "http://example.com/thumb.jpg"
                            )

                            assert result is None
                            mock_logger.error.assert_called()

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_download_and_cache_cloud_thumbnail_file_write_error(
        self, mock_cache
    ) -> None:
        """Test download_and_cache_cloud_thumbnail with file write error."""
        from blinkapp.services.clip_processing import download_and_cache_cloud_thumbnail

        mock_response = Mock()
        mock_response.content = b"thumbnail_data"
        mock_response.raise_for_status = Mock()  # No HTTP error

        mock_cache_instance = {}
        mock_cache.return_value = mock_cache_instance

        with patch(
            "blinkapp.services.clip_processing.requests.get", return_value=mock_response
        ):
            with patch(
                "blinkapp.CLIPS_CACHE_DIR",
                return_value="/tmp/cache",
            ):
                with patch("pathlib.Path.mkdir"):
                    with patch("pathlib.Path.exists", return_value=False):
                        with patch("builtins.open", side_effect=OSError("Write error")):
                            with patch(
                                "blinkapp.services.clip_processing.logger"
                            ) as mock_logger:
                                result = download_and_cache_cloud_thumbnail(
                                    self.clip_id, "http://example.com/thumb.jpg"
                                )

                                assert result is None
                                mock_logger.error.assert_called()

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_download_and_cache_cloud_thumbnail_update_existing_cache(
        self, mock_cache
    ) -> None:
        """Test download_and_cache_cloud_thumbnail updating existing cache entry."""
        from blinkapp.services.clip_processing import download_and_cache_cloud_thumbnail

        mock_response = Mock()
        mock_response.content = b"thumbnail_data"
        mock_response.raise_for_status = Mock()  # No HTTP error

        # Existing cache entry
        from blinkapp.models.cache import ClipCacheEntry

        existing_entry = ClipCacheEntry(
            filepath=Path("/tmp/existing.mp4"), media_url="", created_at=""
        )
        mock_cache_instance = {self.clip_id: existing_entry}
        mock_cache.return_value = mock_cache_instance

        with patch(
            "blinkapp.services.clip_processing.requests.get", return_value=mock_response
        ):
            with patch(
                "blinkapp.CLIPS_CACHE_DIR",
                return_value="/tmp/cache",
            ):
                with patch("pathlib.Path.mkdir"):
                    with patch(
                        "pathlib.Path.exists", return_value=False
                    ):  # Thumbnail doesn't exist
                        with patch("builtins.open", mock_open()):
                            result = download_and_cache_cloud_thumbnail(
                                self.clip_id, "http://example.com/thumb.jpg"
                            )

                            assert result is not None
                            # Verify the function returned a path
                            assert str(result).endswith(".jpg")

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.clip_processing.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    def test_process_cloud_clip_background(
        self, mock_executor, mock_cache, mock_connection, mock_blink
    ) -> None:
        """Test process_cloud_clip_background function."""
        from blinkapp.services.clip_processing import process_cloud_clip_background

        mock_blink_instance = create_mock_blink_instance(available=True)
        mock_blink_instance.get_clip_url = Mock(
            return_value="http://example.com/video.mp4"
        )
        mock_blink.return_value = mock_blink_instance

        mock_executor_instance = Mock(spec=ThreadPoolExecutor)
        mock_executor.return_value = mock_executor_instance

        # Set up cache with clip data including media_url
        clip_data = {
            "id": str(self.clip_id),
            "media_url": "http://example.com/video.mp4",
        }
        mock_cache_instance = create_mock_cache_instance({str(self.clip_id): clip_data})
        mock_cache.return_value = mock_cache_instance

        with patch(
            "blinkapp.CLIPS_CACHE_DIR",
            return_value="/tmp/cache",
        ):
            with patch(
                "pathlib.Path.exists", return_value=False
            ):  # Thumbnail and clip don't exist
                with patch("pathlib.Path.mkdir"):
                    with patch(
                        "blinkapp.services.clip_processing.requests.get"
                    ) as mock_get:
                        mock_response = Mock()
                        mock_response.content = b"video_data"
                        mock_response.raise_for_status = Mock()
                        mock_get.return_value = mock_response

                        with patch("builtins.open", mock_open()):
                            process_cloud_clip_background(self.clip_id)

                            # Verify the function completed successfully
                            mock_get.assert_called_once()

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    def test_process_local_clip_background(
        self, mock_executor, mock_cache, mock_connection, mock_blink
    ) -> None:
        """Test process_local_clip_background function."""
        from blinkapp.services.clip_processing import process_local_clip_background

        # Set up sync module with local storage
        mock_local_storage = Mock()
        mock_local_storage.get_video_count.return_value = 1
        mock_local_storage.get_video_info.return_value = {
            "url": "http://example.com/local_video.mp4"
        }

        mock_sync_module = Mock()
        mock_sync_module.local_storage = mock_local_storage

        mock_blink_instance = create_mock_blink_instance(available=True)
        mock_blink_instance.get_clip_url = Mock(
            return_value="http://example.com/local_video.mp4"
        )
        mock_blink_instance.sync = {"sync1": mock_sync_module}
        mock_blink.return_value = mock_blink_instance

        mock_executor_instance = Mock(spec=ThreadPoolExecutor)
        mock_executor.return_value = mock_executor_instance

        mock_cache.return_value = {}

        with patch(
            "blinkapp.CLIPS_CACHE_DIR",
            return_value="/tmp/cache",
        ):
            with patch(
                "blinkapp.services.blink_service.blink",
                mock_blink_instance,
            ):
                with patch(
                    "pathlib.Path.exists", return_value=False
                ):  # Thumbnail doesn't exist
                    with patch("pathlib.Path.mkdir"):
                        with patch(
                            "blinkapp.services.clip_processing.requests.get"
                        ) as mock_get:
                            mock_response = Mock()
                            mock_response.content = b"video_data"
                            mock_response.raise_for_status = Mock()
                            mock_get.return_value = mock_response

                            with patch("builtins.open", mock_open()):
                                with patch(
                                    "blinkapp.services.clip_processing.logger"
                                ) as mock_logger:
                                    process_local_clip_background(
                                        self.clip_id, "sync1", "123"
                                    )

                                    # Verify the function logged the warning (not fully implemented)
                                    mock_logger.warning.assert_called()

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    @patch("blinkapp.services.clip_download.send_file")
    def test_download_clip_common(
        self, mock_send_file, mock_executor, mock_cache
    ) -> None:
        """Test download_clip_common function."""
        import tempfile
        from pathlib import Path

        from blinkapp.services.clip_download import download_clip_common

        # Create a real temporary file for the test
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            temp_file.write(b"fake video data")
            temp_path = Path(temp_file.name)

        try:
            mock_cache_instance = {}
            mock_cache.return_value = mock_cache_instance

            mock_executor_instance = Mock(spec=ThreadPoolExecutor)
            mock_executor.return_value = mock_executor_instance

            mock_send_file.return_value = "file_response"

            # Need Flask request context for send_file
            from blinkapp import app

            with app.test_request_context():
                result = download_clip_common(temp_path, self.clip_id)

            assert result is not None
            # Verify send_file was called with correct parameters
            mock_send_file.assert_called_once_with(
                temp_path,
                as_attachment=True,
                download_name=f"clip_{self.clip_id}.mp4",
                mimetype="video/mp4",
            )
        finally:
            # Clean up the temporary file
            if temp_path.exists():
                temp_path.unlink()

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    @patch("blinkapp.services.clip_download.send_file")
    def test_download_clip_common_with_download_name(
        self, mock_send_file, mock_executor, mock_cache
    ) -> None:
        """Test download_clip_common with proper download name."""
        import tempfile
        from pathlib import Path

        from blinkapp.services.clip_download import download_clip_common

        # Create a real temporary file for the test
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            temp_file.write(b"fake video data")
            temp_path = Path(temp_file.name)

        try:
            mock_cache_instance = {}
            mock_cache.return_value = mock_cache_instance

            mock_executor_instance = Mock(spec=ThreadPoolExecutor)
            mock_executor.return_value = mock_executor_instance

            mock_send_file.return_value = "file_response"

            # Need Flask request context for send_file
            from blinkapp import app

            with app.test_request_context():
                result = download_clip_common(temp_path, self.clip_id)

            assert result is not None
            # Verify send_file was called with correct parameters
            mock_send_file.assert_called_once_with(
                temp_path,
                as_attachment=True,
                download_name=f"clip_{self.clip_id}.mp4",
                mimetype="video/mp4",
            )
        finally:
            # Clean up the temporary file
            if temp_path.exists():
                temp_path.unlink()
