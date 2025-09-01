"""Core logic tests for clip_service.py - targeting maximum coverage without Flask context issues."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

from blinkapp.models.ids import ClipId

from .test_base import BaseTestCase, create_mock_blink_instance


class TestClipServiceCoreLogic(BaseTestCase):
    """Tests focusing on core business logic without Flask dependencies."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()
        """Set up test fixtures."""
        self.clip_id = ClipId("123456")
        self.mock_blink = create_mock_blink_instance()
        self.mock_cache_dir = Path("/tmp/test_cache")

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_download_cloud_clip_core_sync_no_blink_instance(
        self, mock_cache: Mock
    ) -> None:
        """Test _download_cloud_clip_core_sync with no blink instance."""
        from blinkapp.services.clip_download import _download_cloud_clip_core_sync

        filepath, error = _download_cloud_clip_core_sync(
            self.clip_id, None, self.mock_cache_dir
        )

        assert filepath is None
        assert error is not None
        assert "'NoneType' object has no attribute 'get_clip_url'" in error

    def test_download_cloud_clip_core_sync_cached_file_exists(self) -> None:
        """Test _download_cloud_clip_core_sync successful download."""
        from blinkapp.services.clip_download import _download_cloud_clip_core_sync

        # Add do_http_get method for successful HTTP download
        async def mock_do_http_get(url: str) -> Mock:
            mock_response = Mock()
            mock_response.read = AsyncMock(return_value=b"fake video content")
            return mock_response

        self.mock_blink.do_http_get = mock_do_http_get

        # Mock cache directory
        with (
            patch("pathlib.Path.mkdir"),
            patch("builtins.open", create=True) as mock_open,
        ):
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            filepath, error = _download_cloud_clip_core_sync(
                self.clip_id, self.mock_blink, self.mock_cache_dir
            )

            assert error is None
            assert filepath is not None
            mock_file.write.assert_called_once_with(b"fake video content")

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_download_cloud_clip_core_sync_cached_file_os_error(
        self, mock_cache: Mock
    ) -> None:
        """Test _download_cloud_clip_core_sync with OSError on cached file check."""
        from blinkapp.services.clip_download import _download_cloud_clip_core_sync

        mock_filepath = Mock(spec=Path)
        mock_filepath.exists.side_effect = OSError("File access error")
        mock_cache_instance = {self.clip_id: {"filepath": mock_filepath}}
        mock_cache.return_value = mock_cache_instance

        # Override get_videos_metadata to return empty list
        async def mock_get_videos_metadata_empty(
            stop: int = 25,
        ) -> list[dict[str, Any]]:
            return []

        self.mock_blink.get_videos_metadata = mock_get_videos_metadata_empty
        self.mock_blink.videos = {"all": []}

        with patch(
            "blinkapp.services.blink_service.ensure_blink_connection_initialized",
            return_value=Mock(execute=Mock(return_value=[])),
        ):
            filepath, error = _download_cloud_clip_core_sync(
                self.clip_id, self.mock_blink, self.mock_cache_dir
            )

        assert error == "Clip not found"
        assert filepath is None

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_download_cloud_clip_core_sync_clip_not_found(
        self, mock_cache: Mock
    ) -> None:
        """Test _download_cloud_clip_core_sync when clip not found in metadata."""
        from blinkapp.services.clip_download import _download_cloud_clip_core_sync

        mock_cache.return_value = {}

        # Override get_videos_metadata to return empty list
        async def mock_get_videos_metadata_empty(
            stop: int = 25,
        ) -> list[dict[str, Any]]:
            return []

        self.mock_blink.get_videos_metadata = mock_get_videos_metadata_empty
        self.mock_blink.videos = {"all": []}

        with patch(
            "blinkapp.services.blink_service.ensure_blink_connection_initialized",
            return_value=Mock(execute=Mock(return_value=[])),
        ):
            filepath, error = _download_cloud_clip_core_sync(
                self.clip_id, self.mock_blink, self.mock_cache_dir
            )

        assert error is not None and "not found" in error.lower()
        assert filepath is None

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    @patch("blinkapp.services.connection_service.ensure_http_session_initialized")
    def test_download_cloud_clip_core_sync_no_media_url(
        self, mock_session, mock_executor, mock_cache
    ) -> None:
        """Test _download_cloud_clip_core_sync with no media URL."""
        from blinkapp.services.clip_download import _download_cloud_clip_core_sync

        mock_cache.return_value = {}
        clip_info = {
            "id": "123456",
            "created_at": "2023-01-01T12:00:00Z",
            "device_name": "test_camera",
            "media": None,
        }

        # Override get_videos_metadata to return clip with no media URL
        async def mock_get_videos_metadata_no_media(
            stop: int = 25,
        ) -> list[dict[str, Any]]:
            return [clip_info]

        self.mock_blink.get_videos_metadata = mock_get_videos_metadata_no_media
        self.mock_blink.videos = {"all": [clip_info]}

        with patch("pathlib.Path.exists", return_value=False):
            with patch(
                "blinkapp.services.blink_service.ensure_blink_connection_initialized",
                return_value=Mock(execute=Mock(return_value=[clip_info])),
            ):
                filepath, error = _download_cloud_clip_core_sync(
                    self.clip_id, self.mock_blink, self.mock_cache_dir
                )

        # Check for the actual error message from Config.ErrorMessages.CLIP_NO_MEDIA_URL
        assert error is not None and ("is not available for download" in error.lower())
        assert filepath is None

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
            assert result == "/test/cache"  # Function returns string, not Path
