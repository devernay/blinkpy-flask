"""TCP to HLS stream management module.

Provides object-oriented management of TCP streams from Blink cameras with FFmpeg transcoding
to HLS format. Handles multiple concurrent streams with automatic cleanup
and resource management.

This module specifically handles MPEG-TS streams from Blink's init_livestream() TCP proxy.
"""

import logging
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

# Import Config for timeout constants
from config import Config

logger = logging.getLogger(__name__)


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


class HLSStream:
    """Manages a single TCP to HLS transcoding stream for Blink cameras.

    This class handles the lifecycle of an FFmpeg process that converts
    MPEG-TS streams from Blink's TCP proxy into HLS format for web browsers.
    Each stream is isolated in its own temporary directory with automatic
    cleanup when the stream ends.

    The transcoding process uses FFmpeg with optimized settings for low-latency
    streaming from Blink cameras, producing .m3u8 playlists and .ts segments
    that can be consumed by HTML5 video players.

    Attributes:
        stream_id: Unique identifier for this stream (typically camera ID)
        tcp_url: Source TCP URL from Blink's init_livestream()
        config: Stream configuration with timeouts and HLS settings
        process: FFmpeg subprocess handle (None when not running)
        hls_dir: Temporary directory for HLS files
        playlist_path: Path to the main .m3u8 playlist file
        last_access: Timestamp of last access for idle cleanup
    """

    def __init__(self, stream_id: str, tcp_url: str, config: StreamConfig) -> None:
        """Initialize HLS stream instance.

        Creates a new HLS stream manager but doesn't start transcoding yet.
        Call start() to begin the FFmpeg process and HLS generation.

        Args:
            stream_id: Unique identifier for the stream (typically camera ID)
            tcp_url: TCP source URL from Blink's init_livestream()
                    (e.g., tcp://127.0.0.1:12345)
            config: Stream configuration with timeout and HLS parameters
        """
        super().__init__()
        self.stream_id = stream_id
        self.tcp_url = tcp_url
        self.config = config
        self.process: subprocess.Popen | None = None
        self.hls_dir: Path | None = None
        self.playlist_path: Path | None = None
        self.last_accessed = time.time()
        # Use lock to ensure thread-safe access to process and file operations
        self._lock = threading.Lock()

    def start(self) -> tuple[str | None, str | None]:
        """Start HLS transcoding from TCP stream.

        Launches FFmpeg to convert the MPEG-TS stream from Blink's TCP proxy
        into HLS format suitable for web browsers. Creates a temporary directory
        for HLS segments and playlist files.

        The FFmpeg process is configured for low-latency streaming with:
        - MPEG-TS input format (from Blink TCP stream)
        - H.264 video encoding with ultrafast preset
        - AAC audio encoding
        - HLS output with configurable segment duration
        - Automatic segment deletion to manage disk space

        Returns:
            Tuple of (playlist_url, error_message):
            - If successful: (URL string, None)
            - If failed: (None, error description)

        Example:
            >>> stream = HLSStream("camera123", "tcp://127.0.0.1:12345", config)
            >>> url, error = stream.start()
            >>> if error:
            ...     print(f"Stream failed: {error}")
            ... else:
            ...     print(f"Stream available at: {url}")
        """
        with self._lock:
            # Check if stream is already running
            if self.process and self.process.poll() is None:
                return f"/api/camera/{self.stream_id}/hls/playlist.m3u8", None

            # Create temporary directory for HLS files
            self.hls_dir = Path(tempfile.mkdtemp(prefix=f"hls_{self.stream_id}_"))
            self.playlist_path = self.hls_dir / "playlist.m3u8"

            # Build FFmpeg command for TCP MPEG-TS input from Blink livestream
            # This command is optimized for low-latency streaming from Blink cameras
            cmd = [
                "ffmpeg",
                "-f",
                "mpegts",  # Input format is MPEG-TS from Blink TCP stream
                "-i",
                self.tcp_url,  # TCP source URL from init_livestream()
                "-c:v",
                "libx264",  # H.264 video codec for broad compatibility
                "-c:a",
                "aac",  # AAC audio codec for web browsers
                "-preset",
                "ultrafast",  # Fastest encoding for low latency
                "-tune",
                "zerolatency",  # Optimize for real-time streaming
                "-f",
                "hls",  # Output format is HLS
                "-hls_time",
                str(self.config.segment_time),  # Segment duration
                "-hls_list_size",
                str(self.config.list_size),  # Playlist size
                "-hls_flags",
                "delete_segments",  # Auto-delete old segments
                str(self.playlist_path),  # Output playlist file
            ]

            try:
                logger.info(
                    f"Starting FFmpeg for Blink TCP stream {self.stream_id} with command: {' '.join(cmd)}"
                )
                # Start FFmpeg process with pipe redirection for error handling
                self.process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )

                # Check if process started successfully (brief delay for initialization)
                time.sleep(1)
                if self.process.poll() is not None:
                    # Process exited immediately - capture error details
                    stdout, stderr = self.process.communicate()
                    return_code = self.process.returncode
                    error_msg = (
                        stderr.decode("utf-8")
                        if stderr
                        else f"FFmpeg exited with code {return_code}"
                    )
                    logger.error(
                        f"FFmpeg failed for stream {self.stream_id} (exit code {return_code}): {error_msg}"
                    )
                    self._cleanup()
                    return None, error_msg

                logger.info(f"Started HLS stream {self.stream_id}")
                return f"/api/camera/{self.stream_id}/hls/playlist.m3u8", None

            except (OSError, subprocess.SubprocessError, PermissionError) as e:
                error_msg = f"Error starting stream {self.stream_id}: {e}"
                logger.error(error_msg)
                self._cleanup()
                return None, error_msg

    def stop(self) -> None:
        """Stop HLS transcoding and cleanup resources.

        Gracefully terminates the FFmpeg process and cleans up temporary
        files. Uses SIGTERM first, then SIGKILL if the process doesn't
        respond within the configured timeout.

        This method is safe to call multiple times and handles cases where
        the process has already exited.
        """
        with self._lock:
            if self.process:
                try:
                    # Try graceful termination first
                    self.process.terminate()
                    self.process.wait(timeout=Config.PROCESS_WAIT_TIMEOUT)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful termination fails
                    logger.warning(
                        f"Force killing FFmpeg process for stream {self.stream_id}"
                    )
                    self.process.kill()
                    self.process.wait()
                except (OSError, subprocess.SubprocessError) as e:
                    logger.error(
                        f"Error stopping process for stream {self.stream_id}: {e}"
                    )

                self.process = None

            self._cleanup()
            logger.debug(f"Stopped HLS stream {self.stream_id}")

    def update_access_time(self) -> None:
        """Update last accessed timestamp."""
        self.last_accessed = time.time()

    def is_idle(self) -> bool:
        """Check if stream has been idle too long."""
        if self.config.idle_timeout is None:
            return False
        return time.time() - self.last_accessed > self.config.idle_timeout

    def is_running(self) -> bool:
        """Check if stream is currently running."""
        with self._lock:
            return self.process is not None and self.process.poll() is None

    def get_file_path(self, filename: str) -> Path | None:
        """Get path to HLS file.

        Args:
            filename: HLS file name (playlist.m3u8 or segment.ts)

        Returns:
            Path to file if exists, None otherwise
        """
        if not self.hls_dir:
            return None

        file_path = self.hls_dir / filename
        return file_path if file_path.exists() else None

    def _cleanup(self) -> None:
        """Clean up temporary directory."""
        if self.hls_dir and self.hls_dir.exists():
            try:
                import shutil

                shutil.rmtree(self.hls_dir)
                self.hls_dir = None
                self.playlist_path = None
            except (OSError, PermissionError) as e:
                logger.error(
                    f"Error cleaning up HLS directory for stream {self.stream_id}: {e}"
                )


