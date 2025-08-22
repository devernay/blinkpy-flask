"""Core logic tests for clip_service.py - targeting maximum coverage without Flask context issues."""

from pathlib import Path
from unittest.mock import Mock, patch

from blinkapp.models.ids import ClipId


class TestClipServiceCoreLogic:
    """Tests focusing on core business logic without Flask dependencies."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.clip_id = ClipId("123456")
        self.mock_blink = Mock()
        self.mock_cache_dir = Path("/tmp/test_cache")

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_download_cloud_clip_core_no_blink_instance(self, mock_cache: Mock) -> None:
        """Test _download_cloud_clip_core with no blink instance."""
        from blinkapp.services.clip_service import _download_cloud_clip_core

        success, error, filepath = _download_cloud_clip_core(
            self.clip_id, None, self.mock_cache_dir
        )

        assert not success
        assert error == "No blink instance"
        assert filepath is None

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_download_cloud_clip_core_cached_file_exists(
        self, mock_cache: Mock
    ) -> None:
        """Test _download_cloud_clip_core with existing cached file."""
        from blinkapp.services.clip_service import _download_cloud_clip_core

        mock_filepath = Mock()
        mock_filepath.exists.return_value = True
        mock_cache_instance = {self.clip_id: {"filepath": mock_filepath}}
        mock_cache.return_value = mock_cache_instance

        success, error, filepath = _download_cloud_clip_core(
            self.clip_id, self.mock_blink, self.mock_cache_dir
        )

        assert success
        assert error == ""
        assert filepath == mock_filepath

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_download_cloud_clip_core_cached_file_os_error(
        self, mock_cache: Mock
    ) -> None:
        """Test _download_cloud_clip_core with OSError on cached file check."""
        from blinkapp.services.clip_service import _download_cloud_clip_core

        mock_filepath = Mock()
        mock_filepath.exists.side_effect = OSError("File access error")
        mock_cache_instance = {self.clip_id: {"filepath": mock_filepath}}
        mock_cache.return_value = mock_cache_instance

        self.mock_blink.videos = {"all": []}

        success, error, filepath = _download_cloud_clip_core(
            self.clip_id, self.mock_blink, self.mock_cache_dir
        )

        assert not success
        assert error == "Clip not found"
        assert filepath is None

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    def test_download_cloud_clip_core_clip_not_found(self, mock_cache: Mock) -> None:
        """Test _download_cloud_clip_core when clip not found in metadata."""
        from blinkapp.services.clip_service import _download_cloud_clip_core

        mock_cache.return_value = {}
        self.mock_blink.videos = {"all": []}

        success, error, filepath = _download_cloud_clip_core(
            self.clip_id, self.mock_blink, self.mock_cache_dir
        )

        assert not success
        assert error == "Clip not found"
        assert filepath is None

    @patch("blinkapp.services.clip_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    @patch("blinkapp.services.connection_service.ensure_http_session_initialized")
    def test_download_cloud_clip_core_no_media_url(
        self, mock_session, mock_executor, mock_cache
    ):
        """Test _download_cloud_clip_core with no media URL."""
        from blinkapp.services.clip_service import _download_cloud_clip_core

        mock_cache.return_value = {}
        clip_info = {
            "id": "123456",
            "created_at": "2023-01-01T12:00:00Z",
            "device_name": "test_camera",
            "media": None,
        }
        self.mock_blink.videos = {"all": [clip_info]}

        with patch("pathlib.Path.exists", return_value=False):
            success, error, filepath = _download_cloud_clip_core(
                self.clip_id, self.mock_blink, self.mock_cache_dir
            )

        assert not success
        # Check for the actual error message from Config.ErrorMessages.CLIP_NO_MEDIA_URL
        assert (
            "video clip is not available" in error.lower()
            or "no media url" in error.lower()
        )
        assert filepath is None

    def test_get_blink_instance(self) -> None:
        """Test _get_blink_instance function."""
        from blinkapp.services.clip_service import _get_blink_instance

        with patch("blinkapp.services.blink_service.blink", "mock_blink"):
            result = _get_blink_instance()
            assert result == "mock_blink"

    def test_get_clips_cache_dir(self) -> None:
        """Test _get_clips_cache_dir function."""
        from blinkapp.services.clip_service import _get_clips_cache_dir

        with patch("blinkapp.CLIPS_CACHE_DIR", "/test/cache"):
            result = _get_clips_cache_dir()
            assert result == Path("/test/cache")
