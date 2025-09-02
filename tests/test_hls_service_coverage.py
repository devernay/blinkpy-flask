"""Comprehensive tests for HLS service to improve coverage.

Tests focus on the HLSStream class and FFmpeg process management
which are the main uncovered areas in hls_service.py.
"""

import subprocess
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from blinkapp.services.hls_service import (
    HLSStream,
    HLSStreamConfig,
    _build_ffmpeg_command,
    _create_ffmpeg_process,
)
from tests.test_base import BaseTestCase


class TestHLSStreamConfig(BaseTestCase):
    """Test HLS stream configuration."""

    def test_hls_stream_config_defaults(self) -> None:
        """Test HLS config uses defaults from Config."""
        config = HLSStreamConfig()

        # Should use Config defaults
        self.assertIsNotNone(config.segment_time)
        self.assertIsNotNone(config.list_size)
        self.assertIsNotNone(config.timeout)
        self.assertIsNotNone(config.idle_timeout)

    def test_hls_stream_config_custom_values(self) -> None:
        """Test HLS config with custom values."""
        config = HLSStreamConfig(
            segment_time=5, list_size=10, timeout=30, idle_timeout=60
        )

        self.assertEqual(config.segment_time, 5)
        self.assertEqual(config.list_size, 10)
        self.assertEqual(config.timeout, 30)
        self.assertEqual(config.idle_timeout, 60)


class TestFFmpegHelpers(BaseTestCase):
    """Test FFmpeg helper functions."""

    def test_build_ffmpeg_command(self) -> None:
        """Test FFmpeg command building."""
        config = HLSStreamConfig(segment_time=4, list_size=5)
        output_path = Path("/tmp/test.m3u8")
        tcp_url = "tcp://127.0.0.1:8080"

        cmd = _build_ffmpeg_command(tcp_url, output_path, config)

        expected = [
            "ffmpeg",
            "-i",
            tcp_url,
            "-c",
            "copy",
            "-f",
            "hls",
            "-hls_time",
            "4",
            "-hls_list_size",
            "5",
            "-hls_flags",
            "delete_segments",
            str(output_path),
        ]

        self.assertEqual(cmd, expected)

    def test_create_ffmpeg_process_success(self) -> None:
        """Test successful FFmpeg process creation."""
        mock_process = Mock(spec=subprocess.Popen)
        mock_factory = Mock(return_value=mock_process)

        cmd = ["ffmpeg", "-version"]
        result = _create_ffmpeg_process(cmd, mock_factory)

        self.assertEqual(result, mock_process)
        mock_factory.assert_called_once_with(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
        )

    def test_create_ffmpeg_process_error(self) -> None:
        """Test FFmpeg process creation error."""
        mock_factory = Mock(side_effect=OSError("Command not found"))

        cmd = ["ffmpeg", "-version"]
        result = _create_ffmpeg_process(cmd, mock_factory)

        self.assertIsNone(result)

    def test_create_ffmpeg_process_subprocess_error(self) -> None:
        """Test FFmpeg process creation subprocess error."""
        mock_factory = Mock(side_effect=subprocess.SubprocessError("Process error"))

        cmd = ["ffmpeg", "-version"]
        result = _create_ffmpeg_process(cmd, mock_factory)

        self.assertIsNone(result)

    def test_create_ffmpeg_process_default_factory(self) -> None:
        """Test FFmpeg process creation with default factory."""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_popen.return_value = mock_process

            cmd = ["echo", "test"]
            result = _create_ffmpeg_process(cmd)

            self.assertEqual(result, mock_process)


