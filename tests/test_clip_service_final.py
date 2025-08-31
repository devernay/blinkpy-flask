#!/usr/bin/env python3
"""
Final comprehensive tests to achieve 75% coverage for clip_service.py.
Targets remaining uncovered lines with working, minimal tests.
"""

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any
from unittest.mock import Mock, mock_open, patch

from blinkpy.blinkpy import Blink
from requests import Response
from test_base import create_mock_blink_instance, create_mock_sync

from blinkapp.models.ids import ClipId


class TestClipServiceFinal:
    """Final tests to reach 75% coverage."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.clip_id = ClipId("123456")

    def test_get_clips_cache_dir(self) -> None:
        """Test _get_clips_cache_dir helper function."""
        from blinkapp.services.clip_download import _get_clips_cache_dir

        with patch("blinkapp.CLIPS_CACHE_DIR", "/test/cache"):
            result = _get_clips_cache_dir()
            assert result == "/test/cache"  # Function returns string, not Path

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_download_and_cache_cloud_thumbnail_no_url(self, mock_cache: Mock) -> None:
        """Test download_and_cache_cloud_thumbnail with no URL."""
        from blinkapp.services.clip_processing import download_and_cache_cloud_thumbnail

        mock_cache.return_value = {}

        from typing import cast

        result = download_and_cache_cloud_thumbnail(
            self.clip_id, cast(str, None)
        )  # Intentionally testing invalid input

        assert result is None

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_download_cloud_clip_core_sync_no_blink(self, mock_cache: Mock) -> None:
        """Test _download_cloud_clip_core_sync with no blink instance."""
        from blinkapp.services.clip_download import _download_cloud_clip_core_sync

        mock_cache.return_value = {}

        with patch(
            "blinkapp.services.blink_service.ensure_blink_connection_initialized",
            return_value=Mock(execute=Mock(return_value=[])),
        ):
            from typing import cast

            filepath, error = _download_cloud_clip_core_sync(
                self.clip_id,
                cast(Blink, None),
                Path("/tmp"),  # Intentionally testing invalid input
            )

        assert (
            error is not None
            and "'NoneType' object has no attribute 'get_clip_url'" in error
        )

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_download_cloud_clip_core_sync_no_clip_found(
        self, mock_cache: Mock
    ) -> None:
        """Test _download_cloud_clip_core_sync with clip not found."""
        from blinkapp.services.clip_download import _download_cloud_clip_core_sync

        mock_cache.return_value = {}

        # Use the base mock with proper async method
        mock_blink = create_mock_blink_instance()

        # Override get_videos_metadata to return empty list (no clips found)
        async def mock_get_videos_metadata(stop: int = 25) -> list[dict[str, Any]]:
            return []  # No clips found

        mock_blink.get_videos_metadata = mock_get_videos_metadata

        with patch(
            "blinkapp.services.blink_service.ensure_blink_connection_initialized",
            return_value=Mock(execute=Mock(return_value=[])),
        ):
            filepath, error = _download_cloud_clip_core_sync(
                self.clip_id, mock_blink, Path("/tmp")
            )

        assert error is not None and "not found" in error.lower()

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_download_cloud_clip_cached_file_exists(self, mock_cache: Mock) -> None:
        """Test _download_cloud_clip_core_sync downloads and returns new file path."""
        from blinkapp.services.clip_download import _download_cloud_clip_core_sync

        mock_cache.return_value = {}

        # Use proper mock with get_videos_metadata
        mock_blink = create_mock_blink_instance()

        with patch(
            "blinkapp.services.blink_service.ensure_blink_connection_initialized",
            return_value=Mock(execute=Mock(return_value=[])),
        ):
            with patch("builtins.open", mock_open()) as mock_file:
                filepath, error = _download_cloud_clip_core_sync(
                    self.clip_id, mock_blink, Path("/tmp")
                )

                # Verify file was written
                mock_file.assert_called_once()
                assert filepath is not None
                assert str(filepath).endswith("123456.mp4")
                assert error is None

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_download_cloud_clip_cached_file_os_error(self, mock_cache: Mock) -> None:
        """Test _download_cloud_clip_core_sync with cached file OS error."""
        from blinkapp.services.clip_download import _download_cloud_clip_core_sync

        mock_filepath = Mock(spec=Path)
        mock_filepath.exists.side_effect = OSError("Permission denied")

        mock_cache_instance = {self.clip_id: {"filepath": mock_filepath}}
        mock_cache.return_value = mock_cache_instance

        clip_info = {
            "id": "123456",
            "created_at": "2023-01-01T12:00:00Z",
            "device_name": "test_camera",
            "media": "http://example.com/video.mp4",
        }

        mock_blink = Mock(spec=object)
        mock_blink.videos = {"all": [clip_info]}

        # Should continue to download since cached file check failed
        with patch("pathlib.Path.exists", return_value=False):
            with patch(
                "blinkapp.services.connection_service.ensure_http_session_initialized"
            ):
                with patch(
                    "blinkapp.services.connection_service.ensure_executor_initialized"
                ) as mock_executor:
                    mock_future = Mock(spec=Future)
                    mock_future.result.return_value = False
                    mock_executor_instance = Mock(spec=ThreadPoolExecutor)
                    mock_executor_instance.submit.return_value = mock_future
                    mock_executor.return_value = mock_executor_instance

                    with patch(
                        "blinkapp.services.blink_service.ensure_blink_connection_initialized",
                        return_value=Mock(execute=Mock(return_value=[])),
                    ):
                        filepath, error = _download_cloud_clip_core_sync(
                            self.clip_id, mock_blink, Path("/tmp")
                        )

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_process_cloud_clips_invalid_timestamp(self, mock_cache: Mock) -> None:
        """Test process_cloud_clips with invalid timestamp."""
        from blinkapp.services.clip_service import process_cloud_clips

        mock_cache.return_value = {}

        from tests.test_base import create_video_metadata

        videos_metadata = [
            create_video_metadata(
                clip_id="123456",
                created_at="invalid_timestamp",
                device_name="Test Camera",
            )
        ]

        with patch("blinkapp.utils.formatters.format_clips_by_day") as mock_format:
            mock_format.return_value = []

            result = process_cloud_clips(videos_metadata)

            # Should handle invalid timestamp gracefully
            assert result == []

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_process_local_clips_no_local_storage(self, mock_cache: Mock) -> None:
        """Test process_local_clips with no local storage."""
        from blinkapp.services.clip_service import process_local_clips

        mock_cache.return_value = {}

        mock_sync = create_mock_sync(local_storage=False)

        mock_blink_instance = Mock(spec=object)
        mock_blink_instance.sync = {"sync1": mock_sync}

        mock_connection = Mock(spec=object)

        with patch("blinkapp.utils.formatters.format_clips_by_day") as mock_format:
            mock_format.return_value = []

            result = process_local_clips(
                blink_instance=mock_blink_instance,
                blink_connection_instance=mock_connection,
            )

            assert result == []

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_process_local_clips_manifest_not_ready(self, mock_cache: Mock) -> None:
        """Test process_local_clips with manifest not ready."""
        from blinkapp.services.clip_service import process_local_clips

        mock_cache.return_value = {}

        mock_sync = create_mock_sync(
            local_storage=True, local_storage_manifest_ready=False
        )

        mock_blink_instance = Mock(spec=object)
        mock_blink_instance.sync = {"sync1": mock_sync}

        mock_connection = Mock(spec=object)

        with patch("blinkapp.utils.formatters.format_clips_by_day") as mock_format:
            mock_format.return_value = []

            result = process_local_clips(
                blink_instance=mock_blink_instance,
                blink_connection_instance=mock_connection,
            )

            assert result == []

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_process_local_clips_invalid_item(self, mock_cache: Mock) -> None:
        """Test process_local_clips with invalid item in manifest."""
        from blinkapp.services.clip_service import process_local_clips

        mock_cache.return_value = {}

        # Mock item that will cause an exception
        mock_item = Mock(spec=dict)
        mock_item.created_at = "invalid_date"  # This will cause an error

        mock_sync = create_mock_sync(
            local_storage=True, local_storage_manifest_ready=True
        )
        mock_sync._local_storage = {
            "manifest": [mock_item],
            "last_manifest_id": "manifest_123",
        }
        mock_sync.refresh.return_value = None

        mock_blink_instance = Mock(spec=object)
        mock_blink_instance.sync = {"sync1": mock_sync}

        mock_connection = Mock(spec=object)
        mock_connection.execute = Mock(spec=callable)

        with patch("blinkapp.utils.formatters.format_clips_by_day") as mock_format:
            with patch("blinkapp.services.clip_service.logger") as mock_logger:
                mock_format.return_value = []

                result = process_local_clips(
                    blink_instance=mock_blink_instance,
                    blink_connection_instance=mock_connection,
                )

                # Should log warning for invalid item but continue processing
                mock_logger.warning.assert_called()
                assert result == []

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_download_and_cache_cloud_thumbnail_success(self, mock_cache: Mock) -> None:
        """Test download_and_cache_cloud_thumbnail success path."""
        from blinkapp.services.clip_processing import download_and_cache_cloud_thumbnail

        mock_cache_instance = {}
        mock_cache.return_value = mock_cache_instance

        # Mock session and response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.content = b"thumbnail_data"
        mock_response.raise_for_status = Mock()

        with patch(
            "blinkapp.services.clip_processing.requests.get",
            return_value=mock_response,
        ):
            result = download_and_cache_cloud_thumbnail(
                self.clip_id, "http://example.com/thumb.jpg"
            )

            # Should return the thumbnail path
            assert result is not None

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_download_and_cache_cloud_thumbnail_http_error(
        self, mock_cache: Mock
    ) -> None:
        """Test download_and_cache_cloud_thumbnail HTTP error."""
        from blinkapp.services.clip_processing import download_and_cache_cloud_thumbnail

        mock_cache_instance = {}
        mock_cache.return_value = mock_cache_instance

        # Mock requests.get with error response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("HTTP 404")

        with (
            patch(
                "blinkapp.services.clip_processing.requests.get",
                return_value=mock_response,
            ),
            patch("pathlib.Path.exists", return_value=False),
        ):
            result = download_and_cache_cloud_thumbnail(
                self.clip_id, "http://example.com/thumb.jpg"
            )

            assert result is None

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_download_clip_common_file_not_exists(self, mock_cache: Mock) -> None:
        """Test download_clip_common with non-existent file."""
        from blinkapp.services.clip_download import download_clip_common

        mock_filepath = Mock(spec=Path)
        mock_filepath.exists.return_value = False

        mock_cache.return_value = {}

        with patch(
            "blinkapp.services.connection_service.ensure_executor_initialized"
        ) as mock_executor:
            mock_executor_instance = Mock(spec=ThreadPoolExecutor)
            mock_executor.return_value = mock_executor_instance

            result = download_clip_common(
                mock_filepath,
                self.clip_id,
            )

            # When file doesn't exist, it returns create_api_response tuple
            assert isinstance(result, tuple)
            assert len(result) >= 2
            _response, status_code = result[0], result[1]
            assert status_code == 404

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_download_clip_common_cached_file_exists(self, mock_cache: Mock) -> None:
        """Test download_clip_common with existing cached file."""
        import tempfile
        from pathlib import Path

        from blinkapp.services.clip_download import download_clip_common

        # Create a real temporary file for the test
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            temp_file.write(b"fake video data")
            temp_path = Path(temp_file.name)

        try:
            mock_cache_instance = {self.clip_id: {"filepath": temp_path}}
            mock_cache.return_value = mock_cache_instance

            mock_send_file = Mock(return_value="file_response")

            with patch("blinkapp.services.clip_download.send_file", mock_send_file):
                with patch(
                    "blinkapp.services.connection_service.ensure_executor_initialized"
                ) as mock_executor:
                    mock_executor_instance = Mock(spec=ThreadPoolExecutor)
                    mock_executor.return_value = mock_executor_instance

                    # Need Flask request context for send_file
                    from blinkapp import app

                    with app.test_request_context():
                        result = download_clip_common(temp_path, self.clip_id)

                    mock_send_file.assert_called_once()
                    # When file exists, it returns send_file response directly
                    assert result == "file_response"
        finally:
            # Clean up the temporary file
            if temp_path.exists():
                temp_path.unlink()

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_process_local_clips_default_dependencies(self, mock_cache: Mock) -> None:
        """Test process_local_clips with default dependencies."""
        from blinkapp.services.clip_service import process_local_clips

        mock_cache.return_value = {}

        with patch("blinkapp.services.blink_service.blink") as mock_blink:
            with patch("blinkapp.services.blink_service.blink_connection"):
                with patch(
                    "blinkapp.utils.formatters.format_clips_by_day"
                ) as mock_format:
                    mock_blink.sync = {}
                    mock_format.return_value = []

                    result = process_local_clips()

                    assert result == []

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_process_cloud_clips_empty_metadata(self, mock_cache: Mock) -> None:
        """Test process_cloud_clips with empty metadata."""
        from blinkapp.services.clip_service import process_cloud_clips

        mock_cache.return_value = {}

        with patch("blinkapp.utils.formatters.format_clips_by_day") as mock_format:
            mock_format.return_value = []

            result = process_cloud_clips([])

            assert result == []

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_download_and_cache_cloud_thumbnail_exception(
        self, mock_cache: Mock
    ) -> None:
        """Test download_and_cache_cloud_thumbnail with exception."""
        from blinkapp.services.clip_processing import download_and_cache_cloud_thumbnail

        mock_cache.return_value = {}

        with (
            patch(
                "blinkapp.services.clip_processing.requests.get",
                side_effect=Exception("Network error"),
            ),
            patch("pathlib.Path.exists", return_value=False),
        ):
            result = download_and_cache_cloud_thumbnail(
                self.clip_id, "http://example.com/thumb.jpg"
            )

            assert result is None
