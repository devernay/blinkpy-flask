"""HLS streaming service for the Blink Camera Flask application.

This module handles HLS (HTTP Live Streaming) specific functionality including
TCP URL parsing, HLS URL generation, and FFmpeg process management for
converting TCP streams to HLS format.
"""

import logging
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from blinkapp.config import Config

logger = logging.getLogger(__name__)

__all__ = [
    "parse_tcp_url",
    "generate_hls_url",
    "HLSStreamConfig",
    "HLSStream",
    "_create_ffmpeg_process",
    "_build_ffmpeg_command",
]


def parse_tcp_url(tcp_url: str) -> dict[str, str]:
    """Parse TCP URL components - pure function.

    Args:
        tcp_url: TCP URL string to parse (e.g., "tcp://host:port").

    Returns:
        dict[str, str]: Dictionary with protocol, host, and port components.
    """
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
    """Generate HLS URL for camera - pure function.

    Args:
        camera_id: Camera identifier for the stream.
        base_url: Base URL for the HLS server (default: "http://localhost:8080").

    Returns:
        str: Complete HLS playlist URL for the camera.
    """
    return f"{base_url}/hls/{camera_id}/playlist.m3u8"


@dataclass
class HLSStreamConfig:
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
    cmd: list[str], process_factory: type[subprocess.Popen] | None = None
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


def _build_ffmpeg_command(
    tcp_url: str, output_path: Path, config: HLSStreamConfig
) -> list[str]:
    """Build FFmpeg command for TCP to HLS transcoding.

    Creates FFmpeg command to convert MPEG-TS stream from TCP source
    into HLS segments suitable for web browser playback.

    Args:
        tcp_url: Source TCP stream URL (e.g., "tcp://127.0.0.1:8080")
        output_path: Output path for HLS playlist file
        config: HLS configuration with segment timing

    Returns:
        List of FFmpeg command arguments
    """
    return [
        "ffmpeg",
        "-i",
        tcp_url,  # Input: TCP stream source
        "-c",
        "copy",  # Codec: Copy without re-encoding (faster)
        "-f",
        "hls",  # Format: HTTP Live Streaming
        "-hls_time",
        str(config.segment_time),  # Segment duration in seconds
        "-hls_list_size",
        str(config.list_size),  # Max segments in playlist
        "-hls_flags",
        "delete_segments",  # Auto-delete old segments
        str(output_path),  # Output playlist file
    ]


class HLSStream:
    """Manages a single HLS stream from TCP source."""

    def __init__(self, camera_id: str, tcp_url: str, config: HLSStreamConfig) -> None:
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
                    # Clean up temp directory if process creation failed
                    if self.temp_dir is not None:
                        self.temp_dir.cleanup()
                        self.temp_dir = None
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
        """Check if stream is active.

        Returns:
            bool: True if stream is running and within timeout limits, False otherwise.
        """
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
        """Get HLS stream URL.

        Returns:
            str | None: HLS stream URL if available, None otherwise.
        """
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
