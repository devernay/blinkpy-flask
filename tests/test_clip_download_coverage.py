"""Comprehensive tests for clip_download.py to achieve near 100% coverage."""

from pathlib import Path
from unittest.mock import patch

from blinkapp.models.ids import ClipId
from blinkapp.services import clip_download

from .test_base import create_mock_blink_instance


class TestDownloadClipCommon:
    """Test download_clip_common function."""

    @patch("pathlib.Path.exists")
    def test_download_clip_common_file_not_found(self, mock_exists):
        """Test when clip file doesn't exist."""
        mock_exists.return_value = False

        result = clip_download.download_clip_common(
            Path("/nonexistent/clip.mp4"), ClipId("test_clip")
        )

        assert isinstance(result, tuple)
        response_dict, status_code = result
        assert response_dict["success"] is False
        assert status_code == 404

    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.clip_download.send_file")
    def test_download_clip_common_success(self, mock_send_file, mock_exists):
        """Test successful file download."""
        mock_exists.return_value = True
        mock_send_file.return_value = "file_response"

        result = clip_download.download_clip_common(
            Path("/test/clip.mp4"), ClipId("test_clip")
        )

        assert result == "file_response"
        mock_send_file.assert_called_once_with(
            Path("/test/clip.mp4"),
            as_attachment=True,
            download_name="clip_test_clip.mp4",
            mimetype="video/mp4",
        )

    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.clip_download.send_file")
    def test_download_clip_common_exception(self, mock_send_file, mock_exists):
        """Test exception handling."""
        mock_exists.return_value = True
        mock_send_file.side_effect = Exception("File error")

        result = clip_download.download_clip_common(
            Path("/test/clip.mp4"), ClipId("test_clip")
        )

        assert isinstance(result, tuple)
        response_dict, status_code = result
        assert response_dict["success"] is False
        assert status_code == 500


class TestDownloadCloudClip:
    """Test download_cloud_clip function."""

    @patch("blinkapp.services.blink_service.get_blink_instance")
    def test_download_cloud_clip_no_blink(self, mock_get_blink):
        """Test when blink instance not available."""
        mock_get_blink.return_value = None

        result = clip_download.download_cloud_clip(ClipId("test_clip"))

        assert isinstance(result, tuple)
        response_dict, status_code = result
        assert response_dict["success"] is False
        assert status_code == 503

    @patch("blinkapp.services.blink_service.get_blink_instance")
    def test_download_cloud_clip_blink_unavailable(self, mock_get_blink):
        """Test when blink instance exists but not available."""
        mock_blink = create_mock_blink_instance(available=False)
        mock_get_blink.return_value = mock_blink

        result = clip_download.download_cloud_clip(ClipId("test_clip"))

        assert isinstance(result, tuple)
        response_dict, status_code = result
        assert response_dict["success"] is False
        assert status_code == 503

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("blinkapp.services.blink_service.get_blink_instance")
    @patch("pathlib.Path.exists")
    @patch("blinkapp.services.clip_download.download_clip_common")
    def test_download_cloud_clip_cached(self, mock_common, mock_exists, mock_get_blink):
        """Test when clip is already cached."""
        mock_blink = create_mock_blink_instance(available=True)
        mock_get_blink.return_value = mock_blink
        mock_exists.return_value = True
        mock_common.return_value = "file_response"

        result = clip_download.download_cloud_clip(ClipId("test_clip"))

        assert result == "file_response"
        mock_common.assert_called_once()

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("blinkapp.services.blink_service.get_blink_instance")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("blinkapp.services.clip_download._download_cloud_clip_core_sync")
    def test_download_cloud_clip_download_error(
        self, mock_sync, mock_mkdir, mock_exists, mock_get_blink
    ):
        """Test when download fails."""
        mock_blink = create_mock_blink_instance(available=True)
        mock_get_blink.return_value = mock_blink
        mock_exists.return_value = False
        mock_sync.return_value = (None, "Download error")

        result = clip_download.download_cloud_clip(ClipId("test_clip"))

        assert isinstance(result, tuple)
        response_dict, status_code = result
        assert response_dict["success"] is False
        assert status_code == 500

    @patch("blinkapp.CLIPS_CACHE_DIR", "/tmp/test_clips")
    @patch("blinkapp.services.blink_service.get_blink_instance")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("blinkapp.services.clip_download._download_cloud_clip_core_sync")
    def test_download_cloud_clip_not_found_error(
        self, mock_sync, mock_mkdir, mock_exists, mock_get_blink
    ):
        """Test when clip not found."""
        mock_blink = create_mock_blink_instance(available=True)
        mock_get_blink.return_value = mock_blink
        mock_exists.return_value = False
        mock_sync.return_value = (None, "Clip not found")

        result = clip_download.download_cloud_clip(ClipId("test_clip"))

        assert isinstance(result, tuple)
        response_dict, status_code = result
        assert response_dict["success"] is False
        assert status_code == 404

    @patch("blinkapp.services.blink_service.get_blink_instance")
    def test_download_cloud_clip_exception(self, mock_get_blink):
        """Test exception handling."""
        mock_get_blink.side_effect = Exception("Unexpected error")

        result = clip_download.download_cloud_clip(ClipId("test_clip"))

        assert isinstance(result, tuple)
        response_dict, status_code = result
        assert response_dict["success"] is False
        assert status_code == 500


class TestClipDownloadCore:
    """Test core download functions."""

    def test_download_cloud_clip_core_sync_no_blink(self):
        """Test sync wrapper when blink instance is None."""
        result = clip_download._download_cloud_clip_core_sync(
            ClipId("test_clip"), None, Path("/tmp")
        )

        assert result[0] is None
        assert result[1] is not None and "Blink instance not available" in result[1]
