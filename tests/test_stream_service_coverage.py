"""Test coverage for stream_service."""

from unittest.mock import Mock, patch

from blinkapp.models.ids import CameraId
from blinkapp.services import stream_service

from .test_base import BaseTestCase


class TestStreamOperations(BaseTestCase):
    """Test stream operation functions."""

    @patch("blinkapp.services.stream_service.ensure_stream_manager_initialized")
    def test_stop_camera_stream_success(self, mock_ensure):
        """Test successful camera stream stop."""
        mock_manager = Mock()
        mock_ensure.return_value = mock_manager

        camera_id = CameraId("test_camera")

        result = stream_service.stop_camera_stream(camera_id)

        assert result is True
        mock_manager.stop_stream.assert_called_once_with(str(camera_id))

    @patch("blinkapp.services.stream_service.ensure_stream_manager_initialized")
    def test_stop_camera_stream_failure(self, mock_ensure):
        """Test camera stream stop failure."""
        mock_manager = Mock()
        mock_manager.stop_stream.side_effect = Exception("Stop error")
        mock_ensure.return_value = mock_manager

        camera_id = CameraId("test_camera")

        result = stream_service.stop_camera_stream(camera_id)

        assert result is False

    @patch("blinkapp.services.stream_service.ensure_stream_manager_initialized")
    def test_is_stream_active_true(self, mock_ensure):
        """Test stream active check returns true."""
        mock_manager = Mock()
        mock_manager.is_stream_active.return_value = True
        mock_ensure.return_value = mock_manager

        camera_id = CameraId("test_camera")

        result = stream_service.is_stream_active(camera_id)

        assert result is True

    @patch("blinkapp.services.stream_service.ensure_stream_manager_initialized")
    def test_is_stream_active_false(self, mock_ensure):
        """Test stream active check returns false."""
        mock_manager = Mock()
        mock_manager.is_stream_active.return_value = False
        mock_ensure.return_value = mock_manager

        camera_id = CameraId("test_camera")

        result = stream_service.is_stream_active(camera_id)

        assert result is False

    @patch("blinkapp.services.stream_service.ensure_stream_manager_initialized")
    def test_get_hls_file_success(self, mock_ensure):
        """Test successful HLS file retrieval."""
        mock_manager = Mock()
        mock_manager.get_hls_file.return_value = (b"file_content", "video/mp4")
        mock_ensure.return_value = mock_manager

        camera_id = CameraId("test_camera")
        filename = "segment.ts"

        content, mimetype = stream_service.get_hls_file(camera_id, filename)

        assert content == b"file_content"
        assert mimetype == "video/mp4"

    @patch("blinkapp.services.stream_service.ensure_stream_manager_initialized")
    def test_get_hls_file_not_found(self, mock_ensure):
        """Test HLS file not found."""
        mock_manager = Mock()
        mock_manager.get_hls_file.return_value = (None, None)
        mock_ensure.return_value = mock_manager

        camera_id = CameraId("test_camera")
        filename = "nonexistent.ts"

        content, mimetype = stream_service.get_hls_file(camera_id, filename)

        assert content is None
        assert mimetype is None


class TestUtilityFunctions(BaseTestCase):
    """Test utility functions."""

    def test_generate_hls_url(self):
        """Test HLS URL generation."""
        camera_id = "test_camera"
        filename = "segment.ts"

        result = stream_service.generate_hls_url(camera_id, filename)

        expected = f"/api/cameras/{camera_id}/streams/{filename}"
        assert result == expected

    def test_parse_tcp_url_valid(self):
        """Test parsing valid TCP URL."""
        tcp_url = "tcp://192.168.1.100:8080"

        host, port = stream_service.parse_tcp_url(tcp_url)

        assert host == "192.168.1.100"
        assert port == 8080

    def test_parse_tcp_url_invalid(self):
        """Test parsing invalid TCP URL."""
        tcp_url = "invalid_url"

        try:
            stream_service.parse_tcp_url(tcp_url)
            raise AssertionError("Should have raised ValueError")
        except ValueError:
            assert True

    def test_validate_camera_id_valid(self):
        """Test valid camera ID validation."""
        camera_id = "camera_123"

        result = stream_service.validate_camera_id(camera_id)

        assert result is True

    def test_validate_camera_id_invalid(self):
        """Test invalid camera ID validation."""
        camera_id = ""

        result = stream_service.validate_camera_id(camera_id)

        assert result is False

    def test_validate_tcp_url_valid(self):
        """Test valid TCP URL validation."""
        tcp_url = "tcp://192.168.1.100:8080"

        result = stream_service.validate_tcp_url(tcp_url)

        assert result is True

    def test_validate_tcp_url_invalid(self):
        """Test invalid TCP URL validation."""
        tcp_url = "invalid_url"

        result = stream_service.validate_tcp_url(tcp_url)

        assert result is False
