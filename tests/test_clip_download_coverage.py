"""Test coverage for clip_download service."""

from pathlib import Path
from unittest.mock import Mock, patch

from blinkapp.models.ids import ClipId
from blinkapp.services import clip_download

from .test_base import BaseTestCase


class TestDownloadCloudClipCoreSync(BaseTestCase):
    """Test _download_cloud_clip_core_sync function."""

    def test_download_cloud_clip_core_sync_no_blink(self):
        """Test sync download with no blink instance."""
        clip_id = ClipId("test_clip")
        clips_cache_dir = Path("/test/cache")

        result_path, error = clip_download._download_cloud_clip_core_sync(
            clip_id, None, clips_cache_dir
        )

        assert result_path is None
        assert error is not None and "Blink instance not available" in error


class TestDownloadCloudClip(BaseTestCase):
    """Test download_cloud_clip function."""

    @patch("blinkapp.services.blink_service.get_blink_instance")
    def test_download_cloud_clip_no_blink_instance(self, mock_get_blink):
        """Test download with no blink instance."""
        mock_get_blink.return_value = None
        clip_id = ClipId("test_clip")

        result = clip_download.download_cloud_clip(clip_id)

        assert isinstance(result, tuple)
        response_data, status_code = result
        assert status_code == 503
        assert not response_data["success"]

    @patch("blinkapp.services.blink_service.get_blink_instance")
    @patch("blinkapp.services.clip_download._download_cloud_clip_core_sync")
    @patch("blinkapp.services.clip_download.download_clip_common")
    def test_download_cloud_clip_success(self, mock_common, mock_sync, mock_get_blink):
        """Test successful cloud clip download."""
        clip_id = ClipId("test_clip")
        mock_get_blink.return_value = Mock()
        mock_sync.return_value = (Path("/test/file.mp4"), None)
        mock_common.return_value = Mock()

        with patch("blinkapp.CLIPS_CACHE_DIR", Path("/tmp")):
            result = clip_download.download_cloud_clip(clip_id)

        mock_common.assert_called_once()
        assert result is not None

    @patch("blinkapp.services.blink_service.get_blink_instance")
    @patch("blinkapp.services.clip_download._download_cloud_clip_core_sync")
    def test_download_cloud_clip_download_error(self, mock_sync, mock_get_blink):
        """Test cloud clip download with error."""
        clip_id = ClipId("test_clip")
        mock_get_blink.return_value = Mock()
        mock_sync.return_value = (None, "Download failed")

        with patch("blinkapp.CLIPS_CACHE_DIR", Path("/tmp")):
            result = clip_download.download_cloud_clip(clip_id)

        assert isinstance(result, tuple)
        response_data, status_code = result
        assert status_code == 500
        assert not response_data["success"]


class TestDownloadLocalClip(BaseTestCase):
    """Test download_local_clip function."""

    @patch("blinkapp.services.blink_service.get_blink_instance")
    def test_download_local_clip_no_blink_instance(self, mock_get_blink):
        """Test local download with no blink instance."""
        mock_get_blink.return_value = None
        clip_id = ClipId("test_clip")

        result = clip_download.download_local_clip(clip_id)

        assert isinstance(result, tuple)
        response_data, status_code = result
        assert status_code == 503
        assert not response_data["success"]


class TestDownloadClipCommon(BaseTestCase):
    """Test download_clip_common function."""

    @patch("blinkapp.services.clip_download.Path.exists")
    def test_download_clip_common_file_not_found(self, mock_exists):
        """Test common download when file doesn't exist."""
        mock_exists.return_value = False
        clip_path = Path("/test/nonexistent.mp4")
        clip_id = ClipId("test_clip")

        result = clip_download.download_clip_common(clip_path, clip_id)

        assert isinstance(result, tuple)
        response_data, status_code = result
        assert status_code == 404
        assert not response_data["success"]

    @patch("blinkapp.services.clip_download.Path.exists")
    @patch("blinkapp.services.clip_download.send_file")
    def test_download_clip_common_success(self, mock_send_file, mock_exists):
        """Test successful common download."""
        mock_exists.return_value = True
        mock_send_file.return_value = Mock()
        clip_path = Path("/test/file.mp4")
        clip_id = ClipId("test_clip")

        result = clip_download.download_clip_common(clip_path, clip_id)

        mock_send_file.assert_called_once_with(
            clip_path,
            as_attachment=True,
            download_name=f"clip_{clip_id}.mp4",
            mimetype="video/mp4",
        )
        assert result is not None

    @patch("blinkapp.services.clip_download.Path.exists")
    @patch("blinkapp.services.clip_download.send_file")
    def test_download_clip_common_send_file_error(self, mock_send_file, mock_exists):
        """Test common download with send_file error."""
        mock_exists.return_value = True
        mock_send_file.side_effect = Exception("Send file error")
        clip_path = Path("/test/file.mp4")
        clip_id = ClipId("test_clip")

        result = clip_download.download_clip_common(clip_path, clip_id)

        assert isinstance(result, tuple)
        response_data, status_code = result
        assert status_code == 500
        assert not response_data["success"]
