"""Stream service for Blink Camera Flask application.

This module handles all streaming-related business logic including
live stream management, HLS transcoding, and stream cleanup.
"""

from __future__ import annotations

import concurrent.futures
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable as CallableType

    from blinkpy.livestream import BlinkLiveStream


from blinkapp.services.hls_service import (
    HLSStream,
    HLSStreamConfig,
)

__all__ = [
    "StreamManager",
    "create_stream_manager",
    "ensure_stream_manager_initialized",
    "generate_hls_url",
    "get_hls_file",
    "init_camera_stream",
    "initialize_stream_manager",
    "is_stream_active",
    "parse_tcp_url",
    "start_camera_stream",
    "stop_camera_stream",
    "stream_manager",
    "validate_camera_id",
    "validate_tcp_url",
]

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable as CallableType
    from pathlib import Path

    from blinkpy.camera import BlinkCamera

    from blinkapp.models.ids import CameraId
    from blinkapp.services.liveview_recording import RecordingSession


if TYPE_CHECKING:
    from blinkapp.models.ids import CameraId

logger = logging.getLogger(__name__)

# Global stream manager instance
stream_manager: StreamManager | None = None

# Active live-view recording sessions, keyed by camera id (str). Populated when a
# live view starts and consumed (kept or discarded) when it stops.
_recording_sessions: dict[str, RecordingSession] = {}
_recording_lock = threading.Lock()


def set_live_view_save_state(camera_id: CameraId, saved: bool) -> bool:
    """Toggle whether the active live-view recording will be kept on stop.

    Args:
        camera_id: Camera whose live-view session to update.
        saved: True to keep the recording when the session ends, False to discard.

    Returns:
        True if there is an active session that was updated, else False.
    """
    with _recording_lock:
        session = _recording_sessions.get(str(camera_id))
        if session is None:
            return False
        session.save = saved
        return True


def get_live_view_save_state(camera_id: CameraId) -> bool:
    """Return the current save state of the active live-view session.

    Args:
        camera_id: Camera whose live-view session to query.

    Returns:
        True if the active session will be kept on stop, else False (also
        False when there is no active session).
    """
    with _recording_lock:
        session = _recording_sessions.get(str(camera_id))
        return bool(session.save) if session is not None else False


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
    # Start the background idle-stream sweeper (app-level startup only, so
    # unit tests that construct StreamManager directly don't spawn threads).
    try:
        stream_manager.start_idle_sweeper()
    except AttributeError:
        # Custom/mock factories may return objects without a sweeper.
        pass


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
        # stop_stream finalizes via the manager; this is a fallback for the
        # already-stopped case (idempotent if the session was already taken).
        _schedule_finalize(camera_id)
        return True
    except Exception as e:
        logger.error(f"Failed to stop stream for camera {camera_id}: {e}")
        _schedule_finalize(camera_id)
        return False


def _schedule_finalize(camera_id: CameraId | str, wait: bool = False) -> None:
    """Finalize (keep or discard) the live-view recording for a camera.

    Pops the active recording session and finalizes it according to its save
    flag. By default this runs on a background daemon thread so the blocking
    FFmpeg remux/thumbnail work never stalls the caller (e.g. an HTTP request
    or a lock-holding teardown path). Pass wait=True to run synchronously
    (used on shutdown so recordings are persisted before exit).

    Args:
        camera_id: Camera whose recording session to finalize.
        wait: If True, finalize synchronously instead of on a thread.
    """
    with _recording_lock:
        session = _recording_sessions.pop(str(camera_id), None)
    if session is None:
        return

    from blinkapp.services.liveview_recording import finalize_session

    if wait:
        finalize_session(session, session.save)
        return
    threading.Thread(
        target=finalize_session,
        args=(session, session.save),
        name=f"finalize-recording-{camera_id}",
        daemon=True,
    ).start()


