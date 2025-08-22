"""Stream service for Blink Camera Flask application.

This module handles all streaming-related business logic including
live stream management, HLS transcoding, and stream cleanup.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from blinkapp.config import Config

__all__ = [
    "initialize_stream_manager",
    "ensure_stream_manager_initialized",
    "start_camera_stream",
    "stop_camera_stream",
    "is_stream_active",
    "get_hls_file",
    "StreamConfig",
    "HLSStream",
    "StreamManager",
]

if TYPE_CHECKING:
    from blinkapp.models.ids import CameraId
    from blinkapp.services.stream_service import StreamManager

logger = logging.getLogger(__name__)

# Global stream manager instance
stream_manager: StreamManager | None = None


def initialize_stream_manager(manager_factory=None) -> None:
    """Initialize the global stream manager instance with injectable factory."""
    global stream_manager
    from blinkapp import Config
    from blinkapp.services.stream_service import StreamConfig, StreamManager

    if manager_factory is None:

        def default_factory(config):
            return StreamManager(config)

        manager_factory = default_factory

    stream_config = StreamConfig(
        segment_time=Config.HLS_SEGMENT_TIME,
        list_size=Config.HLS_LIST_SIZE,
        timeout=Config.FFMPEG_TIMEOUT,
        idle_timeout=Config.STREAM_IDLE_TIMEOUT,
    )
    stream_manager = manager_factory(stream_config)


def create_stream_manager(**kwargs):
    """Factory function for stream manager - easily mockable."""
    from blinkapp.services.stream_manager import StreamManager

    return StreamManager(**kwargs)


def ensure_stream_manager_initialized(manager_factory=None):
    """Ensure stream manager is initialized.

    Args:
        manager_factory: Optional factory function for testing

    Returns:
        Initialized stream manager instance

    Raises:
        RuntimeError: If stream_manager hasn't been initialized
    """
    if stream_manager is None:
        if manager_factory is None:
            manager_factory = create_stream_manager
        # Could initialize here with factory if needed
        raise RuntimeError(
            "Stream manager not initialized. Call initialize_blink() first."
        )
    return stream_manager


def parse_tcp_url(tcp_url: str) -> dict[str, str]:
    """Parse TCP URL components - pure function."""
    if not tcp_url:
        return {}

    try:
        if "://" in tcp_url:
            protocol, rest = tcp_url.split("://", 1)
            if ":" in rest:
                host, port = rest.split(":", 1)
                return {"protocol": protocol, "host": host, "port": port}
            return {"protocol": protocol, "host": rest, "port": ""}
        return {}
    except (ValueError, AttributeError):
        return {}


def generate_hls_url(camera_id: str, base_url: str = "http://localhost:8080") -> str:
    """Generate HLS URL for camera - pure function."""
    return f"{base_url}/hls/{camera_id}/playlist.m3u8"


def validate_camera_id(camera_id: str) -> bool:
    """Validate camera ID format - pure function."""
    return bool(camera_id and len(camera_id.strip()) > 0)


def validate_tcp_url(tcp_url: str) -> bool:
    """Validate TCP URL format - pure function."""
    return bool(tcp_url and tcp_url.startswith(("tcp://", "http://")))


def start_camera_stream(
    camera_id: CameraId, tcp_url: str
) -> tuple[str | None, str | None]:
    """Start HLS stream for a camera.

    Args:
        camera_id: The camera ID
        tcp_url: TCP stream URL from camera

    Returns:
        Tuple of (hls_url, error_message). If successful, hls_url is set and error_message is None.
        If failed, hls_url is None and error_message contains the error.
    """
    try:
        stream_manager = ensure_stream_manager_initialized()
        hls_url, error_msg = stream_manager.start_stream(str(camera_id), tcp_url)
        return hls_url, error_msg
    except Exception as e:
        logger.error(f"Failed to start stream for camera {camera_id}: {e}")
        return None, str(e)


def stop_camera_stream(camera_id: CameraId) -> bool:
    """Stop stream for a camera.

    Args:
        camera_id: The camera ID

    Returns:
        True if stream stopped successfully, False otherwise
    """
    try:
        stream_manager = ensure_stream_manager_initialized()
        if stream_manager.is_stream_active(str(camera_id)):
            stream_manager.stop_stream(str(camera_id))
            logger.info(f"Stream stopped for camera {camera_id}")
            return True
        return True  # Already stopped
    except Exception as e:
        logger.error(f"Failed to stop stream for camera {camera_id}: {e}")
        return False


def is_stream_active(camera_id: CameraId) -> bool:
    """Check if stream is active for a camera.

    Args:
        camera_id: The camera ID

    Returns:
        True if stream is active, False otherwise
    """
    try:
        stream_manager = ensure_stream_manager_initialized()
        return stream_manager.is_stream_active(str(camera_id))
    except Exception as e:
        logger.error(f"Failed to check stream status for camera {camera_id}: {e}")
        return False


def get_hls_file(camera_id: CameraId, filename: str) -> tuple[bytes | None, str | None]:
    """Get HLS file content for a camera stream.

    Args:
        camera_id: The camera ID
        filename: HLS filename to retrieve

    Returns:
        Tuple of (file_content, content_type). Both None if file not found or error.
    """
    try:
        stream_manager = ensure_stream_manager_initialized()
        return stream_manager.get_hls_file(str(camera_id), filename)
    except Exception as e:
        logger.error(f"Failed to get HLS file {filename} for camera {camera_id}: {e}")
        return None, None


# ============================================================================
# Stream Manager (merged from stream_manager.py)
# ============================================================================

"""TCP to HLS stream management module.

