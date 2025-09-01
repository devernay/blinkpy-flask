"""Tests for clip processing functions in clip_service.py."""

from datetime import datetime
from unittest.mock import Mock, patch

from blinkapp.models.ids import ClipId

from .test_base import (
    BaseTestCase,
    create_mock_blink_instance,
    create_mock_cache_instance,
    create_mock_clip_item,
    create_mock_sync,
)


class TestClipProcessingFunctions(BaseTestCase):
    """Tests for process_cloud_clips and process_local_clips functions."""

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.clip_service.format_clips_by_day")
    def test_process_cloud_clips_with_valid_data(
        self, mock_format: Mock, mock_cache: Mock
    ) -> None:
        """Test cloud clips processing with complete video metadata.

        Why: This tests the main success path for displaying user's cloud-stored videos.
        What: Verifies proper processing of video metadata into UI-ready clip data.
        How: Provides complete metadata with all fields and validates processing pipeline.
        """
        from blinkapp.services.clip_service import process_cloud_clips

        mock_cache.return_value = {}
        mock_format.return_value = [{"date": "January 01, 2023", "clips": []}]

        videos_metadata: list[dict[str, str | int | bool | None]] = [
            {
                "id": "123456",
                "created_at": "2023-01-01T12:00:00Z",
                "device_name": "Test Camera",
                "thumbnail": "http://example.com/thumb.jpg",
                "media": "http://example.com/video.mp4",
                "deleted": False,
            }
        ]

        result = process_cloud_clips(videos_metadata)
        assert len(result) == 1
        # Verify format_clips_by_day was called with processed data
        mock_format.assert_called_once()
        call_args = mock_format.call_args[0][0]
        # call_args should be a list of processed clips
        assert len(call_args) == 1
        # Check that the clip has the expected fields
        clip = call_args[0]
        assert clip["id"] == "123456"
        assert clip["camera_name"] == "Test Camera"

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    @patch("blinkapp.utils.formatters.format_clips_by_day")
    def test_process_cloud_clips_invalid_timestamp(
        self, mock_format, mock_cache
    ) -> None:
        """Test cloud clips processing with malformed timestamp data.

        Why: Blink API can return corrupted timestamps that break date parsing.
        What: Verifies graceful handling of invalid timestamp formats without crashing.
        How: Provides metadata with malformed timestamp and validates error handling.
        """
        from blinkapp.services.clip_service import process_cloud_clips

        mock_cache.return_value = {}
        mock_format.return_value = []

        videos_metadata: list[dict[str, str | int | bool | None]] = [
            {
                "id": "123456",
                "created_at": "invalid_timestamp",
                "device_name": "Test Camera",
            }
        ]

        with patch("blinkapp.services.clip_service.logger") as mock_logger:
            process_cloud_clips(videos_metadata)
            mock_logger.warning.assert_called()

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.utils.formatters.format_clips_by_day")
    def test_process_cloud_clips_with_cached_clip(
        self, mock_format, mock_cache
    ) -> None:
        """Test process_cloud_clips with existing cached clip."""
        from blinkapp.services.clip_service import process_cloud_clips

        clip_id = ClipId("123456")
        cached_clip_data = {"cloud_thumbnail_url": "existing_url"}

        # Create mock cache with initial data
        mock_cache_obj = create_mock_cache_instance({str(clip_id): cached_clip_data})
        mock_cache.return_value = mock_cache_obj
        mock_format.return_value = []

        videos_metadata: list[dict[str, str | int | bool | None]] = [
            {
                "id": "123456",
                "created_at": "2023-01-01T12:00:00Z",
                "device_name": "Test Camera",
                "thumbnail": "http://example.com/thumb.jpg",
                "media": "http://example.com/video.mp4",
                "deleted": False,
            }
        ]

        process_cloud_clips(videos_metadata)

        # Verify cached clip was updated - get the updated data from the mock cache
        updated_clip = mock_cache_obj.get(clip_id)
        assert updated_clip is not None
        assert updated_clip["cloud_thumbnail_url"] == "http://example.com/thumb.jpg"

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.utils.formatters.format_clips_by_day")
    def test_process_local_clips_no_blink(
        self, mock_format, mock_connection, mock_blink
    ) -> None:
        """Test process_local_clips with no blink instance."""
        from blinkapp.services.clip_service import process_local_clips

        mock_blink.return_value = None
        mock_format.return_value = []

        result = process_local_clips()
        assert result == []

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.clip_service.format_clips_by_day")
    def test_process_local_clips_with_data(
        self, mock_format, mock_cache, mock_connection, mock_blink
    ) -> None:
        """Test process_local_clips with valid data."""
        from blinkapp.services.clip_service import process_local_clips

        # Mock sync module with local storage
        mock_item = create_mock_clip_item()
        mock_item.created_at = datetime(2023, 1, 1, 12, 0, 0)
        mock_item.id = 123
        mock_item.name = "Test Camera"
        mock_item.url.return_value = "http://example.com/local_video.mp4"

        mock_sync = create_mock_sync(
            local_storage=True, local_storage_manifest_ready=True
        )
        mock_sync._local_storage = {
            "manifest": [mock_item],
            "last_manifest_id": "manifest_123",
        }

        mock_blink_instance = create_mock_blink_instance(sync_data={"sync1": mock_sync})
        mock_blink.return_value = mock_blink_instance

        mock_cache.return_value = {}
        mock_format.return_value = [{"date": "January 01, 2023", "clips": []}]

        result = process_local_clips()
        assert len(result) == 1
        mock_format.assert_called_once()

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.clip_service.format_clips_by_day")
    def test_process_local_clips_sync_error(
        self, mock_format, mock_connection, mock_blink
    ) -> None:
        """Test process_local_clips with sync module error."""
        from blinkapp.services.clip_service import process_local_clips

        mock_sync = create_mock_sync()
        mock_sync.refresh.side_effect = Exception("Sync error")

        mock_blink.sync = {"sync1": mock_sync}

        mock_format.return_value = []

        with patch("blinkapp.services.clip_service.logger") as mock_logger:
            process_local_clips()
            # The error should be logged but processing should continue
            mock_logger.warning.assert_called()

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    @patch("blinkapp.utils.formatters.format_clips_by_day")
    def test_process_local_clips_no_local_storage(
        self, mock_format, mock_cache, mock_connection, mock_blink
    ) -> None:
        """Test local clips processing when USB storage is unavailable.

        Why: Users may disconnect USB storage or it may fail, breaking local clip access.
        What: Verifies system handles missing local storage gracefully without errors.
        How: Mocks sync without local storage and validates empty result handling.
        """
        from blinkapp.services.clip_service import process_local_clips

        mock_sync = create_mock_sync(local_storage=False)
        mock_blink_instance = create_mock_blink_instance(sync_data={"sync1": mock_sync})
        mock_blink.return_value = mock_blink_instance

        mock_cache.return_value = {}
        mock_format.return_value = []

        result = process_local_clips()
        assert result == []

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    @patch("blinkapp.utils.formatters.format_clips_by_day")
    def test_process_local_clips_manifest_not_ready(
        self, mock_format, mock_cache, mock_connection, mock_blink
    ) -> None:
        """Test local clips processing when manifest file is not ready.

        Why: Local storage manifest can be corrupted or still being written during access.
        What: Verifies system handles manifest read failures without crashing.
        How: Mocks sync with manifest_ready=False and validates error handling.
        """
        from blinkapp.services.clip_service import process_local_clips

        mock_sync = create_mock_sync(
            local_storage=True, local_storage_manifest_ready=False
        )
        mock_blink_instance = create_mock_blink_instance(sync_data={"sync1": mock_sync})
        mock_blink.return_value = mock_blink_instance

        mock_cache.return_value = {}
        mock_format.return_value = []

        result = process_local_clips()
        assert result == []

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.clip_service.format_clips_by_day")
    def test_process_local_clips_invalid_item(
        self, mock_format, mock_cache, mock_connection, mock_blink
    ) -> None:
        """Test process_local_clips with invalid item in manifest."""
        from blinkapp.services.clip_service import process_local_clips

        # Mock item that will cause an exception
        mock_item = create_mock_clip_item()
        mock_created_at = Mock()
        mock_created_at.strftime.side_effect = AttributeError("Invalid date")
        mock_item.created_at = mock_created_at
        mock_item.id = "test_id"
        mock_item.name = "test_camera"

        mock_sync = create_mock_sync(
            local_storage=True,
            local_storage_manifest_ready=True,
            _local_storage={
                "manifest": [mock_item],
                "last_manifest_id": "manifest_123",
            },
        )
        # Add refresh method that returns a mock coroutine
        mock_sync.refresh = Mock(return_value=Mock())

        mock_blink_instance = create_mock_blink_instance(sync_data={"sync1": mock_sync})
        mock_blink.return_value = mock_blink_instance

        mock_cache.return_value = {}
        mock_format.return_value = []

        # Mock the connection execute method
        mock_connection.return_value.execute = Mock()

        with patch("blinkapp.services.clip_service.logger") as mock_logger:
            process_local_clips(
                blink_instance=mock_blink_instance,
                blink_connection_instance=mock_connection.return_value,
            )
            # Should log warning for invalid item but continue processing
            mock_logger.warning.assert_called()
