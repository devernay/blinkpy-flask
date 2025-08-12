"""Stream service for Blink Camera Flask application.

This module handles all streaming-related business logic including
live stream management, HLS transcoding, and stream cleanup.
"""

from __future__ import annotations

__all__ = [
    "initialize_stream_manager",
    "ensure_stream_manager_initialized",
    "start_camera_stream",
    "stop_camera_stream",
    "is_stream_active",
    "get_hls_file",
]

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blinkapp.models.ids import CameraId
    from stream_manager import StreamManager

logger = logging.getLogger(__name__)

# Global stream manager instance
stream_manager: StreamManager | None = None


def initialize_stream_manager() -> None:
    """Initialize the global stream manager instance."""
    global stream_manager
    from blinkapp import Config
    from stream_manager import StreamConfig, StreamManager

    stream_config = StreamConfig(
        segment_time=Config.HLS_SEGMENT_TIME,
        list_size=Config.HLS_LIST_SIZE,
        timeout=Config.FFMPEG_TIMEOUT,
        idle_timeout=Config.STREAM_IDLE_TIMEOUT,
    )
    stream_manager = StreamManager(stream_config)


def ensure_stream_manager_initialized():
    """Ensure stream manager is initialized.

    Returns:
        Initialized stream manager instance

    Raises:
        RuntimeError: If stream_manager hasn't been initialized
    """
    if stream_manager is None:
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
        Tuple of (hls_url, error_message)
    """
    try:
        stream_manager = ensure_stream_manager_initialized()
        if stream_manager is None:
            return None, "Stream manager not available"

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
        if stream_manager is None:
            return False

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
        if stream_manager is None:
            return False

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
        Tuple of (file_content, content_type)
    """
    try:
        stream_manager = ensure_stream_manager_initialized()
        if stream_manager is None:
            return None, None

        return stream_manager.get_hls_file(str(camera_id), filename)
    except Exception as e:
        logger.error(f"Failed to get HLS file {filename} for camera {camera_id}: {e}")
        return None, None