class StreamManager:
    """Manages multiple TCP to HLS streams for Blink cameras."""

    def __init__(self, config: StreamConfig | None = None) -> None:
        """Initialize stream manager.

        Args:
            config: Default stream configuration
        """
        self.config = config or StreamConfig()
        self.streams: dict[str, HLSStream] = {}
        self._lock = threading.Lock()
        self._cleanup_timer: threading.Timer | None = None
        self._start_cleanup_timer()

    def start_stream(
        self, stream_id: str, tcp_url: str
    ) -> tuple[str | None, str | None]:
        """Start or get existing HLS stream from Blink TCP source.

        Manages HLS stream lifecycle by either returning an existing active
        stream or creating a new one. Handles URL changes by stopping the
        old stream and creating a new one with the updated TCP source.

        Args:
            stream_id: Unique identifier for the stream (typically camera ID)
            tcp_url: TCP source URL from Blink's init_livestream() method

        Returns:
            Tuple of (playlist_url, error_message). On success, playlist_url
            contains the HLS playlist endpoint and error_message is None.
            On failure, playlist_url is None and error_message contains details.
        """
        with self._lock:
            # Stop existing stream if different URL to handle camera reconnections
            if stream_id in self.streams:
                existing_stream = self.streams[stream_id]
                if existing_stream.tcp_url != tcp_url:
                    # TCP URL changed, need to restart stream
                    existing_stream.stop()
                    del self.streams[stream_id]
                else:
                    # Same URL, update access time and return if still running
                    existing_stream.update_access_time()
                    if existing_stream.is_running():
                        return f"/api/camera/{stream_id}/hls/playlist.m3u8", None

            # Create new stream with FFmpeg transcoding
            stream = HLSStream(stream_id, tcp_url, self.config)
            result = stream.start()

            if result[0]:  # Success - store stream for management
                self.streams[stream_id] = stream

            return result

    def stop_stream(self, stream_id: str) -> None:
        """Stop specific stream and clean up resources.

        Args:
            stream_id: Stream identifier to stop
        """
        with self._lock:
            if stream_id in self.streams:
                self.streams[stream_id].stop()
                del self.streams[stream_id]

    def get_stream_file(self, stream_id: str, filename: str) -> Path | None:
        """Get HLS file path for stream if it exists and is valid.

        Args:
            stream_id: Stream identifier
            filename: HLS file name (playlist.m3u8 or segment file)

        Returns:
            Path to file if exists, None otherwise
        """
        with self._lock:
            if stream_id in self.streams:
                self.streams[stream_id].update_access_time()
                return self.streams[stream_id].get_file_path(filename)
        return None

    def cleanup_idle_streams(self) -> None:
        """Clean up streams that have been idle too long."""
        idle_streams = []

        with self._lock:
            for stream_id, stream in self.streams.items():
                if stream.is_idle():
                    idle_streams.append(stream_id)

        for stream_id in idle_streams:
            logger.info(f"Cleaning up idle stream {stream_id}")
            self.stop_stream(stream_id)

        # Reschedule cleanup if streams remain
        with self._lock:
            if self.streams:
                self._start_cleanup_timer()

    def shutdown(self) -> None:
        """Shutdown all streams and cleanup resources."""
        logger.info("Shutting down stream manager...")

        # Cancel cleanup timer
        if self._cleanup_timer:
            self._cleanup_timer.cancel()

        # Stop all streams
        with self._lock:
            stream_ids = list(self.streams.keys())

        for stream_id in stream_ids:
            self.stop_stream(stream_id)

        logger.info("Stream manager shutdown complete")

    def _start_cleanup_timer(self) -> None:
        """Start cleanup timer for idle streams."""
        if self._cleanup_timer:
            self._cleanup_timer.cancel()

        self._cleanup_timer = threading.Timer(60.0, self.cleanup_idle_streams)
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()
