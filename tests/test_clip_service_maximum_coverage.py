"""Maximum coverage tests for clip_service.py - targeting 75% coverage."""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

from blinkapp.models.ids import ClipId


class TestClipServiceMaximumCoverage:
    """Comprehensive tests targeting maximum coverage of clip_service.py."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.clip_id = ClipId("123456")
        self.mock_blink = Mock()
        self.mock_cache_dir = Path("/tmp/test_cache")

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_download_cloud_clip_core_no_blink_instance(self, mock_cache: Mock) -> None:
        """Test _download_cloud_clip_core with no blink instance."""
        from blinkapp.services.clip_download import _download_cloud_clip_core

        filepath, error = _download_cloud_clip_core(
            self.clip_id, None, self.mock_cache_dir
        )

        assert error == "No blink instance"
        assert filepath is None

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_download_cloud_clip_core_cached_file_exists(
        self, mock_cache: Mock
    ) -> None:
        """Test _download_cloud_clip_core with existing cached file."""
        from blinkapp.services.clip_download import _download_cloud_clip_core

        mock_filepath = Mock()
        mock_filepath.exists.return_value = True
        mock_cache_instance = {self.clip_id: {"filepath": mock_filepath}}
        mock_cache.return_value = mock_cache_instance

        filepath, error = _download_cloud_clip_core(
            self.clip_id, self.mock_blink, self.mock_cache_dir
        )

        assert error == ""
        assert filepath == mock_filepath

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_download_cloud_clip_core_cached_file_os_error(
        self, mock_cache: Mock
    ) -> None:
        """Test _download_cloud_clip_core with OSError on cached file check."""
        from blinkapp.services.clip_download import _download_cloud_clip_core

        mock_filepath = Mock()
        mock_filepath.exists.side_effect = OSError("File access error")
        mock_cache_instance = {self.clip_id: {"filepath": mock_filepath}}
        mock_cache.return_value = mock_cache_instance

        self.mock_blink.videos = {"all": []}

        with patch(
            "blinkapp.services.blink_service.ensure_blink_connection_initialized",
            return_value=Mock(execute=Mock(return_value=[])),
        ):
            filepath, error = _download_cloud_clip_core(
                self.clip_id, self.mock_blink, self.mock_cache_dir
            )

        assert error == "Clip not found"
        assert filepath is None

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_download_cloud_clip_core_clip_not_found(self, mock_cache: Mock) -> None:
        """Test _download_cloud_clip_core when clip not found in metadata."""
        from blinkapp.services.clip_download import _download_cloud_clip_core

        mock_cache.return_value = {}
        self.mock_blink.videos = {"all": []}

        with patch(
            "blinkapp.services.blink_service.ensure_blink_connection_initialized",
            return_value=Mock(execute=Mock(return_value=[])),
        ):
            filepath, error = _download_cloud_clip_core(
                self.clip_id, self.mock_blink, self.mock_cache_dir
            )

        assert error == "Clip not found"
        assert filepath is None

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    @patch("blinkapp.services.connection_service.ensure_http_session_initialized")
    def test_download_cloud_clip_core_no_media_url(
        self, mock_session, mock_executor, mock_cache
    ):
        """Test _download_cloud_clip_core with no media URL."""
        from blinkapp.services.clip_download import _download_cloud_clip_core

        mock_cache.return_value = {}
        clip_info = {
            "id": "123456",
            "created_at": "2023-01-01T12:00:00Z",
            "device_name": "test_camera",
            "media": None,
        }
        self.mock_blink.videos = {"all": [clip_info]}

        with patch("pathlib.Path.exists", return_value=False):
            with patch(
                "blinkapp.services.blink_service.ensure_blink_connection_initialized",
                return_value=Mock(execute=Mock(return_value=[clip_info])),
            ):
                filepath, error = _download_cloud_clip_core(
                    self.clip_id, self.mock_blink, self.mock_cache_dir
                )

        assert error is not None and "not available for download" in error
        assert filepath is None

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    @patch("blinkapp.services.connection_service.ensure_http_session_initialized")
    def test_download_cloud_clip_core_http_error(
        self, mock_session, mock_executor, mock_cache
    ):
        """Test _download_cloud_clip_core with HTTP error."""
        from blinkapp.services.clip_download import _download_cloud_clip_core

        mock_cache.return_value = {}
        clip_info = {
            "id": "123456",
            "created_at": "2023-01-01T12:00:00Z",
            "device_name": "test_camera",
            "media": "http://example.com/video.mp4",
        }
        self.mock_blink.videos = {"all": [clip_info]}

        # Mock HTTP session with error
        mock_http_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_http_session.get.return_value = mock_response
        mock_session.return_value = mock_http_session

        # Mock executor
        mock_future = Mock()
        mock_future.result.return_value = False
        mock_executor_instance = Mock()
        mock_executor_instance.submit.return_value = mock_future
        mock_executor.return_value = mock_executor_instance

        with patch("pathlib.Path.exists", return_value=False):
            with patch(
                "blinkapp.services.blink_service.ensure_blink_connection_initialized",
                return_value=Mock(execute=Mock(return_value=[clip_info])),
            ):
                filepath, error = _download_cloud_clip_core(
                    self.clip_id, self.mock_blink, self.mock_cache_dir
                )

        assert error is not None and "We couldn't download your video clip" in error
        assert filepath is None

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    @patch("blinkapp.services.connection_service.ensure_http_session_initialized")
    def test_download_cloud_clip_core_timeout_error(
        self, mock_session, mock_executor, mock_cache
    ):
        """Test _download_cloud_clip_core with timeout error."""
        from blinkapp.services.clip_download import _download_cloud_clip_core

        mock_cache.return_value = {}
        clip_info = {
            "id": "123456",
            "created_at": "2023-01-01T12:00:00Z",
            "device_name": "test_camera",
            "media": "http://example.com/video.mp4",
        }
        self.mock_blink.videos = {"all": [clip_info]}

        # Mock executor with timeout
        mock_future = Mock()
        mock_future.result.side_effect = Exception("Timeout")
        mock_executor_instance = Mock()
        mock_executor_instance.submit.return_value = mock_future
        mock_executor.return_value = mock_executor_instance

        with patch("pathlib.Path.exists", return_value=False):
            with patch(
                "blinkapp.services.blink_service.ensure_blink_connection_initialized",
                return_value=Mock(execute=Mock(return_value=[clip_info])),
            ):
                filepath, error = _download_cloud_clip_core(
                    self.clip_id, self.mock_blink, self.mock_cache_dir
                )

        assert error is not None and "taking longer than expected" in error
        assert filepath is None

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    @patch("blinkapp.services.connection_service.ensure_http_session_initialized")
    def test_download_cloud_clip_core_success(
        self, mock_session, mock_executor, mock_cache
    ):
        """Test _download_cloud_clip_core successful download."""
        from blinkapp.services.clip_download import _download_cloud_clip_core

        mock_cache.return_value = {}
        clip_info = {
            "id": "123456",
            "created_at": "2023-01-01T12:00:00Z",
            "device_name": "test_camera",
            "media": "http://example.com/video.mp4",
        }
        self.mock_blink.videos = {"all": [clip_info]}

        # Mock HTTP session with success
        mock_http_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"video_data"
        mock_http_session.get.return_value = mock_response
        mock_session.return_value = mock_http_session

        # Mock executor
        mock_future = Mock()
        mock_future.result.return_value = True
        mock_executor_instance = Mock()
        mock_executor_instance.submit.return_value = mock_future
        mock_executor.return_value = mock_executor_instance

        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.write_bytes"):
                with patch(
                    "blinkapp.services.blink_service.ensure_blink_connection_initialized",
                    return_value=Mock(execute=Mock(return_value=[clip_info])),
                ):
                    filepath, error = _download_cloud_clip_core(
                        self.clip_id, self.mock_blink, self.mock_cache_dir
                    )

        assert error == ""
        assert filepath is not None

    @patch("blinkapp.services.clip_download._get_blink_instance")
    @patch("blinkapp.services.clip_download._get_clips_cache_dir")
    @patch("blinkapp.services.clip_download._download_cloud_clip_core")
    @patch("blinkapp.models.responses.create_api_response")
    @patch("flask.jsonify")
    def test_download_cloud_clip_error_response(
        self, mock_jsonify, mock_create_response, mock_core, mock_cache_dir, mock_blink
    ):
        """Test download_cloud_clip error response."""
        from blinkapp.services.clip_download import download_cloud_clip

        mock_blink.return_value = self.mock_blink
        mock_cache_dir.return_value = self.mock_cache_dir
        mock_core.return_value = (False, "Test error", None)
        mock_create_response.return_value = ({"error": "Test error"}, 500)
        mock_jsonify.return_value = "json_response"

        download_cloud_clip(self.clip_id)

        mock_core.assert_called_once_with(
            self.clip_id, self.mock_blink, self.mock_cache_dir
        )
        mock_create_response.assert_called_once()
        mock_jsonify.assert_called_once()

    @patch("blinkapp.services.clip_service._get_blink_instance")
    @patch("blinkapp.services.clip_service._get_clips_cache_dir")
    @patch("blinkapp.services.clip_service._download_cloud_clip_core")
    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    @patch("flask.send_file")
    def test_download_cloud_clip_success_response(
        self,
        mock_send_file,
        mock_executor,
        mock_cache_init,
        mock_core,
        mock_cache_dir,
        mock_blink,
    ):
        """Test download_cloud_clip success response."""
        from blinkapp.services.clip_download import download_cloud_clip

        mock_filepath = Mock()
        mock_filepath.name = "test.mp4"
        mock_filepath.exists.return_value = True
        mock_blink.return_value = self.mock_blink
        mock_cache_dir.return_value = self.mock_cache_dir
        mock_core.return_value = (True, "", mock_filepath)
        mock_cache_init.return_value = {}
        mock_executor.return_value = Mock()
        mock_send_file.return_value = "file_response"

        download_cloud_clip(self.clip_id)

        mock_core.assert_called_once_with(
            self.clip_id, self.mock_blink, self.mock_cache_dir
        )
        mock_send_file.assert_called_once()

    def test_get_blink_instance(self) -> None:
        """Test _get_blink_instance function."""
        from blinkapp.services.clip_download import _get_blink_instance

        with patch("blinkapp.services.blink_service.blink", "mock_blink"):
            result = _get_blink_instance()
            assert result == "mock_blink"

    def test_get_clips_cache_dir(self) -> None:
        """Test _get_clips_cache_dir function."""
        from blinkapp.services.clip_download import _get_clips_cache_dir

        with patch("blinkapp.CLIPS_CACHE_DIR", "/test/cache"):
            result = _get_clips_cache_dir()
            assert result == Path("/test/cache")

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_process_cloud_clips_empty_metadata(self, mock_cache: Mock) -> None:
        """Test process_cloud_clips with empty metadata."""
        from blinkapp.services.clip_service import process_cloud_clips

        mock_cache.return_value = {}
        result = process_cloud_clips([])
        assert result == []

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.clip_service.format_clips_by_day")
    def test_process_cloud_clips_with_data(
        self, mock_format: Mock, mock_cache: Mock
    ) -> None:
        """Test process_cloud_clips with valid data."""
        from blinkapp.services.clip_service import process_cloud_clips

        mock_cache.return_value = {}
        mock_format.return_value = [{"date": "January 01, 2023", "clips": []}]

        videos_metadata: list[dict[str, object]] = [
            {
                "id": "123456",
                "created_at": "2023-01-01T12:00:00Z",
                "device_name": "Test Camera",
                "thumbnail": "http://example.com/thumb.jpg",
                "media": "http://example.com/video.mp4",
            }
        ]

        result = process_cloud_clips(videos_metadata)
        assert len(result) == 1
        mock_format.assert_called_once()

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.utils.formatters.format_clips_by_day")
    def test_process_cloud_clips_invalid_timestamp(
        self, mock_format, mock_cache
    ) -> None:
        """Test process_cloud_clips with invalid timestamp."""
        from blinkapp.services.clip_service import process_cloud_clips

        mock_cache.return_value = {}
        mock_format.return_value = []

        videos_metadata: list[dict[str, object]] = [
            {
                "id": "123456",
                "created_at": "invalid_timestamp",
                "device_name": "Test Camera",
            }
        ]

        with patch("blinkapp.services.clip_service.logger") as mock_logger:
            process_cloud_clips(videos_metadata)
            mock_logger.warning.assert_called()

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.utils.formatters.format_clips_by_day")
    def test_process_local_clips_no_blink(
        self, mock_format, mock_connection, mock_blink
    ):
        """Test process_local_clips with no blink instance."""
        from blinkapp.services.clip_service import process_local_clips

        mock_blink.return_value = None
        mock_format.return_value = []

        result = process_local_clips()
        assert result == []

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.clip_service.format_clips_by_day")
    def test_process_local_clips_with_data(
        self, mock_format, mock_cache, mock_connection, mock_blink
    ):
        """Test process_local_clips with valid data."""
        from blinkapp.services.clip_service import process_local_clips

        # Mock sync module with local storage
        mock_item = Mock()
        mock_item.created_at = datetime(2023, 1, 1, 12, 0, 0)
        mock_item.id = 123
        mock_item.name = "Test Camera"
        mock_item.url.return_value = "http://example.com/local_video.mp4"

        mock_sync = Mock()
        mock_sync.local_storage = True
        mock_sync.local_storage_manifest_ready = True
        mock_sync._local_storage = {
            "manifest": [mock_item],
            "last_manifest_id": "manifest_123",
        }

        mock_blink.sync = {"sync1": mock_sync}

        mock_cache.return_value = {}
        mock_format.return_value = [{"date": "January 01, 2023", "clips": []}]

        result = process_local_clips()
        assert len(result) == 1

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.utils.formatters.format_clips_by_day")
    def test_process_local_clips_sync_error(
        self, mock_format, mock_connection, mock_blink
    ):
        """Test process_local_clips with sync module error."""
        from blinkapp.services.clip_service import process_local_clips

        mock_sync = Mock()
        mock_sync.refresh.side_effect = Exception("Sync error")

        mock_blink.sync = {"sync1": mock_sync}
        mock_format.return_value = []

        with patch("blinkapp.services.clip_service.logger") as mock_logger:
            process_local_clips()
            mock_logger.warning.assert_called()

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_http_session_initialized")
    def test_download_and_cache_cloud_thumbnail_success(
        self, mock_session, mock_cache
    ) -> None:
        """Test download_and_cache_cloud_thumbnail success."""
        from blinkapp.services.clip_processing import download_and_cache_cloud_thumbnail

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
    def test_download_and_cache_cloud_thumbnail_error(
        self, mock_session, mock_cache
    ) -> None:
        """Test download_and_cache_cloud_thumbnail with error."""
        from blinkapp.services.clip_processing import download_and_cache_cloud_thumbnail

        mock_session.side_effect = Exception("Network error")

        with patch("blinkapp.services.clip_service.logger") as mock_logger:
            result = download_and_cache_cloud_thumbnail(
                self.clip_id, "http://example.com/thumb.jpg"
            )

            assert result is None
            mock_logger.error.assert_called()

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    def test_process_cloud_clip_background(
        self, mock_executor, mock_cache, mock_connection, mock_blink
    ):
        """Test process_cloud_clip_background function."""
        from blinkapp.services.clip_processing import process_cloud_clip_background

        mock_blink_instance = Mock()
        mock_blink.return_value = mock_blink_instance

        mock_executor_instance = Mock()
        mock_executor.return_value = mock_executor_instance

        mock_cache.return_value = {}

        with patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/cache"):
            process_cloud_clip_background(self.clip_id)

            mock_executor_instance.submit.assert_called_once()

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    def test_process_local_clip_background(
        self, mock_executor, mock_cache, mock_connection, mock_blink
    ):
        """Test process_local_clip_background function."""
        from blinkapp.services.clip_processing import process_local_clip_background

        mock_blink_instance = Mock()
        mock_blink.return_value = mock_blink_instance

        mock_executor_instance = Mock()
        mock_executor.return_value = mock_executor_instance

        mock_cache.return_value = {}

        with patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/cache"):
            process_local_clip_background(self.clip_id, "sync1", "123")

            mock_executor_instance.submit.assert_called_once()

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    @patch("flask.send_file")
    def test_download_clip_common(
        self, mock_send_file, mock_executor, mock_cache
    ) -> None:
        """Test download_clip_common function."""
        from blinkapp.services.clip_download import download_clip_common

        mock_filepath = Mock()
        mock_filepath.exists.return_value = True
        mock_cache_instance = {}
        mock_cache.return_value = mock_cache_instance

        mock_executor_instance = Mock()
        mock_executor.return_value = mock_executor_instance

        mock_send_file.return_value = "file_response"

        result = download_clip_common(mock_filepath, self.clip_id)

        assert result == ("file_response", 200)
        mock_executor_instance.submit.assert_called_once()
        assert self.clip_id in mock_cache_instance

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.models.responses.create_api_response")
    @patch("flask.jsonify")
    def test_download_local_clip_sync_not_found(
        self,
        mock_jsonify,
        mock_create_response,
        mock_cache,
        mock_connection,
        mock_blink,
    ):
        """Test download_local_clip with sync module not found."""
        from blinkapp.services.clip_download import download_local_clip

        mock_blink_instance = Mock()
        mock_blink_instance.sync = {}
        mock_blink.return_value = mock_blink_instance

        mock_cache.return_value = {}
        mock_create_response.return_value = ({"error": "Sync not found"}, 404)
        mock_jsonify.return_value = "json_response"

        download_local_clip(self.clip_id, "nonexistent_sync", "123")

        mock_create_response.assert_called_once()
        mock_jsonify.assert_called_once()

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.models.responses.create_api_response")
    @patch("flask.jsonify")
    def test_download_local_clip_no_local_storage(
        self,
        mock_jsonify,
        mock_create_response,
        mock_cache,
        mock_connection,
        mock_blink,
    ):
        """Test download_local_clip with no local storage."""
        from blinkapp.services.clip_download import download_local_clip

        mock_sync = Mock()
        mock_sync.local_storage = False

        mock_blink_instance = Mock()
        mock_blink_instance.sync = {"sync1": mock_sync}
        mock_blink.return_value = mock_blink_instance

        mock_cache.return_value = {}
        mock_create_response.return_value = ({"error": "No local storage"}, 404)
        mock_jsonify.return_value = "json_response"

        download_local_clip(self.clip_id, "sync1", "123")

        mock_create_response.assert_called_once()
        mock_jsonify.assert_called_once()

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.models.responses.create_api_response")
    @patch("flask.jsonify")
    def test_download_local_clip_item_not_found(
        self,
        mock_jsonify,
        mock_create_response,
        mock_cache,
        mock_connection,
        mock_blink,
    ):
        """Test download_local_clip with item not found."""
        from blinkapp.services.clip_download import download_local_clip

        mock_sync = Mock()
        mock_sync.local_storage = True
        mock_sync.local_storage_manifest_ready = True
        mock_sync._local_storage = {"manifest": []}

        mock_blink_instance = Mock()
        mock_blink_instance.sync = {"sync1": mock_sync}
        mock_blink.return_value = mock_blink_instance

        mock_cache.return_value = {}
        mock_create_response.return_value = ({"error": "Item not found"}, 404)
        mock_jsonify.return_value = "json_response"

        download_local_clip(self.clip_id, "sync1", "123")

        mock_create_response.assert_called_once()
        mock_jsonify.assert_called_once()

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.clip_service.download_clip_common")
    @patch("flask.send_file")
    def test_download_local_clip_cached_success(
        self,
        mock_send_file,
        mock_download_common,
        mock_cache,
        mock_connection,
        mock_blink,
    ):
        """Test download_local_clip with cached file success."""
        from blinkapp.services.clip_download import download_local_clip

        mock_filepath = Mock()
        mock_filepath.exists.return_value = True
        mock_cache_instance = {self.clip_id: {"filepath": mock_filepath}}
        mock_cache.return_value = mock_cache_instance

        mock_send_file.return_value = "file_response"

        result = download_local_clip(self.clip_id, "sync1", "123")

        assert result == ("file_response", 200)
        mock_send_file.assert_called_once_with(str(mock_filepath), as_attachment=True)
