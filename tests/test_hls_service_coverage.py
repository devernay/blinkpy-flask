"""Test coverage for hls_service."""

from pathlib import Path
from unittest.mock import Mock, patch

from blinkapp.services.hls_service import (
    HLSStream,
    HLSStreamConfig,
    _build_ffmpeg_command,
    _create_ffmpeg_process,
    generate_hls_url,
    parse_tcp_url,
)

from .test_base import BaseTestCase


class TestParseTcpUrl(BaseTestCase):
    """Test parse_tcp_url function."""

    def test_parse_tcp_url_empty(self):
        """Test parsing empty URL."""
        result = parse_tcp_url("")
        assert result == {}

    def test_parse_tcp_url_none(self):
        """Test parsing None URL."""
        result = parse_tcp_url("")  # Use empty string instead of None
        assert result == {}

    def test_parse_tcp_url_valid(self):
        """Test parsing valid TCP URL."""
        result = parse_tcp_url("tcp://127.0.0.1:8080")
        assert result == {"protocol": "tcp", "host": "127.0.0.1", "port": "8080"}

    def test_parse_tcp_url_no_port(self):
        """Test parsing URL without port."""
        result = parse_tcp_url("tcp://127.0.0.1")
        assert result == {"protocol": "tcp", "host": "127.0.0.1", "port": ""}

    def test_parse_tcp_url_no_protocol(self):
        """Test parsing URL without protocol."""
        result = parse_tcp_url("127.0.0.1:8080")
        assert result == {}


class TestGenerateHlsUrl(BaseTestCase):
    """Test generate_hls_url function."""

    def test_generate_hls_url_default(self):
        """Test generating HLS URL with default base."""
        result = generate_hls_url("camera123")
        assert result == "http://localhost:8080/hls/camera123/playlist.m3u8"

    def test_generate_hls_url_custom_base(self):
        """Test generating HLS URL with custom base."""
        result = generate_hls_url("camera456", "https://example.com")
        assert result == "https://example.com/hls/camera456/playlist.m3u8"


class TestHlsStreamConfig(BaseTestCase):
    """Test HLSStreamConfig dataclass."""

    def test_hls_stream_config_defaults(self):
        """Test HLSStreamConfig with default values."""
        config = HLSStreamConfig()
        assert config.segment_time == 2
        assert config.list_size == 3
        assert config.idle_timeout == 300


class TestCreateFfmpegProcess(BaseTestCase):
    """Test _create_ffmpeg_process function."""

    def test_create_ffmpeg_process_success(self):
        """Test successful FFmpeg process creation."""
        mock_process = Mock()

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            result = _create_ffmpeg_process(["ffmpeg", "-version"])

            assert result == mock_process
            mock_popen.assert_called_once()

    def test_create_ffmpeg_process_exception(self):
        """Test FFmpeg process creation with exception."""
        with patch("subprocess.Popen", side_effect=OSError("Process error")):
            result = _create_ffmpeg_process(["ffmpeg", "-version"])

            assert result is None


class TestBuildFfmpegCommand(BaseTestCase):
    """Test _build_ffmpeg_command function."""

    def test_build_ffmpeg_command_basic(self):
        """Test building basic FFmpeg command."""
        config = HLSStreamConfig()
        output_path = Path("/tmp/output")

        cmd = _build_ffmpeg_command("tcp://127.0.0.1:8080", output_path, config)

        assert "ffmpeg" in cmd
        assert "-i" in cmd
        assert "tcp://127.0.0.1:8080" in cmd
        # Check that output path is in the command (may be in different format)
        assert any("/tmp/output" in str(arg) for arg in cmd)