Provides object-oriented management of TCP streams from Blink cameras with FFmpeg transcoding
to HLS format. Handles multiple concurrent streams with automatic cleanup
and resource management.

This module specifically handles MPEG-TS streams from Blink's init_livestream() TCP proxy.
"""


# Add to exports
__all__.extend(
    [
        "StreamConfig",
        "HLSStream",
        "StreamManager",
    ]
)


@dataclass
class StreamConfig:
    """Configuration for HLS stream transcoding from Blink TCP streams."""

    segment_time: int | None = None  # HLS segment duration in seconds
    list_size: int | None = None  # Number of segments in playlist
    timeout: int | None = None  # Process timeout
    idle_timeout: int | None = None  # Stream idle timeout

    def __post_init__(self) -> None:
        """Set default values from Config if not provided."""
        if self.segment_time is None:
            self.segment_time = Config.HLS_SEGMENT_TIME
        if self.list_size is None:
            self.list_size = Config.HLS_LIST_SIZE
        if self.timeout is None:
            self.timeout = Config.FFMPEG_TIMEOUT
        if self.idle_timeout is None:
            self.idle_timeout = Config.STREAM_IDLE_TIMEOUT


def _create_ffmpeg_process(
    cmd: list[str], process_factory=None
) -> subprocess.Popen | None:
    """Create FFmpeg process with injectable factory."""
    if process_factory is None:
        process_factory = subprocess.Popen

    try:
        return process_factory(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _build_ffmpeg_command(tcp_url: str, output_path: Path, config) -> list[str]:
    """Build FFmpeg command for TCP to HLS transcoding."""
    return [
        "ffmpeg",
        "-i",
        tcp_url,
        "-c",
        "copy",
        "-f",
        "hls",
        "-hls_time",
        str(config.segment_time),
        "-hls_list_size",
        str(config.list_size),
        "-hls_flags",
        "delete_segments",
        str(output_path),
    ]


class HLSStream:
    """Manages a single HLS stream from TCP source."""

    def __init__(self, camera_id: str, tcp_url: str, config: StreamConfig):
        """Initialize HLS stream.

        Args:
            camera_id: Unique identifier for the camera
            tcp_url: TCP stream URL from Blink camera
            config: Stream configuration
        """
        self.camera_id = camera_id
        self.tcp_url = tcp_url
        self.config = config
        self.process: subprocess.Popen[bytes] | None = None
        self.temp_dir: tempfile.TemporaryDirectory[str] | None = None
        self.last_access = time.time()
        self.lock = threading.Lock()
        self._active = False

    def start(self) -> tuple[str | None, str | None]:
        """Start HLS stream transcoding.

        Returns:
            Tuple of (hls_url, error_message)
        """
        with self.lock:
            if self._active:
                return self.get_hls_url(), None

            try:
                # Create temporary directory for HLS files
                self.temp_dir = tempfile.TemporaryDirectory(
                    prefix=f"hls_{self.camera_id}_"
                )
                output_path = Path(self.temp_dir.name) / "stream.m3u8"

                # FFmpeg command for TCP to HLS transcoding
                cmd = _build_ffmpeg_command(self.tcp_url, output_path, self.config)

                # Start FFmpeg process
                self.process = _create_ffmpeg_process(cmd)
                if self.process is None:
                    return None, "Failed to create FFmpeg process"

                # Wait a moment for stream to start
                time.sleep(2)

                if self.process.poll() is not None:
                    # Process already terminated
                    _, stderr = self.process.communicate()
                    error_msg = (
                        stderr.decode() if stderr else "FFmpeg process terminated"
                    )
                    return None, f"Stream failed to start: {error_msg}"

                self._active = True
                self.last_access = time.time()
                return self.get_hls_url(), None

            except Exception as e:
                self.cleanup()
                return None, f"Failed to start stream: {str(e)}"

    def stop(self) -> None:
        """Stop HLS stream and cleanup resources."""
        with self.lock:
            self._active = False
            self.cleanup()

    def cleanup(self) -> None:
        """Clean up stream resources."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except (subprocess.TimeoutExpired, OSError):
                try:
                    self.process.kill()
                    self.process.wait(timeout=2)
                except (subprocess.TimeoutExpired, OSError):
                    pass
            self.process = None

        if self.temp_dir:
            try:
                self.temp_dir.cleanup()
            except OSError:
                pass
            self.temp_dir = None

    def is_active(self) -> bool:
        """Check if stream is active."""
        with self.lock:
            if not self._active or not self.process:
                return False

            # Check if process is still running
            if self.process.poll() is not None:
                self._active = False
                return False

            # Check idle timeout
            idle_timeout = self.config.idle_timeout
            if (
                idle_timeout is not None
                and time.time() - self.last_access > idle_timeout
            ):
                self.stop()
                return False

            return True

    def get_hls_url(self) -> str | None:
        """Get HLS stream URL."""
        if not self.temp_dir:
            return None
        return f"/api/cameras/{self.camera_id}/hls/stream.m3u8"

    def get_file(self, filename: str) -> tuple[bytes | None, str | None]:
        """Get HLS file content.

        Args:
            filename: HLS filename to retrieve

        Returns:
            Tuple of (file_content, content_type)
        """
        with self.lock:
            if not self.temp_dir or not self._active:
                return None, None

            try:
                file_path = Path(self.temp_dir.name) / filename
                if not file_path.exists():
                    return None, None

                self.last_access = time.time()

                with open(file_path, "rb") as f:
                    content = f.read()

                # Determine content type
                if filename.endswith(".m3u8"):
                    content_type = "application/vnd.apple.mpegurl"
                elif filename.endswith(".ts"):
                    content_type = "video/mp2t"
                else:
                    content_type = "application/octet-stream"

                return content, content_type

            except OSError:
                return None, None


