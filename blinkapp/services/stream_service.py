"""Stream service for Blink Camera Flask application.

This module handles all streaming-related business logic including
live stream management, HLS transcoding, and stream cleanup.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable as CallableType

    from blinkapp.config import Config

from blinkapp.services.hls_service import (
    HLSStream,
    HLSStreamConfig,
)

__all__ = [
    "initialize_stream_manager",
    "create_stream_manager",
    "ensure_stream_manager_initialized",
    "start_camera_stream",
    "stop_camera_stream",
    "is_stream_active",
    "get_hls_file",
    "init_camera_stream",
    "StreamManager",
    "stream_manager",
    "generate_hls_url",
    "parse_tcp_url",
    "validate_camera_id",
    "validate_tcp_url",
]

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable as CallableType

    from blinkpy.camera import BlinkCamera

    from blinkapp.config import Config
    from blinkapp.models.ids import CameraId


if TYPE_CHECKING:
    from blinkapp.models.ids import CameraId

logger = logging.getLogger(__name__)

# Global stream manager instance
stream_manager: StreamManager | None = None


def initialize_stream_manager(
    manager_factory: CallableType[[HLSStreamConfig], StreamManager] | None = None,
) -> None:
    """Initialize the global stream manager instance with injectable factory.

    Args:
        manager_factory: Optional factory function for creating StreamManager instances.
    """
    global stream_manager
    from blinkapp import Config

    if manager_factory is None:

        def default_factory(config: HLSStreamConfig) -> StreamManager:
            """Default factory function for creating StreamManager instances.

            Args:
                config: Configuration object for the StreamManager.

            Returns:
                StreamManager: New StreamManager instance.
            """
            return StreamManager(config)

        manager_factory = default_factory

    stream_config = HLSStreamConfig(
        segment_time=Config.HLS_SEGMENT_TIME,
        list_size=Config.HLS_LIST_SIZE,
        timeout=Config.FFMPEG_TIMEOUT,
        idle_timeout=Config.STREAM_IDLE_TIMEOUT,
    )
    stream_manager = manager_factory(stream_config)


def create_stream_manager(config: HLSStreamConfig | None = None) -> StreamManager:
    """Factory function for stream manager - easily mockable.

    Args:
        config: Optional HLS stream configuration.

    Returns:
        StreamManager: New StreamManager instance with provided configuration.
    """
    return StreamManager(config)


def ensure_stream_manager_initialized(
    manager_factory: CallableType[[HLSStreamConfig], StreamManager] | None = None,
) -> StreamManager:
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


class StreamManager:
    """Manages multiple HLS streams from Blink cameras.

    This class coordinates the creation, management, and cleanup of HLS streams
    that transcode MPEG-TS data from Blink camera TCP streams into web-compatible
    HLS format using FFmpeg.

    Features:
    - Thread-safe stream management with locking
    - Automatic cleanup of inactive streams
    - Stream status tracking and monitoring
    - Error handling and recovery

    Each stream runs in its own process via FFmpeg, converting the raw MPEG-TS
    stream from Blink's TCP proxy into segmented HLS files that can be played
    in web browsers.
    """

    def __init__(self, config: HLSStreamConfig | None = None) -> None:
        """Initialize stream manager.

        Args:
            config: Default stream configuration
        """
        self.config = config or HLSStreamConfig()
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
        """Stop stream for camera.

        Args:
            camera_id: Camera identifier for the stream to stop.
        """
        with self.lock:
            if camera_id in self.streams:
                self.streams[camera_id].stop()
                del self.streams[camera_id]

    def is_stream_active(self, camera_id: str) -> bool:
        """Check if stream is active for camera.

        Args:
            camera_id: Camera identifier to check stream status for.

        Returns:
            bool: True if stream is active, False otherwise.
        """
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


def generate_hls_url(camera_id: str, filename: str) -> str:
    """Generate HLS URL for camera stream.

    Args:
        camera_id: Camera identifier for the stream.
        filename: HLS filename (playlist or segment).

    Returns:
        str: Complete HLS URL for the camera stream file.
    """
    return f"/api/cameras/{camera_id}/streams/{filename}"


def parse_tcp_url(tcp_url: str) -> tuple[str, int]:
    """Parse TCP URL to extract host and port.

    Args:
        tcp_url: TCP URL string in format "tcp://host:port".

    Returns:
        tuple[str, int]: Tuple of (host, port) extracted from URL.
    """
    if not tcp_url.startswith("tcp://"):
        raise ValueError("Invalid TCP URL format")

    url_part = tcp_url[6:]  # Remove "tcp://"
    if ":" not in url_part:
        raise ValueError("TCP URL must include port")

    host, port_str = url_part.split(":", 1)
    try:
        port = int(port_str)
    except ValueError as e:
        raise ValueError("Invalid port number") from e

    return host, port


def validate_camera_id(camera_id: str) -> bool:
    """Validate camera ID format.

    Args:
        camera_id: Camera identifier string to validate.

    Returns:
        bool: True if camera ID is valid, False otherwise.
    """
    return isinstance(camera_id, str) and len(camera_id.strip()) > 0


def validate_tcp_url(tcp_url: str) -> bool:
    """Validate TCP URL format.

    Args:
        tcp_url: TCP URL string to validate.

    Returns:
        bool: True if TCP URL is valid, False otherwise.
    """
    try:
        parse_tcp_url(tcp_url)
        return True
    except (ValueError, AttributeError):
        return False


def init_camera_stream(
    camera: BlinkCamera, camera_id: CameraId
) -> tuple[object | None, str | None]:
    """Initialize camera stream and return stream object and HLS URL.

    Args:
        camera: Camera object from blinkpy
        camera_id: Camera ID for stream management

    Returns:
        Tuple of (stream_object, hls_url) or (None, None) on failure
    """
    from blinkapp import HLS_OUTPUT_DIR

    if HLS_OUTPUT_DIR is None:
        logger.error("HLS output directory not configured")
        return None, None

    try:
        # Initialize camera livestream
        from blinkapp.services.blink_service import ensure_blink_connection_initialized

        connection = ensure_blink_connection_initialized()

        # Type assertion for camera - we know it's a BlinkCamera
        from blinkpy.camera import BlinkCamera

        if not isinstance(camera, BlinkCamera):
            logger.error(f"Invalid camera type for {camera_id}")
            return None, None

        # Initialize livestream on camera to get TCP stream
        camera_stream_result = connection.execute(camera.init_livestream())
        if camera_stream_result is None:
            logger.error(f"Failed to initialize livestream for camera {camera_id}")
            return None, None

        # Type assertion: we know init_livestream returns BlinkLiveStream
        from blinkpy.livestream import BlinkLiveStream

        if not isinstance(camera_stream_result, BlinkLiveStream):
            logger.error(f"Unexpected stream type: {type(camera_stream_result)}")
            return None, None

        camera_stream = camera_stream_result

        # Start the camera stream
        connection.execute(camera_stream.start())
        tcp_url = camera_stream.url

        # Initialize stream manager
        stream_manager = ensure_stream_manager_initialized()

        # Start HLS transcoding
        hls_url, error = stream_manager.start_stream(str(camera_id), tcp_url)
        if hls_url is not None:
            logger.info(f"Started live stream for camera {camera_id}: {hls_url}")
            return camera_stream, hls_url
        else:
            logger.error(f"Failed to start stream for camera {camera_id}: {error}")
            return None, None

    except Exception as e:
        logger.error(f"Error initializing stream for camera {camera_id}: {e}")
        return None, None
