#!/usr/bin/env python3
"""
Final comprehensive tests to achieve 75% coverage for clip_service.py.
Targets remaining uncovered lines with working, minimal tests.
"""

from pathlib import Path
from unittest.mock import Mock, patch

from blinkapp.models.ids import ClipId


class TestClipServiceFinal:
    """Final tests to reach 75% coverage."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.clip_id = ClipId("123456")

    def test_get_clips_cache_dir(self) -> None:
        """Test _get_clips_cache_dir helper function."""
        from blinkapp.services.clip_service import _get_clips_cache_dir

        with patch("blinkapp.CLIPS_CACHE_DIR", "/test/cache"):
            result = _get_clips_cache_dir()
            assert result == Path("/test/cache")

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_download_and_cache_cloud_thumbnail_no_url(self, mock_cache: Mock) -> None:
        """Test download_and_cache_cloud_thumbnail with no URL."""
        from blinkapp.services.clip_service import download_and_cache_cloud_thumbnail

        mock_cache.return_value = {}

        result = download_and_cache_cloud_thumbnail(self.clip_id, None)  # type: ignore[arg-type]

        assert result is None

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_download_cloud_clip_core_no_blink(self, mock_cache: Mock) -> None:
        """Test _download_cloud_clip_core with no blink instance."""
        from blinkapp.services.clip_service import _download_cloud_clip_core

        mock_cache.return_value = {}

        with patch(
            "blinkapp.services.blink_service.ensure_blink_connection_initialized",
            return_value=Mock(execute=Mock(return_value=[])),
        ):
            success, error, filepath = _download_cloud_clip_core(
                self.clip_id, None, Path("/tmp")
            )

        assert not success
        assert "blink instance" in error.lower()

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_download_cloud_clip_core_no_clip_found(self, mock_cache: Mock) -> None:
        """Test _download_cloud_clip_core with clip not found."""
        from blinkapp.services.clip_service import _download_cloud_clip_core

        mock_cache.return_value = {}

        mock_blink = Mock()
        mock_blink.videos = {"all": []}  # No clips

        with patch(
            "blinkapp.services.blink_service.ensure_blink_connection_initialized",
            return_value=Mock(execute=Mock(return_value=[])),
        ):
            success, error, filepath = _download_cloud_clip_core(
                self.clip_id, mock_blink, Path("/tmp")
            )

        assert not success
        assert "not found" in error.lower()

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_download_cloud_clip_cached_file_exists(self, mock_cache: Mock) -> None:
        """Test _download_cloud_clip_core with existing cached file."""
        from blinkapp.services.clip_service import _download_cloud_clip_core

        mock_filepath = Mock()
        mock_filepath.exists.return_value = True

        mock_cache_instance = {self.clip_id: {"filepath": mock_filepath}}
        mock_cache.return_value = mock_cache_instance

        mock_blink = Mock()

        with patch(
            "blinkapp.services.blink_service.ensure_blink_connection_initialized",
            return_value=Mock(execute=Mock(return_value=[])),
        ):
            success, error, filepath = _download_cloud_clip_core(
                self.clip_id, mock_blink, Path("/tmp")
            )

        assert success
        assert filepath == mock_filepath

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_download_cloud_clip_cached_file_os_error(self, mock_cache: Mock) -> None:
        """Test _download_cloud_clip_core with cached file OS error."""
        from blinkapp.services.clip_service import _download_cloud_clip_core

        mock_filepath = Mock()
        mock_filepath.exists.side_effect = OSError("Permission denied")

        mock_cache_instance = {self.clip_id: {"filepath": mock_filepath}}
        mock_cache.return_value = mock_cache_instance

        clip_info = {
            "id": "123456",
            "created_at": "2023-01-01T12:00:00Z",
            "device_name": "test_camera",
            "media": "http://example.com/video.mp4",
        }

        mock_blink = Mock()
        mock_blink.videos = {"all": [clip_info]}

        # Should continue to download since cached file check failed
        with patch("pathlib.Path.exists", return_value=False):
            with patch(
                "blinkapp.services.connection_service.ensure_http_session_initialized"
            ):
                with patch(
                    "blinkapp.services.connection_service.ensure_executor_initialized"
                ) as mock_executor:
                    mock_future = Mock()
                    mock_future.result.return_value = False
                    mock_executor_instance = Mock()
                    mock_executor_instance.submit.return_value = mock_future
                    mock_executor.return_value = mock_executor_instance

                    with patch(
                        "blinkapp.services.blink_service.ensure_blink_connection_initialized",
                        return_value=Mock(execute=Mock(return_value=[])),
                    ):
                        success, error, filepath = _download_cloud_clip_core(
                            self.clip_id, mock_blink, Path("/tmp")
                        )

                    assert not success

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_process_cloud_clips_invalid_timestamp(self, mock_cache: Mock) -> None:
        """Test process_cloud_clips with invalid timestamp."""
        from blinkapp.services.clip_service import process_cloud_clips

        mock_cache.return_value = {}

        videos_metadata: list[dict[str, object]] = [
            {
                "id": "123456",
                "created_at": "invalid_timestamp",
                "device_name": "Test Camera",
                "thumbnail": "http://example.com/thumb.jpg",
                "media": "http://example.com/video.mp4",
            }
        ]

        with patch("blinkapp.utils.validators.format_clips_by_day") as mock_format:
            mock_format.return_value = []

            result = process_cloud_clips(videos_metadata)

            # Should handle invalid timestamp gracefully
            assert result == []

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_process_local_clips_no_local_storage(self, mock_cache: Mock) -> None:
        """Test process_local_clips with no local storage."""
        from blinkapp.services.clip_service import process_local_clips

        mock_cache.return_value = {}

        mock_sync = Mock()
        mock_sync.local_storage = False

        mock_blink_instance = Mock()
        mock_blink_instance.sync = {"sync1": mock_sync}

        mock_connection = Mock()

        with patch("blinkapp.utils.validators.format_clips_by_day") as mock_format:
            mock_format.return_value = []

            result = process_local_clips(
                blink_instance=mock_blink_instance,
                blink_connection_instance=mock_connection,
            )

            assert result == []

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_process_local_clips_manifest_not_ready(self, mock_cache: Mock) -> None:
        """Test process_local_clips with manifest not ready."""
        from blinkapp.services.clip_service import process_local_clips

        mock_cache.return_value = {}

        mock_sync = Mock()
        mock_sync.local_storage = True
        mock_sync.local_storage_manifest_ready = False

        mock_blink_instance = Mock()
        mock_blink_instance.sync = {"sync1": mock_sync}

        mock_connection = Mock()

        with patch("blinkapp.utils.validators.format_clips_by_day") as mock_format:
            mock_format.return_value = []

            result = process_local_clips(
                blink_instance=mock_blink_instance,
                blink_connection_instance=mock_connection,
            )

            assert result == []

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_process_local_clips_invalid_item(self, mock_cache: Mock) -> None:
        """Test process_local_clips with invalid item in manifest."""
        from blinkapp.services.clip_service import process_local_clips

        mock_cache.return_value = {}

        # Mock item that will cause an exception
        mock_item = Mock()
        mock_item.created_at = "invalid_date"  # This will cause an error

        mock_sync = Mock()
        mock_sync.local_storage = True
        mock_sync.local_storage_manifest_ready = True
        mock_sync._local_storage = {
            "manifest": [mock_item],
            "last_manifest_id": "manifest_123",
        }
        mock_sync.refresh.return_value = None

        mock_blink_instance = Mock()
        mock_blink_instance.sync = {"sync1": mock_sync}

        mock_connection = Mock()
        mock_connection.execute = Mock()

        with patch("blinkapp.utils.validators.format_clips_by_day") as mock_format:
            with patch("blinkapp.services.clip_service.logger") as mock_logger:
                mock_format.return_value = []

                result = process_local_clips(
                    blink_instance=mock_blink_instance,
                    blink_connection_instance=mock_connection,
                )

                # Should log warning for invalid item but continue processing
                mock_logger.warning.assert_called()
                assert result == []

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_download_and_cache_cloud_thumbnail_success(self, mock_cache: Mock) -> None:
        """Test download_and_cache_cloud_thumbnail success path."""
        from blinkapp.services.clip_service import download_and_cache_cloud_thumbnail

        mock_cache_instance = {}
        mock_cache.return_value = mock_cache_instance

        # Mock session and response
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"thumbnail_data"
        mock_session.get.return_value = mock_response

        with patch(
            "blinkapp.services.connection_service.ensure_http_session_initialized",
            return_value=mock_session,
        ):
            result = download_and_cache_cloud_thumbnail(
                self.clip_id, "http://example.com/thumb.jpg"
            )

            # Should return the thumbnail path
            assert result is not None

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_download_and_cache_cloud_thumbnail_http_error(
        self, mock_cache: Mock
    ) -> None:
        """Test download_and_cache_cloud_thumbnail HTTP error."""
        from blinkapp.services.clip_service import download_and_cache_cloud_thumbnail

        mock_cache_instance = {}
        mock_cache.return_value = mock_cache_instance

        # Mock session with error response
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")
        mock_session.get.return_value = mock_response

        with patch(
            "blinkapp.services.connection_service.ensure_http_session_initialized",
            return_value=mock_session,
        ):
            result = download_and_cache_cloud_thumbnail(
                self.clip_id, "http://example.com/thumb.jpg"
            )

            assert result is None

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_download_clip_common_file_not_exists(self, mock_cache: Mock) -> None:
        """Test download_clip_common with non-existent file."""
        from blinkapp.services.clip_service import download_clip_common

        mock_filepath = Mock()
        mock_filepath.exists.return_value = False

        mock_cache.return_value = {}

        mock_jsonify = Mock(return_value="json_response")

        with patch("flask.jsonify", mock_jsonify):
            with patch(
                "blinkapp.services.connection_service.ensure_executor_initialized"
            ) as mock_executor:
                mock_executor_instance = Mock()
                mock_executor.return_value = mock_executor_instance

                mock_send_file = Mock(return_value="file_response")
                result = download_clip_common(
                    self.clip_id,
                    mock_filepath,
                    "test.mp4",
                    send_file_func=mock_send_file,
                )

                assert result[1] == 404
                mock_jsonify.assert_called_once()

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_download_clip_common_cached_file_exists(self, mock_cache: Mock) -> None:
        """Test download_clip_common with existing cached file."""
        from blinkapp.services.clip_service import download_clip_common

        # Mock cached file that exists
        mock_filepath = Mock()
        mock_filepath.exists.return_value = True
        mock_filepath.name = "test.mp4"

        mock_cache_instance = {self.clip_id: {"filepath": mock_filepath}}
        mock_cache.return_value = mock_cache_instance

        mock_send_file = Mock(return_value="file_response")

        with patch("flask.send_file", mock_send_file):
            with patch(
                "blinkapp.services.connection_service.ensure_executor_initialized"
            ) as mock_executor:
                mock_executor_instance = Mock()
                mock_executor.return_value = mock_executor_instance

                result = download_clip_common(self.clip_id, mock_filepath, "test.mp4")

                mock_send_file.assert_called_once()
                assert result[0] == "file_response"

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_process_local_clips_default_dependencies(self, mock_cache: Mock) -> None:
        """Test process_local_clips with default dependencies."""
        from blinkapp.services.clip_service import process_local_clips

        mock_cache.return_value = {}

        with patch("blinkapp.services.blink_service.blink") as mock_blink:
            with patch("blinkapp.services.blink_service.blink_connection"):
                with patch(
                    "blinkapp.utils.validators.format_clips_by_day"
                ) as mock_format:
                    mock_blink.sync = {}
                    mock_format.return_value = []

                    result = process_local_clips()

                    assert result == []

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_process_cloud_clips_empty_metadata(self, mock_cache: Mock) -> None:
        """Test process_cloud_clips with empty metadata."""
        from blinkapp.services.clip_service import process_cloud_clips

        mock_cache.return_value = {}

        with patch("blinkapp.utils.validators.format_clips_by_day") as mock_format:
            mock_format.return_value = []

            result = process_cloud_clips([])

            assert result == []

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_download_and_cache_cloud_thumbnail_exception(
        self, mock_cache: Mock
    ) -> None:
        """Test download_and_cache_cloud_thumbnail with exception."""
        from blinkapp.services.clip_service import download_and_cache_cloud_thumbnail

        mock_cache.return_value = {}

        # Mock session that raises exception
        mock_session = Mock()
        mock_session.get.side_effect = Exception("Network error")

        with patch(
            "blinkapp.services.connection_service.ensure_http_session_initialized",
            return_value=mock_session,
        ):
            result = download_and_cache_cloud_thumbnail(
                self.clip_id, "http://example.com/thumb.jpg"
            )

            assert result is None