class StreamManager:
    """Manages multiple HLS streams from Blink cameras."""

    def __init__(self, config: StreamConfig | None = None):
        """Initialize stream manager.

        Args:
            config: Default stream configuration
        """
        self.config = config or StreamConfig()
        self.streams: dict[str, HLSStream] = {}
        self.lock = threading.Lock()

    def start_stream(
        self, camera_id: str, tcp_url: str
    ) -> tuple[str | None, str | None]:
        """Start HLS stream for camera.

        Args:
            camera_id: Camera identifier
            tcp_url: TCP stream URL

        Returns:
            Tuple of (hls_url, error_message)
        """
        with self.lock:
            # Stop existing stream if any
            if camera_id in self.streams:
                self.streams[camera_id].stop()

            # Create new stream
            stream = HLSStream(camera_id, tcp_url, self.config)
            hls_url, error = stream.start()

            if hls_url:
                self.streams[camera_id] = stream
                return hls_url, None
            else:
                return None, error

    def stop_stream(self, camera_id: str) -> None:
        """Stop stream for camera."""
        with self.lock:
            if camera_id in self.streams:
                self.streams[camera_id].stop()
                del self.streams[camera_id]

    def is_stream_active(self, camera_id: str) -> bool:
        """Check if stream is active for camera."""
        with self.lock:
            if camera_id not in self.streams:
                return False

            stream = self.streams[camera_id]
            if not stream.is_active():
                del self.streams[camera_id]
                return False

            return True

    def get_hls_file(
        self, camera_id: str, filename: str
    ) -> tuple[bytes | None, str | None]:
        """Get HLS file for camera stream.

        Args:
            camera_id: Camera identifier
            filename: HLS filename

        Returns:
            Tuple of (file_content, content_type)
        """
        with self.lock:
            if camera_id not in self.streams:
                return None, None

            return self.streams[camera_id].get_file(filename)

    def cleanup_inactive_streams(self) -> None:
        """Clean up inactive streams."""
        with self.lock:
            inactive_cameras: list[str] = []
            for camera_id, stream in self.streams.items():
                if not stream.is_active():
                    inactive_cameras.append(camera_id)

            for camera_id in inactive_cameras:
                del self.streams[camera_id]

    def shutdown(self) -> None:
        """Shutdown all streams."""
        with self.lock:
            for stream in self.streams.values():
                stream.stop()
            self.streams.clear()


# Testability improvement functions - these provide injectable dependencies
# for better unit testing without changing existing functionality


def _create_ffmpeg_process_testable(
    cmd: list[str], process_factory=None
) -> subprocess.Popen | None:
    """Create FFmpeg process with injectable factory for testing."""
    if process_factory is None:
        process_factory = subprocess.Popen

    try:
        return process_factory(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _build_ffmpeg_command_testable(
    tcp_url: str, output_path: Path, config
) -> list[str]:
    """Build FFmpeg command for TCP to HLS transcoding - testable version."""
    return [
        "ffmpeg",
        "-i",
        tcp_url,
        "-c",
        "copy",
        "-f",
        "hls",
        "-hls_time",
        str(config.segment_time),
        "-hls_list_size",
        str(config.list_size),
        "-hls_flags",
        "delete_segments",
        str(output_path),
    ]
