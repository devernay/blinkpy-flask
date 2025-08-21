"""Test coverage boost for stream_service.py missed lines."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from blinkapp.services.stream_service import (
    HLSStream,
    StreamConfig,
    StreamManager,
    ensure_stream_manager_initialized,
    initialize_stream_manager,
)


class TestStreamServiceBoost(unittest.TestCase):
    """Test stream service coverage boost."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_stream_config_creation(self):
        """Test StreamConfig dataclass creation."""
        config = StreamConfig(segment_time=4, list_size=5, timeout=30, idle_timeout=60)

        self.assertEqual(config.segment_time, 4)
        self.assertEqual(config.list_size, 5)
        self.assertEqual(config.timeout, 30)
        self.assertEqual(config.idle_timeout, 60)

    def test_stream_config_defaults(self):
        """Test StreamConfig with default values."""
        with patch("blinkapp.services.stream_service.Config") as mock_config:
            mock_config.HLS_SEGMENT_TIME = 4
            mock_config.HLS_LIST_SIZE = 5
            mock_config.FFMPEG_TIMEOUT = 30
            mock_config.STREAM_IDLE_TIMEOUT = 60

            config = StreamConfig()

            self.assertEqual(config.segment_time, 4)
            self.assertEqual(config.list_size, 5)
            self.assertEqual(config.timeout, 30)
            self.assertEqual(config.idle_timeout, 60)

    def test_hls_stream_creation(self):
        """Test HLSStream creation."""
        config = StreamConfig(segment_time=4, list_size=5)

        stream = HLSStream(
            camera_id="test_camera", tcp_url="tcp://localhost:8080", config=config
        )

        self.assertEqual(stream.camera_id, "test_camera")
        self.assertEqual(stream.tcp_url, "tcp://localhost:8080")
        self.assertEqual(stream.config, config)
        self.assertIsNone(stream.process)
        self.assertIsNone(stream.temp_dir)
        self.assertIsNotNone(stream.lock)
        self.assertFalse(stream._active)

    def test_initialize_stream_manager(self):
        """Test initialize_stream_manager function."""
        with patch("blinkapp.services.stream_service.Config") as mock_config:
            mock_config.HLS_SEGMENT_TIME = 4
            mock_config.HLS_LIST_SIZE = 5
            mock_config.HLS_OUTPUT_DIR = Path(self.temp_dir)

            initialize_stream_manager()

            # Check that global stream_manager is set
            from blinkapp.services.stream_service import stream_manager

            self.assertIsNotNone(stream_manager)

    def test_ensure_stream_manager_initialized_with_existing(self):
        """Test ensure_stream_manager_initialized with existing manager."""
        # Set up existing manager
        import blinkapp.services.stream_service

        mock_manager = Mock()
        blinkapp.services.stream_service.stream_manager = mock_manager

        result = ensure_stream_manager_initialized()

        self.assertEqual(result, mock_manager)

    def test_stream_manager_creation(self):
        """Test StreamManager creation."""
        config = StreamConfig(segment_time=4, list_size=5)

        manager = StreamManager(config)

        self.assertEqual(manager.config, config)
        self.assertEqual(manager.streams, {})

    def test_hls_stream_is_active_false(self):
        """Test HLSStream.is_active returns False."""
        config = StreamConfig(segment_time=4, list_size=5)
        stream = HLSStream("test_camera", "tcp://localhost:8080", config)

        result = stream.is_active()

        self.assertFalse(result)

    def test_hls_stream_is_active_true(self):
        """Test HLSStream.is_active returns True."""
        config = StreamConfig(segment_time=4, list_size=5)
        stream = HLSStream("test_camera", "tcp://localhost:8080", config)

        mock_process = Mock()
        mock_process.poll.return_value = None  # Process running
        stream.process = mock_process
        stream._active = True

        result = stream.is_active()

        self.assertTrue(result)

    def test_hls_stream_is_active_process_dead(self):
        """Test HLSStream.is_active with dead process."""
        config = StreamConfig(segment_time=4, list_size=5)
        stream = HLSStream("test_camera", "tcp://localhost:8080", config)

        mock_process = Mock()
        mock_process.poll.return_value = 1  # Process exited
        stream.process = mock_process
        stream._active = True

        result = stream.is_active()

        self.assertFalse(result)
        self.assertFalse(stream._active)

    def test_stream_manager_is_stream_active_false(self):
        """Test StreamManager.is_stream_active returns False."""
        config = StreamConfig(segment_time=4, list_size=5)
        manager = StreamManager(config)

        result = manager.is_stream_active("nonexistent_camera")

        self.assertFalse(result)

    def test_stream_manager_stop_stream_nonexistent(self):
        """Test StreamManager.stop_stream with nonexistent stream."""
        config = StreamConfig(segment_time=4, list_size=5)
        manager = StreamManager(config)

        result = manager.stop_stream("nonexistent_camera")

        self.assertFalse(result)

    def test_stream_manager_cleanup_inactive_streams(self):
        """Test StreamManager.cleanup_inactive_streams."""
        config = StreamConfig(segment_time=4, list_size=5)
        manager = StreamManager(config)

        # Add inactive stream
        stream = HLSStream("test_camera", "tcp://localhost:8080", config)
        stream._active = False
        manager.streams["test_camera"] = stream

        manager.cleanup_inactive_streams()

        # Stream should be removed
        self.assertNotIn("test_camera", manager.streams)


if __name__ == "__main__":
    unittest.main()
