"""Tests for clip processing functions in clip_service.py."""

from datetime import datetime
from unittest.mock import Mock, patch

from blinkapp.models.ids import ClipId


class TestClipProcessingFunctions:
    """Tests for process_cloud_clips and process_local_clips functions."""

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_process_cloud_clips_empty_metadata(self, mock_cache: Mock) -> None:
        """Test process_cloud_clips with empty metadata."""
        from blinkapp.services.clip_service import process_cloud_clips

        mock_cache.return_value = {}
        result = process_cloud_clips([])
        assert result == []

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.clip_service.format_clips_by_day")
    def test_process_cloud_clips_with_valid_data(
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
        # Verify format_clips_by_day was called with processed data
        mock_format.assert_called_once()
        call_args = mock_format.call_args[0][0]
        assert "2023-01-01" in call_args

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.utils.validators.format_clips_by_day")
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

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.utils.validators.format_clips_by_day")
    def test_process_cloud_clips_with_cached_clip(
        self, mock_format, mock_cache
    ) -> None:
        """Test process_cloud_clips with existing cached clip."""
        from blinkapp.services.clip_service import process_cloud_clips

        clip_id = ClipId("123456")
        mock_cache_instance = {clip_id: {"cloud_thumbnail_url": "existing_url"}}
        mock_cache.return_value = mock_cache_instance
        mock_format.return_value = []

        videos_metadata: list[dict[str, object]] = [
            {
                "id": "123456",
                "created_at": "2023-01-01T12:00:00Z",
                "device_name": "Test Camera",
                "thumbnail": "http://example.com/thumb.jpg",
                "media": "http://example.com/video.mp4",
            }
        ]

        process_cloud_clips(videos_metadata)

        # Verify cached clip was updated
        updated_clip = mock_cache_instance[clip_id]
        assert updated_clip["cloud_thumbnail_url"] == "http://example.com/thumb.jpg"

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.utils.validators.format_clips_by_day")
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

        mock_blink_instance = Mock()
        mock_blink_instance.sync = {"sync1": mock_sync}
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
    ):
        """Test process_local_clips with sync module error."""
        from blinkapp.services.clip_service import process_local_clips

        mock_sync = Mock()
        mock_sync.refresh.side_effect = Exception("Sync error")

        mock_blink.sync = {"sync1": mock_sync}

        mock_format.return_value = []

        with patch("blinkapp.services.clip_service.logger") as mock_logger:
            process_local_clips()
            # The error should be logged but processing should continue
            mock_logger.warning.assert_called()

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.utils.validators.format_clips_by_day")
    def test_process_local_clips_no_local_storage(
        self, mock_format, mock_cache, mock_connection, mock_blink
    ):
        """Test process_local_clips with sync module that has no local storage."""
        from blinkapp.services.clip_service import process_local_clips

        mock_sync = Mock()
        mock_sync.local_storage = False

        mock_blink_instance = Mock()
        mock_blink_instance.sync = {"sync1": mock_sync}
        mock_blink.return_value = mock_blink_instance

        mock_cache.return_value = {}
        mock_format.return_value = []

        result = process_local_clips()
        assert result == []

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.utils.validators.format_clips_by_day")
    def test_process_local_clips_manifest_not_ready(
        self, mock_format, mock_cache, mock_connection, mock_blink
    ):
        """Test process_local_clips with manifest not ready."""
        from blinkapp.services.clip_service import process_local_clips

        mock_sync = Mock()
        mock_sync.local_storage = True
        mock_sync.local_storage_manifest_ready = False

        mock_blink_instance = Mock()
        mock_blink_instance.sync = {"sync1": mock_sync}
        mock_blink.return_value = mock_blink_instance

        mock_cache.return_value = {}
        mock_format.return_value = []

        result = process_local_clips()
        assert result == []

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.clip_service.format_clips_by_day")
    def test_process_local_clips_invalid_item(
        self, mock_format, mock_cache, mock_connection, mock_blink
    ):
        """Test process_local_clips with invalid item in manifest."""
        from blinkapp.services.clip_service import process_local_clips

        # Mock item that will cause an exception
        mock_item = Mock()
        mock_item.created_at.strftime.side_effect = AttributeError("Invalid date")
        mock_item.id = "test_id"
        mock_item.name = "test_camera"

        mock_sync = Mock()
        mock_sync.local_storage = True
        mock_sync.local_storage_manifest_ready = True
        mock_sync._local_storage = {
            "manifest": [mock_item],
            "last_manifest_id": "manifest_123",
        }

        mock_blink.sync = {"sync1": mock_sync}

        mock_cache.return_value = {}
        mock_format.return_value = []

        with patch("blinkapp.services.clip_service.logger") as mock_logger:
            process_local_clips()
            # Should log warning for invalid item but continue processing
            mock_logger.warning.assert_called()
