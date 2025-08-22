"""Tests for background processing functions in clip_service.py."""

from pathlib import Path
from unittest.mock import Mock, mock_open, patch

from blinkapp.models.ids import ClipId


class TestClipServiceBackground:
    """Tests for background processing and thumbnail functions."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.clip_id = ClipId("123456")

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_http_session_initialized")
    def test_download_and_cache_cloud_thumbnail_success(
        self, mock_session, mock_cache
    ) -> None:
        """Test download_and_cache_cloud_thumbnail success."""
        from blinkapp.services.clip_service import download_and_cache_cloud_thumbnail

        mock_http_session = Mock()
        mock_response = Mock()
        mock_response.content = b"thumbnail_data"
        mock_http_session.get.return_value = mock_response
        mock_session.return_value = mock_http_session

        mock_cache_instance = {}
        mock_cache.return_value = mock_cache_instance

        with patch("blinkapp.config.Config.DEFAULT_CACHE_DIR", "/tmp/cache"):
            with patch("pathlib.Path.mkdir"):
                with patch("builtins.open", mock_open()):
                    with patch("blinkapp.services.clip_service.logger") as mock_logger:
                        result = download_and_cache_cloud_thumbnail(
                            self.clip_id, "http://example.com/thumb.jpg"
                        )

                        assert result is not None
                        mock_logger.info.assert_called()

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_http_session_initialized")
    def test_download_and_cache_cloud_thumbnail_http_error(
        self, mock_session, mock_cache
    ):
        """Test download_and_cache_cloud_thumbnail with HTTP error."""
        from blinkapp.services.clip_service import download_and_cache_cloud_thumbnail

        mock_http_session = Mock()
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        mock_http_session.get.return_value = mock_response
        mock_session.return_value = mock_http_session

        with patch("blinkapp.services.clip_service.logger") as mock_logger:
            result = download_and_cache_cloud_thumbnail(
                self.clip_id, "http://example.com/thumb.jpg"
            )

            assert result is None
            mock_logger.error.assert_called()

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_http_session_initialized")
    def test_download_and_cache_cloud_thumbnail_file_write_error(
        self, mock_session, mock_cache
    ):
        """Test download_and_cache_cloud_thumbnail with file write error."""
        from blinkapp.services.clip_service import download_and_cache_cloud_thumbnail

        mock_http_session = Mock()
        mock_response = Mock()
        mock_response.content = b"thumbnail_data"
        mock_http_session.get.return_value = mock_response
        mock_session.return_value = mock_http_session

        mock_cache_instance = {}
        mock_cache.return_value = mock_cache_instance

        with patch("blinkapp.config.Config.DEFAULT_CACHE_DIR", "/tmp/cache"):
            with patch("pathlib.Path.mkdir"):
                with patch("builtins.open", side_effect=OSError("Write error")):
                    with patch("blinkapp.services.clip_service.logger") as mock_logger:
                        result = download_and_cache_cloud_thumbnail(
                            self.clip_id, "http://example.com/thumb.jpg"
                        )

                        assert result is None
                        mock_logger.error.assert_called()

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_http_session_initialized")
    def test_download_and_cache_cloud_thumbnail_update_existing_cache(
        self, mock_session, mock_cache
    ):
        """Test download_and_cache_cloud_thumbnail updating existing cache entry."""
        from blinkapp.services.clip_service import download_and_cache_cloud_thumbnail

        mock_http_session = Mock()
        mock_response = Mock()
        mock_response.content = b"thumbnail_data"
        mock_http_session.get.return_value = mock_response
        mock_session.return_value = mock_http_session

        # Existing cache entry
        existing_entry = {"filepath": Path("/tmp/existing.mp4")}
        mock_cache_instance = {self.clip_id: existing_entry}
        mock_cache.return_value = mock_cache_instance

        with patch("blinkapp.config.Config.DEFAULT_CACHE_DIR", "/tmp/cache"):
            with patch("pathlib.Path.mkdir"):
                with patch("builtins.open", mock_open()):
                    result = download_and_cache_cloud_thumbnail(
                        self.clip_id, "http://example.com/thumb.jpg"
                    )

                    assert result is not None
                    # Verify cache was updated with thumbnail
                    assert "thumbnail" in mock_cache_instance[self.clip_id]

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    def test_process_cloud_clip_background(
        self, mock_executor, mock_cache, mock_connection, mock_blink
    ):
        """Test process_cloud_clip_background function."""
        from blinkapp.services.clip_service import process_cloud_clip_background

        mock_blink_instance = Mock()
        mock_blink.return_value = mock_blink_instance

        mock_executor_instance = Mock()
        mock_executor.return_value = mock_executor_instance

        mock_cache.return_value = {}

        with patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/cache"):
            process_cloud_clip_background(self.clip_id)

            # Verify executor was called to submit background task
            mock_executor_instance.submit.assert_called_once()

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    def test_process_local_clip_background(
        self, mock_executor, mock_cache, mock_connection, mock_blink
    ):
        """Test process_local_clip_background function."""
        from blinkapp.services.clip_service import process_local_clip_background

        mock_blink_instance = Mock()
        mock_blink.return_value = mock_blink_instance

        mock_executor_instance = Mock()
        mock_executor.return_value = mock_executor_instance

        mock_cache.return_value = {}

        with patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/cache"):
            process_local_clip_background(self.clip_id, "sync1", 123)

            # Verify executor was called to submit background task
            mock_executor_instance.submit.assert_called_once()

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    @patch("flask.send_file")
    def test_download_clip_common(
        self, mock_send_file, mock_executor, mock_cache
    ) -> None:
        """Test download_clip_common function."""
        from blinkapp.services.clip_service import download_clip_common

        mock_filepath = Path("/tmp/test.mp4")
        mock_cache_instance = {}
        mock_cache.return_value = mock_cache_instance

        mock_executor_instance = Mock()
        mock_executor.return_value = mock_executor_instance

        mock_send_file.return_value = "file_response"

        result = download_clip_common(
            self.clip_id, mock_filepath, "test.mp4", middle_frame=True
        )

        assert result == ("file_response", 200)
        # Verify background thumbnail generation was submitted
        mock_executor_instance.submit.assert_called_once()
        # Verify clip was cached
        assert self.clip_id in mock_cache_instance
        cached_entry = mock_cache_instance[self.clip_id]
        assert cached_entry["filepath"] == mock_filepath
        assert (
            cached_entry["thumbnail"] is None
        )  # Initially None, updated in background

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    @patch("flask.send_file")
    def test_download_clip_common_with_download_name(
        self, mock_send_file, mock_executor, mock_cache
    ):
        """Test download_clip_common with proper download name."""
        from blinkapp.services.clip_service import download_clip_common

        mock_filepath = Path("/tmp/test.mp4")
        mock_cache_instance = {}
        mock_cache.return_value = mock_cache_instance

        mock_executor_instance = Mock()
        mock_executor.return_value = mock_executor_instance

        mock_send_file.return_value = "file_response"

        filename = "custom_filename.mp4"
        result = download_clip_common(
            self.clip_id, mock_filepath, filename, middle_frame=False
        )

        assert result == ("file_response", 200)
        # Verify send_file was called with correct parameters
        mock_send_file.assert_called_once_with(
            str(mock_filepath), as_attachment=True, download_name=filename
        )