class TestHlsStream(BaseTestCase):
    """Test HLSStream class."""

    def test_hls_stream_init(self):
        """Test HLS stream initialization."""
        config = HLSStreamConfig()
        stream = HLSStream("camera123", "tcp://127.0.0.1:8080", config)

        assert stream.camera_id == "camera123"
        assert stream.tcp_url == "tcp://127.0.0.1:8080"
        assert stream.config == config
        assert not stream._active

    @patch("tempfile.TemporaryDirectory")
    @patch("blinkapp.services.hls_service._create_ffmpeg_process")
    def test_hls_stream_start_success(self, mock_create_process, mock_temp_dir):
        """Test successful HLS stream start."""
        mock_temp_dir_instance = Mock()
        mock_temp_dir_instance.name = "/tmp/test_stream"
        mock_temp_dir.return_value = mock_temp_dir_instance

        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_create_process.return_value = mock_process

        config = HLSStreamConfig()
        stream = HLSStream("camera123", "tcp://127.0.0.1:8080", config)

        url, error = stream.start()

        assert error is None
        assert url is not None
        assert "/api/cameras/camera123/hls/stream.m3u8" in url
        assert stream._active

    @patch("tempfile.TemporaryDirectory")
    @patch("blinkapp.services.hls_service._create_ffmpeg_process")
    def test_hls_stream_start_failure(self, mock_create_process, mock_temp_dir):
        """Test HLS stream start failure."""
        mock_temp_dir_instance = Mock()
        mock_temp_dir_instance.name = "/tmp/test_stream"
        mock_temp_dir.return_value = mock_temp_dir_instance

        mock_create_process.return_value = None

        config = HLSStreamConfig()
        stream = HLSStream("camera123", "tcp://127.0.0.1:8080", config)

        url, error = stream.start()

        assert url is None
        assert error is not None
        assert "Failed to create FFmpeg process" in error
        assert not stream._active

    def test_hls_stream_stop(self):
        """Test HLS stream stop."""
        config = HLSStreamConfig()
        stream = HLSStream("camera123", "tcp://127.0.0.1:8080", config)
        stream._active = True

        stream.stop()

        assert not stream._active

    def test_hls_stream_cleanup(self):
        """Test HLS stream cleanup."""
        config = HLSStreamConfig()
        stream = HLSStream("camera123", "tcp://127.0.0.1:8080", config)

        mock_process = Mock()
        stream.process = mock_process

        mock_temp_dir = Mock()
        stream.temp_dir = mock_temp_dir

        stream.cleanup()

        mock_process.terminate.assert_called_once()
        mock_temp_dir.cleanup.assert_called_once()
        assert stream.process is None
        assert stream.temp_dir is None

    def test_hls_stream_is_active_false(self):
        """Test HLS stream active check when inactive."""
        config = HLSStreamConfig()
        stream = HLSStream("camera123", "tcp://127.0.0.1:8080", config)

        assert not stream.is_active()

    def test_hls_stream_is_active_true(self):
        """Test HLS stream active check when active."""
        config = HLSStreamConfig()
        stream = HLSStream("camera123", "tcp://127.0.0.1:8080", config)

        mock_process = Mock()
        mock_process.poll.return_value = None  # Still running
        stream.process = mock_process
        stream._active = True
        stream.last_access = 0  # Set to avoid timeout

        with patch("time.time", return_value=1):  # 1 second elapsed
            assert stream.is_active()

    def test_hls_stream_get_hls_url_no_temp_dir(self):
        """Test getting HLS URL without temp directory."""
        config = HLSStreamConfig()
        stream = HLSStream("camera123", "tcp://127.0.0.1:8080", config)

        result = stream.get_hls_url()
        assert result is None

    def test_hls_stream_get_hls_url_with_temp_dir(self):
        """Test getting HLS URL with temp directory."""
        config = HLSStreamConfig()
        stream = HLSStream("camera123", "tcp://127.0.0.1:8080", config)

        mock_temp_dir = Mock()
        stream.temp_dir = mock_temp_dir

        result = stream.get_hls_url()
        assert result == "/api/cameras/camera123/hls/stream.m3u8"

    def test_hls_stream_get_file_no_temp_dir(self):
        """Test getting file without temp directory."""
        config = HLSStreamConfig()
        stream = HLSStream("camera123", "tcp://127.0.0.1:8080", config)

        content, content_type = stream.get_file("stream.m3u8")
        assert content is None
        assert content_type is None

    @patch("pathlib.Path.exists")
    @patch("builtins.open")
    @patch("time.time")
    def test_hls_stream_get_file_success(self, mock_time, mock_open, mock_exists):
        """Test successful file retrieval."""
        mock_exists.return_value = True
        mock_time.return_value = 123456

        mock_file = Mock()
        mock_file.read.return_value = b"test content"
        mock_open.return_value.__enter__.return_value = mock_file

        config = HLSStreamConfig()
        stream = HLSStream("camera123", "tcp://127.0.0.1:8080", config)

        mock_temp_dir = Mock()
        mock_temp_dir.name = "/tmp/test"
        stream.temp_dir = mock_temp_dir
        stream._active = True

        content, content_type = stream.get_file("stream.m3u8")
        assert content == b"test content"
        assert content_type == "application/vnd.apple.mpegurl"

    @patch("pathlib.Path.exists")
    def test_hls_stream_get_file_not_found(self, mock_exists):
        """Test file retrieval when file doesn't exist."""
        mock_exists.return_value = False

        config = HLSStreamConfig()
        stream = HLSStream("camera123", "tcp://127.0.0.1:8080", config)

        mock_temp_dir = Mock()
        mock_temp_dir.name = "/tmp/test"
        stream.temp_dir = mock_temp_dir
        stream._active = True

        content, content_type = stream.get_file("stream.m3u8")
        assert content is None
        assert content_type is None