def _discard_recording_session(camera_id: CameraId | str) -> None:
    """Drop a recording session and delete its (empty) working file.

    Used when a live view fails to start, so a registered session and its
    partial working file are not left behind.

    Args:
        camera_id: Camera whose pending recording session to discard.
    """
    with _recording_lock:
        session = _recording_sessions.pop(str(camera_id), None)
    if session is None:
        return
    from blinkapp.services.liveview_recording import finalize_session

    finalize_session(session, save=False)


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
        self.camera_streams: dict[
            str, BlinkLiveStream
        ] = {}  # Store Blink camera streams
        self.feed_tasks: dict[
            str, concurrent.futures.Future[None]
        ] = {}  # Store feed() tasks for cleanup
        self.lock = threading.Lock()
        # Background idle-stream sweeper (started via start_idle_sweeper()).
        self._sweeper_stop = threading.Event()
        self._sweeper_thread: threading.Thread | None = None

    def start_idle_sweeper(self) -> None:
        """Start a background thread that periodically reaps idle streams.

        Idempotent: a second call while a sweeper is running is a no-op. The
        sweeper runs as a daemon thread and exits when shutdown() is called.
        """
        if self._sweeper_thread is not None and self._sweeper_thread.is_alive():
            return
        self._sweeper_stop.clear()
        self._sweeper_thread = threading.Thread(
            target=self._sweep_loop, name="hls-idle-sweeper", daemon=True
        )
        self._sweeper_thread.start()

    def _sweep_loop(self) -> None:
        """Periodically clean up idle streams until asked to stop."""
        from blinkapp.config import Config

        interval = Config.STREAM_CLEANUP_INTERVAL
        while not self._sweeper_stop.wait(interval):
            try:
                self.cleanup_inactive_streams()
            except Exception as e:
                logger.warning(f"Idle stream sweep error: {e}")

    def start_stream(
        self,
        camera_id: str,
        tcp_url: str,
        camera_stream: BlinkLiveStream | None = None,
        record_path: Path | None = None,
    ) -> tuple[str | None, str | None]:
        """Start HLS stream for camera.

        Args:
            camera_id: Camera identifier
            tcp_url: TCP stream URL
            camera_stream: Optional Blink camera stream for cleanup
            record_path: Optional path to also record the full session

        Returns:
            Tuple of (hls_url, error_message)
        """
        # Stop any existing stream for this camera first (hold the lock only
        # briefly to detach it from the registry).
        with self.lock:
            existing = self.streams.pop(camera_id, None)
        if existing is not None:
            existing.stop()
            with self.lock:
                self._release_camera_stream(camera_id)

        # Create and start the new stream WITHOUT holding the manager lock, so
        # the ~2s FFmpeg warm-up does not block stream operations for other
        # cameras (get_hls_file/is_stream_active/stop on the whole manager).
        stream = HLSStream(camera_id, tcp_url, self.config, record_path)
        hls_url, error = stream.start()

        if hls_url:
            with self.lock:
                self.streams[camera_id] = stream
                # Store camera stream for cleanup if provided
                if camera_stream:
                    self.camera_streams[camera_id] = camera_stream
            return hls_url, None
        return None, error

    def _release_camera_stream(self, camera_id: str) -> None:
        """Stop the Blink camera stream and cancel its feed task.

        Must be called with self.lock held. Safe to call when nothing is
        registered for the camera.

        Args:
            camera_id: Camera identifier whose resources to release.
        """
        # Cancel the asyncio feed() task so it doesn't leak.
        feed_task = self.feed_tasks.pop(camera_id, None)
        if feed_task is not None:
            try:
                feed_task.cancel()
            except Exception as e:
                logger.warning(f"Error cancelling feed task for {camera_id}: {e}")

        # Stop the Blink camera (TCP proxy) stream.
        camera_stream = self.camera_streams.pop(camera_id, None)
        if camera_stream is not None:
            try:
                camera_stream.stop()
            except Exception as e:
                logger.warning(f"Error stopping camera stream for {camera_id}: {e}")

    def stop_stream(self, camera_id: str) -> None:
        """Stop stream for camera.

        Args:
            camera_id: Camera identifier for the stream to stop.
        """
        with self.lock:
            # Stop HLS stream (FFmpeg)
            if camera_id in self.streams:
                self.streams[camera_id].stop()
                del self.streams[camera_id]

            # Stop Blink camera stream and cancel its feed task
            self._release_camera_stream(camera_id)

        # Keep or discard the live-view recording (non-blocking).
        _schedule_finalize(camera_id)

    def register_feed_task(
        self, camera_id: str, feed_task: concurrent.futures.Future[None]
    ) -> None:
        """Register a camera's feed() task under the manager lock.

        Args:
            camera_id: Camera identifier the feed task belongs to.
            feed_task: The scheduled feed() future to track for cleanup.
        """
        with self.lock:
            self.feed_tasks[camera_id] = feed_task

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
                stream.stop()
                del self.streams[camera_id]
                self._release_camera_stream(camera_id)
                finalize = True
            else:
                finalize = False
        if finalize:
            # Idle/dead stream removed: finalize its recording (non-blocking).
            _schedule_finalize(camera_id)
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
        """Clean up inactive streams and their camera/feed resources."""
        with self.lock:
            inactive_cameras: list[str] = []
            for camera_id, stream in self.streams.items():
                if not stream.is_active():
                    inactive_cameras.append(camera_id)

            for camera_id in inactive_cameras:
                self.streams[camera_id].stop()
                del self.streams[camera_id]
                self._release_camera_stream(camera_id)

        # Finalize recordings for the reaped cameras (non-blocking, no lock).
        for camera_id in inactive_cameras:
            _schedule_finalize(camera_id)

    def shutdown(self) -> None:
        """Shutdown all streams and release all camera/feed resources."""
        # Stop the idle sweeper first so it doesn't race with teardown.
        self._sweeper_stop.set()
        with self.lock:
            for stream in self.streams.values():
                stream.stop()
            self.streams.clear()

            # Cancel any feed tasks and stop any camera streams still tracked.
            cameras = list(self.camera_streams.keys() | self.feed_tasks.keys())
            for camera_id in cameras:
                self._release_camera_stream(camera_id)

        # Finalize any in-progress recordings synchronously so saved live views
        # are persisted before the process exits.
        for camera_id in set(cameras) | set(_recording_sessions.keys()):
            _schedule_finalize(camera_id, wait=True)


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
    from blinkapp.services.hls_service import get_hls_output_dir

    hls_output_dir = get_hls_output_dir()
    if hls_output_dir is None:
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
            logger.error(
                f"Failed to initialize livestream for camera {camera_id} - camera may not support live streaming"
            )
            return None, None

        # Type assertion: we know init_livestream returns BlinkLiveStream
        from blinkpy.livestream import BlinkLiveStream

        if not isinstance(camera_stream_result, BlinkLiveStream):
            logger.error(
                f"Unexpected stream type for camera {camera_id}: {type(camera_stream_result)}"
            )
            return None, None

        camera_stream = camera_stream_result

        # Start the camera stream
        connection.execute(camera_stream.start())
        tcp_url = camera_stream.url

        # Initialize stream manager first
        stream_manager = ensure_stream_manager_initialized()

        # Cleanly end any prior live view for this camera (stops its stream and
        # finalizes its recording) before starting a new one, so a previous
        # session is never silently orphaned.
        stream_manager.stop_stream(str(camera_id))

        # Create a live-view recording session. Recording always starts with the
        # live view; whether it is kept is decided by the Save state at stop time.
        from blinkapp.services.liveview_recording import create_session
        from blinkapp.services.settings_service import get_save_all_live_views

        camera_name = getattr(camera, "name", str(camera_id))
        session = create_session(
            str(camera_id), camera_name, save=get_save_all_live_views()
        )
        with _recording_lock:
            _recording_sessions[str(camera_id)] = session

        try:
            # Schedule feed() to run asynchronously and store task (under the
            # manager lock so it doesn't race with teardown iterations).
            import asyncio

            if connection.loop:
                feed_task = asyncio.run_coroutine_threadsafe(
                    camera_stream.feed(), connection.loop
                )
                stream_manager.register_feed_task(str(camera_id), feed_task)

            # Start HLS transcoding (with parallel recording) and store camera stream
            hls_url, error = stream_manager.start_stream(
                str(camera_id), tcp_url, camera_stream, record_path=session.working_path
            )
        except Exception:
            # Anything failing after the session was registered must not leave
            # the session, feed task, or working file behind.
            stream_manager.stop_stream(str(camera_id))
            _discard_recording_session(camera_id)
            raise

        if hls_url is not None:
            logger.info(f"Started live stream for camera {camera_id}: {hls_url}")
            return camera_stream, hls_url
        # Stream failed to start: drop the unused recording session + feed task.
        stream_manager.stop_stream(str(camera_id))
        _discard_recording_session(camera_id)
        logger.error(f"Failed to start stream for camera {camera_id}: {error}")
        return None, None

    except Exception as e:
        logger.error(f"Error initializing stream for camera {camera_id}: {e}")
        return None, None
