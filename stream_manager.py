"""RTSP to HLS stream management module.

Provides object-oriented management of RTSP streams with FFmpeg transcoding
to HLS format. Handles multiple concurrent streams with automatic cleanup
and resource management.
"""

import logging
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class StreamConfig:
    """Configuration for HLS stream transcoding."""

    segment_time: int = 2  # HLS segment duration in seconds
    list_size: int = 3  # Number of segments in playlist
    timeout: int = 30  # Process timeout
    idle_timeout: int = 300  # Stream idle timeout (5 minutes)


class HLSStream:
    """Manages a single RTSP to HLS transcoding stream."""

    def __init__(self, stream_id: str, rtsp_url: str, config: StreamConfig):
        """Initialize HLS stream.

        Args:
            stream_id: Unique identifier for the stream
            rtsp_url: RTSP source URL
            config: Stream configuration
        """
        self.stream_id = stream_id
        self.rtsp_url = rtsp_url
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.hls_dir: Optional[Path] = None
        self.playlist_path: Optional[Path] = None
        self.last_accessed = time.time()
        self._lock = threading.Lock()

    def start(self) -> Tuple[Optional[str], Optional[str]]:
        """Start HLS transcoding.

        Returns:
            Tuple of (playlist_url, error_message)
        """
        with self._lock:
            if self.process and self.process.poll() is None:
                return f"/api/hls/{self.stream_id}/playlist.m3u8", None

            # Create temporary directory
            self.hls_dir = Path(tempfile.mkdtemp(prefix=f"hls_{self.stream_id}_"))
            self.playlist_path = self.hls_dir / "playlist.m3u8"

            # FFmpeg command
            cmd = [
                "ffmpeg",
                "-i",
                self.rtsp_url,
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-preset",
                "ultrafast",
                "-tune",
                "zerolatency",
                "-f",
                "hls",
                "-hls_time",
                str(self.config.segment_time),
                "-hls_list_size",
                str(self.config.list_size),
                "-hls_flags",
                "delete_segments",
                str(self.playlist_path),
            ]

            try:
                self.process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )

                # Check if process started successfully
                time.sleep(1)
                if self.process.poll() is not None:
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
                return f"/api/hls/{self.stream_id}/playlist.m3u8", None

            except Exception as e:
                error_msg = f"Error starting stream {self.stream_id}: {e}"
                logger.error(error_msg)
                self._cleanup()
                return None, error_msg

    def stop(self) -> None:
        """Stop HLS transcoding and cleanup resources."""
        with self._lock:
            if self.process:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(
                        f"Force killing FFmpeg process for stream {self.stream_id}"
                    )
                    self.process.kill()
                    self.process.wait()
                except Exception as e:
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
        return time.time() - self.last_accessed > self.config.idle_timeout

    def is_running(self) -> bool:
        """Check if stream is currently running."""
        with self._lock:
            return self.process is not None and self.process.poll() is None

    def get_file_path(self, filename: str) -> Optional[Path]:
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
            except Exception as e:
                logger.error(
                    f"Error cleaning up HLS directory for stream {self.stream_id}: {e}"
                )


class StreamManager:
    """Manages multiple RTSP to HLS streams."""

    def __init__(self, config: Optional[StreamConfig] = None):
        """Initialize stream manager.

        Args:
            config: Default stream configuration
        """
        self.config = config or StreamConfig()
        self.streams: Dict[str, HLSStream] = {}
        self._lock = threading.Lock()
        self._cleanup_timer: Optional[threading.Timer] = None
        self._start_cleanup_timer()

    def start_stream(
        self, stream_id: str, rtsp_url: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Start or get existing HLS stream.

        Args:
            stream_id: Unique identifier for the stream
            rtsp_url: RTSP source URL

        Returns:
            Tuple of (playlist_url, error_message)
        """
        with self._lock:
            # Stop existing stream if different URL
            if stream_id in self.streams:
                existing_stream = self.streams[stream_id]
                if existing_stream.rtsp_url != rtsp_url:
                    existing_stream.stop()
                    del self.streams[stream_id]
                else:
                    existing_stream.update_access_time()
                    if existing_stream.is_running():
                        return f"/api/hls/{stream_id}/playlist.m3u8", None

            # Create new stream
            stream = HLSStream(stream_id, rtsp_url, self.config)
            result = stream.start()

            if result[0]:  # Success
                self.streams[stream_id] = stream

            return result

    def stop_stream(self, stream_id: str) -> None:
        """Stop specific stream.

        Args:
            stream_id: Stream identifier to stop
        """
        with self._lock:
            if stream_id in self.streams:
                self.streams[stream_id].stop()
                del self.streams[stream_id]

    def get_stream_file(self, stream_id: str, filename: str) -> Optional[Path]:
        """Get HLS file path for stream.

        Args:
            stream_id: Stream identifier
            filename: HLS file name

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
