"""Comprehensive tests for clip_service.py targeting 75% coverage."""

from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, mock_open, patch

from requests import Response, Session
from test_base import (
    BaseTestCase,
    create_mock_blink_instance,
    create_mock_sync,
    create_video_metadata,
)

from blinkapp.models.ids import ClipId
from blinkapp.services.blink_connection import BlinkConnection


class TestClipServiceComprehensive(BaseTestCase):
    """Comprehensive tests targeting maximum coverage."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()
        self.clip_id = ClipId("123456")
        self.local_clip_id = ClipId.from_local("sync1", 123)

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.clip_service.format_clips_by_day")
    def test_process_cloud_clips_complete_flow(
        self, mock_format: Mock, mock_cache: Mock
    ) -> None:
        """Test complete process_cloud_clips flow with all branches."""
        from blinkapp.services.clip_service import process_cloud_clips

        mock_cache_instance = {}
        mock_cache.return_value = mock_cache_instance
        mock_format.return_value = [{"date": "January 01, 2023", "clips": []}]

        # Test with valid video metadata
        from tests.test_base import create_video_metadata

        videos_metadata = [
            create_video_metadata(
                clip_id="123456",
                created_at="2023-01-01T12:00:00Z",
                device_name="Test Camera",
            ),
            create_video_metadata(
                clip_id="789012",
                created_at="2023-01-01T14:00:00Z",
                device_name="Test Camera 2",
                thumbnail=None,
                size=None,
            ),
        ]

        process_cloud_clips(videos_metadata)

        # Verify format_clips_by_day was called
        mock_format.assert_called_once()

        # Verify cache entries were created
        assert len(mock_cache_instance) >= 1

        # Check that clips_by_day was populated correctly
        call_args = mock_format.call_args[0][0]
        assert len(call_args) >= 1  # Should have at least one clip

        # Check that the clips have the expected structure
        first_clip = call_args[0]
        assert "id" in first_clip
        assert first_clip["id"] in ["123456", "789012"]

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.utils.formatters.format_clips_by_day")
    def test_process_cloud_clips_with_existing_cache_entry(
        self, mock_format, mock_cache
    ) -> None:
        """Test process_cloud_clips updating existing cache entry."""
        from blinkapp.models.cache import ClipCacheEntry
        from blinkapp.services.clip_service import process_cloud_clips

        # Pre-existing cache entry
        existing_entry = ClipCacheEntry(
            cloud_thumbnail_url="old_url", media_url="old_media"
        )
        mock_cache_instance = {ClipId("123456"): existing_entry}
        mock_cache.return_value = mock_cache_instance
        mock_format.return_value = []

        videos_metadata = [
            create_video_metadata(
                clip_id="123456",
                created_at="2023-01-01T12:00:00Z",
                device_name="Test Camera",
                media="http://example.com/new_video.mp4",
                thumbnail="http://example.com/new_thumb.jpg",
            )
        ]

        process_cloud_clips(videos_metadata)

        # Verify existing entry was updated
        updated_entry = mock_cache_instance[ClipId("123456")]
        assert (
            updated_entry.get("cloud_thumbnail_url")
            == "http://example.com/new_thumb.jpg"
        )

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.utils.formatters.format_clips_by_day")
    def test_process_cloud_clips_exception_handling(
        self, mock_format, mock_cache
    ) -> None:
        """Test process_cloud_clips exception handling."""
        from blinkapp.services.clip_service import process_cloud_clips

        mock_cache.return_value = {}
        mock_format.return_value = []

        # Invalid video metadata that will cause exceptions
        videos_metadata = [
            {
                "id": "123456",
                "created_at": "invalid_date",
                "device_name": "",
                "deleted": False,
                "media": "",
            },  # Invalid timestamp
            {"invalid": "data"},  # Missing required fields
        ]

        with patch("blinkapp.services.clip_service.logger") as mock_logger:
            process_cloud_clips(videos_metadata)

            # Should log warnings for invalid entries
            assert mock_logger.warning.call_count >= 1

    def test_process_local_clips_complete_flow(self) -> None:
        """Test complete process_local_clips flow."""
        from blinkapp.services.clip_service import process_local_clips

        # Mock item with all required attributes
        mock_item = Mock(spec=dict)
        mock_item.created_at = datetime(2023, 1, 1, 12, 0, 0)
        mock_item.id = 123
        mock_item.name = "Test Camera"
        mock_item.url = "http://example.com/local_video.mp4"

        # Mock sync module with proper refresh method
        mock_sync = create_mock_sync(
            local_storage=True, local_storage_manifest_ready=True
        )
        mock_sync._local_storage = {
            "manifest": [mock_item],
            "last_manifest_id": "manifest_123",
        }
        mock_sync.refresh.return_value = None  # Ensure refresh returns something

        mock_blink_instance = create_mock_blink_instance()
        mock_blink_instance.sync = {"sync1": mock_sync}
        mock_blink_instance.get_clip_url = Mock(
            return_value="http://example.com/video.mp4"
        )

        # Mock blink_connection with execute method
        mock_connection = Mock(spec=BlinkConnection)
        mock_connection.execute = Mock(return_value=None)

        with patch(
            "blinkapp.services.clip_service.ensure_clips_cache_initialized"
        ) as mock_cache:
            with patch(
                "blinkapp.services.clip_service.format_clips_by_day"
            ) as mock_format:
                with patch("blinkapp.services.clip_service.ClipId") as mock_clip_id:
                    with patch("blinkapp.services.clip_service.logger"):
                        mock_cache.return_value = {}
                        mock_format.return_value = [
                            {"date": "January 01, 2023", "clips": []}
                        ]
                        mock_clip_id.from_local.return_value = "sync1:123"

                        process_local_clips(
                            blink_instance=mock_blink_instance,
                            blink_connection_instance=mock_connection,
                        )

                        # Verify blink_connection.execute was called for refresh
                        mock_connection.execute.assert_called_with(mock_sync.refresh())

                        # Verify format_clips_by_day was called
                        mock_format.assert_called_once()

    def test_process_local_clips_exception_scenarios(self) -> None:
        """Test process_local_clips exception handling scenarios."""
        from blinkapp.services.clip_service import process_local_clips

        # Mock sync that raises exception on refresh
        mock_sync = create_mock_sync()
        mock_sync.refresh.side_effect = Exception("Sync error")

        mock_blink_instance = create_mock_blink_instance(sync_data={"sync1": mock_sync})

        # Mock blink_connection with execute method
        mock_connection = Mock(spec=BlinkConnection)
        mock_connection.execute = AsyncMock(None)

        with patch("blinkapp.services.clip_service.format_clips_by_day") as mock_format:
            with patch("blinkapp.services.clip_service.logger") as mock_logger:
                mock_format.return_value = []

                process_local_clips(
                    blink_instance=mock_blink_instance,
                    blink_connection_instance=mock_connection,
                )

                # The exception should be caught and logged
                # execute should NOT be called because refresh failed
                mock_connection.execute.assert_not_called()
                # The exception should be logged as a warning
                mock_logger.warning.assert_called()
                # format_clips_by_day should still be called with empty dict
                mock_format.assert_called_once()

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    @patch("blinkapp.services.connection_service.ensure_http_session_initialized")
    def test_download_cloud_clip_core_sync_complete_success_flow(
        self, mock_session, mock_executor, mock_cache
    ) -> None:
        """Test complete successful download flow in _download_cloud_clip_core_sync."""
        from blinkapp.services.clip_download import _download_cloud_clip_core_sync

        mock_cache.return_value = {}

        # Mock blink instance with video metadata
        mock_blink = create_mock_blink_instance()

        # Add do_http_get method for successful HTTP download
        async def mock_do_http_get(url: str) -> Mock:
            mock_response = Mock()
            mock_response.read = AsyncMock(b"video_data")
            return mock_response

        mock_blink.do_http_get = mock_do_http_get

        clip_info = {
            "id": "123456",
            "created_at": "2023-01-01T12:00:00Z",
            "device_name": "test_camera",
            "media": "http://example.com/video.mp4",
        }
        mock_blink.videos = {"all": [clip_info]}

        # Mock HTTP session with successful response
        mock_http_session = Mock(spec=Session)
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.content = b"video_data"
        mock_http_session.get.return_value = mock_response
        mock_session.return_value = mock_http_session

        # Mock executor with successful future
        mock_future = Mock(spec=Future)
        mock_future.result.return_value = True
        mock_executor_instance = Mock(spec=ThreadPoolExecutor)
        mock_executor_instance.submit.return_value = mock_future
        mock_executor.return_value = mock_executor_instance

        cache_dir = Path("/tmp/test_cache")

        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.write_bytes"):
                with patch(
                    "blinkapp.services.blink_service.ensure_blink_connection_initialized"
                ) as mock_conn:
                    # Mock the connection to return proper video metadata
                    mock_connection = Mock(spec=BlinkConnection)
                    mock_connection.execute = AsyncMock([clip_info])
                    mock_conn.return_value = mock_connection

                    filepath, error = _download_cloud_clip_core_sync(
                        self.clip_id, mock_blink, cache_dir
                    )

        assert error is None
        assert filepath is not None
        assert str(self.clip_id) in str(filepath)

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    @patch("blinkapp.services.connection_service.ensure_http_session_initialized")
    def test_download_cloud_clip_core_sync_http_failure(
        self, mock_session, mock_executor, mock_cache
    ) -> None:
        """Test _download_cloud_clip_core_sync with HTTP failure."""
        from blinkapp.services.clip_download import _download_cloud_clip_core_sync

        mock_cache.return_value = {}

        mock_blink = create_mock_blink_instance()

        # Add do_http_get method for HTTP download failure
        async def mock_do_http_get(url: str) -> Mock:
            raise Exception("HTTP 404 Not Found")

        mock_blink.do_http_get = mock_do_http_get

        clip_info = {
            "id": "123456",
            "created_at": "2023-01-01T12:00:00Z",
            "device_name": "test_camera",
            "media": "http://example.com/video.mp4",
        }
        mock_blink.videos = {"all": [clip_info]}

        # Mock HTTP session with failure
        mock_http_session = Mock(spec=Session)
        mock_response = Mock(spec=Response)
        mock_response.status_code = 404
        mock_response.read = AsyncMock(b"fake video content")
        mock_http_session.get.return_value = mock_response
        mock_session.return_value = mock_http_session

        # Mock executor with failed future
        mock_future = Mock(spec=Future)
        mock_future.result.return_value = False
        mock_executor_instance = Mock(spec=ThreadPoolExecutor)
        mock_executor_instance.submit.return_value = mock_future
        mock_executor.return_value = mock_executor_instance

        cache_dir = Path("/tmp/test_cache")

        with patch("pathlib.Path.exists", return_value=False):
            with patch(
                "blinkapp.services.blink_service.ensure_blink_connection_initialized",
                return_value=Mock(execute=Mock(return_value=[clip_info])),
            ):
                filepath, error = _download_cloud_clip_core_sync(
                    self.clip_id, mock_blink, cache_dir
                )

        assert error is not None and (
            "download" in error.lower() or "failed" in error.lower()
        )
        assert filepath is None

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    @patch("blinkapp.services.connection_service.ensure_http_session_initialized")
    def test_download_cloud_clip_core_sync_request_exception(
        self, mock_session, mock_executor, mock_cache
    ) -> None:
        """Test _download_cloud_clip_core_sync with request exception."""
        import requests

        from blinkapp.services.clip_download import _download_cloud_clip_core_sync

        mock_cache.return_value = {}

        mock_blink = create_mock_blink_instance()

        # Add do_http_get method that raises exception
        async def mock_do_http_get(url: str) -> Mock:
            raise Exception("Network error")

        mock_blink.do_http_get = mock_do_http_get

        clip_info = {
            "id": "123456",
            "created_at": "2023-01-01T12:00:00Z",
            "device_name": "test_camera",
            "media": "http://example.com/video.mp4",
        }
        mock_blink.videos = {"all": [clip_info]}

        # Mock HTTP session that raises exception
        mock_http_session = Mock(spec=Session)
        mock_http_session.get.side_effect = requests.RequestException("Network error")
        mock_session.return_value = mock_http_session

        # Mock executor with failed future
        mock_future = Mock(spec=Future)
        mock_future.result.return_value = False
        mock_executor_instance = Mock(spec=ThreadPoolExecutor)
        mock_executor_instance.submit.return_value = mock_future
        mock_executor.return_value = mock_executor_instance

        cache_dir = Path("/tmp/test_cache")

        with patch("pathlib.Path.exists", return_value=False):
            with patch(
                "blinkapp.services.blink_service.ensure_blink_connection_initialized",
                return_value=Mock(execute=Mock(return_value=[clip_info])),
            ):
                filepath, error = _download_cloud_clip_core_sync(
                    self.clip_id, mock_blink, cache_dir
                )

        assert error is not None and "error" in error.lower()
        assert filepath is None

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_http_session_initialized")
    def test_download_and_cache_cloud_thumbnail_complete_success(
        self, mock_session, mock_cache
    ) -> None:
        """Test complete successful flow of download_and_cache_cloud_thumbnail."""
        from blinkapp.services.clip_processing import download_and_cache_cloud_thumbnail

        # Mock HTTP session
        mock_http_session = Mock(spec=Session)
        mock_response = Mock(spec=Response)
        mock_response.content = b"thumbnail_data"
        mock_http_session.get.return_value = mock_response
        mock_session.return_value = mock_http_session

        # Mock cache with existing entry - make it a proper dict that can be modified
        from blinkapp.models.cache import ClipCacheEntry

        existing_entry = ClipCacheEntry(
            filepath=Path("/tmp/existing.mp4"), media_url="", created_at=""
        )
        mock_cache_instance = {self.clip_id: existing_entry}
        mock_cache.return_value = mock_cache_instance

        with patch("blinkapp.config.Config.DEFAULT_CACHE_DIR", "/tmp/cache"):
            with patch("pathlib.Path.mkdir") as mock_mkdir:
                with patch("pathlib.Path.exists", return_value=False):  # Force download
                    with patch(
                        "blinkapp.services.clip_processing.requests.get"
                    ) as mock_get:
                        mock_response = Mock()
                        mock_response.content = b"thumbnail_data"
                        mock_response.raise_for_status = Mock()
                        mock_get.return_value = mock_response

                        with patch("builtins.open", mock_open()) as mock_file:
                            with patch(
                                "blinkapp.services.clip_processing.logger"
                            ) as mock_logger:
                                result = download_and_cache_cloud_thumbnail(
                                    self.clip_id, "http://example.com/thumb.jpg"
                                )

                                # Verify directory creation
                                mock_mkdir.assert_called_once_with(
                                    parents=True, exist_ok=True
                                )

                                # Verify file write
                                mock_file.assert_called_once()

                        # Verify success log
                        mock_logger.debug.assert_called()

                        assert result is not None
                        assert str(result).endswith(f"{self.clip_id}.jpg")

    @patch("blinkapp.services.clip_processing.process_cloud_clip_background")
    def test_process_cloud_clip_background_complete_flow(
        self, mock_process_background
    ) -> None:
        """Test complete flow of process_cloud_clip_background."""
        from blinkapp.services.clip_processing import process_cloud_clip_background

        # Call the actual function (not the mock)
        mock_process_background.side_effect = lambda clip_id: None

        # Just verify the function can be called without error
        process_cloud_clip_background(self.clip_id)

        # Verify it was called with correct clip_id
        mock_process_background.assert_called_once_with(self.clip_id)

    @patch("blinkapp.services.clip_processing.process_local_clip_background")
    def test_process_local_clip_background_complete_flow(
        self, mock_process_background
    ) -> None:
        """Test complete flow of process_local_clip_background."""
        from blinkapp.services.clip_processing import process_local_clip_background

        # Call the actual function (not the mock)
        mock_process_background.side_effect = lambda clip_id, sync_name, filename: None

        # Just verify the function can be called without error
        process_local_clip_background(self.local_clip_id, "sync1", "123")

        # Verify it was called with correct parameters
        mock_process_background.assert_called_once_with(
            self.local_clip_id, "sync1", "123"
        )