class TestHLSStream(BaseTestCase):
    """Test HLS stream management."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()
        self.config = HLSStreamConfig(
            segment_time=2, list_size=3, timeout=10, idle_timeout=30
        )
        self.camera_id = "test_camera"
        self.tcp_url = "tcp://127.0.0.1:8080"

    def test_hls_stream_init(self) -> None:
        """Test HLS stream initialization."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)

        self.assertEqual(stream.camera_id, self.camera_id)
        self.assertEqual(stream.tcp_url, self.tcp_url)
        self.assertEqual(stream.config, self.config)
        self.assertIsNone(stream.process)
        self.assertIsNone(stream.temp_dir)
        self.assertFalse(stream._active)
        self.assertIsNotNone(stream.lock)  # Just check it exists

    @patch("blinkapp.services.hls_service._create_ffmpeg_process")
    @patch("tempfile.TemporaryDirectory")
    @patch("time.sleep")
    def test_hls_stream_start_success(
        self, mock_sleep: Mock, mock_temp_dir: Mock, mock_create_process: Mock
    ) -> None:
        """Test successful HLS stream start."""
        # Mock temporary directory
        mock_dir = Mock()
        mock_dir.name = "/tmp/hls_test_camera_123"
        mock_temp_dir.return_value = mock_dir

        # Mock FFmpeg process
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.poll.return_value = None  # Process is running
        mock_create_process.return_value = mock_process

        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        hls_url, error = stream.start()

        self.assertIsNotNone(hls_url)
        self.assertIsNone(error)
        self.assertTrue(stream._active)
        self.assertEqual(stream.process, mock_process)
        self.assertEqual(stream.temp_dir, mock_dir)
        mock_sleep.assert_called_once_with(2)

    @patch("blinkapp.services.hls_service._create_ffmpeg_process")
    def test_hls_stream_start_process_creation_failed(
        self, mock_create_process: Mock
    ) -> None:
        """Test HLS stream start when process creation fails."""
        mock_create_process.return_value = None

        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        hls_url, error = stream.start()

        self.assertIsNone(hls_url)
        self.assertEqual(error, "Failed to create FFmpeg process")
        self.assertFalse(stream._active)

    @patch("blinkapp.services.hls_service._create_ffmpeg_process")
    @patch("tempfile.TemporaryDirectory")
    @patch("time.sleep")
    def test_hls_stream_start_process_terminated(
        self, mock_sleep: Mock, mock_temp_dir: Mock, mock_create_process: Mock
    ) -> None:
        """Test HLS stream start when process terminates immediately."""
        # Mock temporary directory
        mock_dir = Mock()
        mock_dir.name = "/tmp/hls_test_camera_123"
        mock_temp_dir.return_value = mock_dir

        # Mock FFmpeg process that terminates
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.poll.return_value = 1  # Process terminated
        mock_process.communicate.return_value = (b"", b"FFmpeg error")
        mock_create_process.return_value = mock_process

        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        hls_url, error = stream.start()

        self.assertIsNone(hls_url)
        self.assertIn("Stream failed to start", error)
        self.assertIn("FFmpeg error", error)

    @patch("blinkapp.services.hls_service._create_ffmpeg_process")
    @patch("tempfile.TemporaryDirectory")
    def test_hls_stream_start_exception(
        self, mock_temp_dir: Mock, mock_create_process: Mock
    ) -> None:
        """Test HLS stream start with exception."""
        mock_temp_dir.side_effect = OSError("Permission denied")

        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        hls_url, error = stream.start()

        self.assertIsNone(hls_url)
        self.assertIn("Failed to start stream", error)
        self.assertIn("Permission denied", error)

    @patch("blinkapp.services.hls_service._create_ffmpeg_process")
    @patch("tempfile.TemporaryDirectory")
    @patch("time.sleep")
    def test_hls_stream_start_already_active(
        self, mock_sleep: Mock, mock_temp_dir: Mock, mock_create_process: Mock
    ) -> None:
        """Test HLS stream start when already active."""
        # Set up active stream
        mock_dir = Mock()
        mock_dir.name = "/tmp/hls_test_camera_123"
        mock_temp_dir.return_value = mock_dir

        mock_process = Mock(spec=subprocess.Popen)
        mock_process.poll.return_value = None
        mock_create_process.return_value = mock_process

        stream = HLSStream(self.camera_id, self.tcp_url, self.config)

        # Start first time
        hls_url1, error1 = stream.start()
        self.assertIsNotNone(hls_url1)
        self.assertIsNone(error1)

        # Start second time - should return existing URL
        hls_url2, error2 = stream.start()
        self.assertEqual(hls_url1, hls_url2)
        self.assertIsNone(error2)

        # Should only create process once
        self.assertEqual(mock_create_process.call_count, 1)

    def test_hls_stream_stop(self) -> None:
        """Test HLS stream stop."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream._active = True

        with patch.object(stream, "cleanup") as mock_cleanup:
            stream.stop()

            self.assertFalse(stream._active)
            mock_cleanup.assert_called_once()

    def test_hls_stream_cleanup_with_process(self) -> None:
        """Test HLS stream cleanup with active process."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)

        # Mock process
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.wait.return_value = None
        stream.process = mock_process

        # Mock temp directory
        mock_temp_dir = Mock()
        stream.temp_dir = mock_temp_dir

        stream.cleanup()

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_with(timeout=5)
        mock_temp_dir.cleanup.assert_called_once()
        self.assertIsNone(stream.process)
        self.assertIsNone(stream.temp_dir)

    def test_hls_stream_cleanup_process_timeout(self) -> None:
        """Test HLS stream cleanup when process doesn't terminate gracefully."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)

        # Mock process that times out on terminate
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.wait.side_effect = [subprocess.TimeoutExpired("ffmpeg", 5), None]
        stream.process = mock_process

        stream.cleanup()

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
        self.assertEqual(mock_process.wait.call_count, 2)

    def test_hls_stream_cleanup_process_kill_timeout(self) -> None:
        """Test HLS stream cleanup when process doesn't respond to kill."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)

        # Mock process that times out on both terminate and kill
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.wait.side_effect = subprocess.TimeoutExpired("ffmpeg", 5)
        stream.process = mock_process

        stream.cleanup()  # Should not raise exception

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    def test_hls_stream_cleanup_os_error(self) -> None:
        """Test HLS stream cleanup with OS errors."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)

        # Mock process that raises OSError
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.terminate.side_effect = OSError("Process error")
        stream.process = mock_process

        # Mock temp directory that raises OSError
        mock_temp_dir = Mock()
        mock_temp_dir.cleanup.side_effect = OSError("Cleanup error")
        stream.temp_dir = mock_temp_dir

        stream.cleanup()  # Should not raise exception

        self.assertIsNone(stream.process)
        self.assertIsNone(stream.temp_dir)

    def test_hls_stream_is_active_not_active(self) -> None:
        """Test is_active when stream is not active."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)

        self.assertFalse(stream.is_active())

    def test_hls_stream_is_active_no_process(self) -> None:
        """Test is_active when no process."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream._active = True

        self.assertFalse(stream.is_active())

    def test_hls_stream_is_active_process_terminated(self) -> None:
        """Test is_active when process terminated."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream._active = True

        mock_process = Mock(spec=subprocess.Popen)
        mock_process.poll.return_value = 1  # Process terminated
        stream.process = mock_process

        self.assertFalse(stream.is_active())
        self.assertFalse(stream._active)

    @patch("time.time")
    def test_hls_stream_is_active_idle_timeout(self, mock_time: Mock) -> None:
        """Test is_active with idle timeout."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream._active = True
        stream.last_access = 100

        mock_process = Mock(spec=subprocess.Popen)
        mock_process.poll.return_value = None  # Process running
        stream.process = mock_process

        # Mock current time to trigger timeout
        mock_time.return_value = 200  # 100 seconds later

        with patch.object(stream, "stop") as mock_stop:
            result = stream.is_active()

            self.assertFalse(result)
            mock_stop.assert_called_once()

    def test_hls_stream_is_active_success(self) -> None:
        """Test is_active when stream is healthy."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream._active = True
        stream.last_access = time.time()

        mock_process = Mock(spec=subprocess.Popen)
        mock_process.poll.return_value = None  # Process running
        stream.process = mock_process

        self.assertTrue(stream.is_active())

    def test_hls_stream_get_hls_url_no_temp_dir(self) -> None:
        """Test get_hls_url when no temp directory."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)

        self.assertIsNone(stream.get_hls_url())

    def test_hls_stream_get_hls_url_success(self) -> None:
        """Test get_hls_url with temp directory."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream.temp_dir = Mock()
        stream.temp_dir.name = "/tmp/test"

        url = stream.get_hls_url()
        expected = f"/api/cameras/{self.camera_id}/hls/stream.m3u8"

        self.assertEqual(url, expected)

    def test_hls_stream_get_file_not_active(self) -> None:
        """Test get_file when stream not active."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)

        content, content_type = stream.get_file("test.m3u8")

        self.assertIsNone(content)
        self.assertIsNone(content_type)

    def test_hls_stream_get_file_no_temp_dir(self) -> None:
        """Test get_file when no temp directory."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream._active = True

        content, content_type = stream.get_file("test.m3u8")

        self.assertIsNone(content)
        self.assertIsNone(content_type)

    @patch("builtins.open")
    @patch("pathlib.Path.exists")
    def test_hls_stream_get_file_success_m3u8(
        self, mock_exists: Mock, mock_open: Mock
    ) -> None:
        """Test get_file success with m3u8 file."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream._active = True

        mock_temp_dir = Mock()
        mock_temp_dir.name = "/tmp/test"
        stream.temp_dir = mock_temp_dir

        mock_exists.return_value = True
        mock_file = Mock()
        mock_file.read.return_value = b"playlist content"
        mock_open.return_value.__enter__.return_value = mock_file

        content, content_type = stream.get_file("playlist.m3u8")

        self.assertEqual(content, b"playlist content")
        self.assertEqual(content_type, "application/vnd.apple.mpegurl")

    @patch("builtins.open")
    @patch("pathlib.Path.exists")
    def test_hls_stream_get_file_success_ts(
        self, mock_exists: Mock, mock_open: Mock
    ) -> None:
        """Test get_file success with ts file."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream._active = True

        mock_temp_dir = Mock()
        mock_temp_dir.name = "/tmp/test"
        stream.temp_dir = mock_temp_dir

        mock_exists.return_value = True
        mock_file = Mock()
        mock_file.read.return_value = b"segment content"
        mock_open.return_value.__enter__.return_value = mock_file

        content, content_type = stream.get_file("segment.ts")

        self.assertEqual(content, b"segment content")
        self.assertEqual(content_type, "video/mp2t")

    @patch("builtins.open")
    @patch("pathlib.Path.exists")
    def test_hls_stream_get_file_success_other(
        self, mock_exists: Mock, mock_open: Mock
    ) -> None:
        """Test get_file success with other file type."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream._active = True

        mock_temp_dir = Mock()
        mock_temp_dir.name = "/tmp/test"
        stream.temp_dir = mock_temp_dir

        mock_exists.return_value = True
        mock_file = Mock()
        mock_file.read.return_value = b"other content"
        mock_open.return_value.__enter__.return_value = mock_file

        content, content_type = stream.get_file("other.txt")

        self.assertEqual(content, b"other content")
        self.assertEqual(content_type, "application/octet-stream")

    @patch("pathlib.Path.exists")
    def test_hls_stream_get_file_not_exists(self, mock_exists: Mock) -> None:
        """Test get_file when file doesn't exist."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream._active = True

        mock_temp_dir = Mock()
        mock_temp_dir.name = "/tmp/test"
        stream.temp_dir = mock_temp_dir

        mock_exists.return_value = False

        content, content_type = stream.get_file("missing.m3u8")

        self.assertIsNone(content)
        self.assertIsNone(content_type)

    @patch("builtins.open")
    @patch("pathlib.Path.exists")
    def test_hls_stream_get_file_os_error(
        self, mock_exists: Mock, mock_open: Mock
    ) -> None:
        """Test get_file with OS error."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream._active = True

        mock_temp_dir = Mock()
        mock_temp_dir.name = "/tmp/test"
        stream.temp_dir = mock_temp_dir

        mock_exists.return_value = True
        mock_open.side_effect = OSError("Permission denied")

        content, content_type = stream.get_file("test.m3u8")

        self.assertIsNone(content)
        self.assertIsNone(content_type)

    @patch("time.time")
    @patch("builtins.open")
    @patch("pathlib.Path.exists")
    def test_hls_stream_get_file_updates_last_access(
        self, mock_exists: Mock, mock_open: Mock, mock_time: Mock
    ) -> None:
        """Test get_file updates last access time."""
        stream = HLSStream(self.camera_id, self.tcp_url, self.config)
        stream._active = True
        stream.last_access = 100

        mock_temp_dir = Mock()
        mock_temp_dir.name = "/tmp/test"
        stream.temp_dir = mock_temp_dir

        mock_exists.return_value = True
        mock_file = Mock()
        mock_file.read.return_value = b"content"
        mock_open.return_value.__enter__.return_value = mock_file
        mock_time.return_value = 200

        stream.get_file("test.m3u8")

        self.assertEqual(stream.last_access, 200)


if __name__ == "__main__":
    unittest.main()
