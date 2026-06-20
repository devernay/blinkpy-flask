"""Live-view recording service.

Captures a live-view session to a working file while it is being viewed, then
either keeps it (remuxed to MP4 with a thumbnail and sidecar metadata) or
discards it when the session ends, based on the user's "Save" choice.

Recordings are stored in a directory separate from the cache (they are
user-owned media, not cached copies of Blink-server items). They surface in
the clip list with a "Live View" event type.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from blinkapp.config import Config
from blinkapp.models.ids import ClipId
from blinkapp.models.types import JsonDict

logger = logging.getLogger(__name__)

__all__ = [
    "RecordingSession",
    "create_session",
    "delete_recording",
    "finalize_session",
    "get_recording_file",
    "list_recording_clips",
    "recording_thumbnail_path",
]


@dataclass
class RecordingSession:
    """State for an in-progress live-view recording."""

    clip_id: ClipId
    camera_id: str
    camera_name: str
    started_at: datetime
    working_path: Path  # MPEG-TS file FFmpeg writes while the live view is active
    save: bool  # Whether to keep the recording when the session ends


def create_session(camera_id: str, camera_name: str, save: bool) -> RecordingSession:
    """Create a recording session and its working-file path.

    Args:
        camera_id: Camera the live view is from.
        camera_name: Human-readable camera name for clip metadata.
        save: Initial save state (typically the "Save all Live Views" setting).

    Returns:
        A RecordingSession whose working_path FFmpeg should write to.
    """
    from blinkapp.services.cache_service import get_recordings_working_dir

    now = datetime.now(UTC)
    # Microsecond precision so two live views of the same camera started in
    # quick succession cannot collide on clip id / working file / output paths.
    clip_id = ClipId.from_liveview(str(camera_id), int(now.timestamp() * 1_000_000))
    working_path = get_recordings_working_dir() / f"{clip_id}.ts"
    return RecordingSession(
        clip_id=clip_id,
        camera_id=str(camera_id),
        camera_name=camera_name,
        started_at=now,
        working_path=working_path,
        save=save,
    )


def finalize_session(session: RecordingSession, save: bool) -> bool:
    """Finish a recording session: keep it if saved, else discard.

    When kept, the working MPEG-TS file is remuxed to MP4, a thumbnail is
    generated into the thumbnail cache, and a JSON sidecar with clip metadata
    is written so the recording appears in the clip list.

    Args:
        session: The session to finalize.
        save: Whether to keep the recording.

    Returns:
        True if the recording was kept, False if discarded or unavailable.
    """
    working = session.working_path
    try:
        if not save:
            logger.info("Discarding unsaved live-view recording %s", session.clip_id)
            return False

        if not working.exists() or working.stat().st_size == 0:
            logger.warning(
                "No live-view recording data captured for %s", session.clip_id
            )
            return False

        recordings_dir = _recordings_dir()
        mp4_path = recordings_dir / f"{session.clip_id}.mp4"

        # Remux MPEG-TS -> MP4 without re-encoding (fast, lossless).
        remux = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(working),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(mp4_path),
            ],
            capture_output=True,
            timeout=Config.FFMPEG_TIMEOUT,
        )
        if remux.returncode != 0 or not mp4_path.exists():
            logger.error(
                "Failed to remux live-view recording %s: %s",
                session.clip_id,
                remux.stderr.decode(errors="replace") if remux.stderr else "",
            )
            return False

        _generate_thumbnail(session.clip_id, mp4_path)
        _write_metadata(session)
        logger.info("Saved live-view recording %s", session.clip_id)
        return True
    except Exception as e:  # never let cleanup failures break stream teardown
        logger.error("Error finalizing live-view recording %s: %s", session.clip_id, e)
        return False
    finally:
        working.unlink(missing_ok=True)


def list_recording_clips() -> list[JsonDict]:
    """List saved live-view recordings as clip dicts for the clip list.

    Returns:
        A list of clip dicts (same shape the UI expects) with event_type
        "Live View".
    """
    from blinkapp.utils.formatters import format_clip_time

    recordings_dir = _recordings_dir()
    clips: list[JsonDict] = []
    if not recordings_dir.exists():
        return clips

    for meta_file in recordings_dir.glob("*.json"):
        try:
            meta = json.loads(meta_file.read_text())
            clip_id_str = str(meta["id"])
            created_at = datetime.fromisoformat(meta["created_at"])
            thumbnail_exists = recording_thumbnail_path(ClipId(clip_id_str)).exists()
            clips.append(
                {
                    "id": clip_id_str,
                    "camera_name": meta.get("camera_name", "Unknown"),
                    "created_at": meta["created_at"],
                    "system_name": meta.get("system_name", Config.DEFAULT_SYSTEM_NAME),
                    "time": format_clip_time(created_at),
                    "event_type": "Live View",
                    "thumbnail": (
                        f"/api/clips/{clip_id_str}/thumbnail"
                        if thumbnail_exists
                        else None
                    ),
                    "media_url": f"/api/clips/{clip_id_str}/download",
                }
            )
        except Exception as e:
            logger.warning("Skipping invalid recording metadata %s: %s", meta_file, e)
    return clips


def get_recording_file(clip_id: ClipId) -> Path | None:
    """Return the MP4 path for a saved live-view recording, if it exists.

    Args:
        clip_id: The live-view clip identifier.

    Returns:
        Path to the recording's MP4 file, or None if it does not exist.
    """
    mp4_path = _recordings_dir() / f"{clip_id}.mp4"
    return mp4_path if mp4_path.exists() else None


def delete_recording(clip_id: ClipId) -> bool:
    """Delete a saved live-view recording, its metadata, and its thumbnail.

    Args:
        clip_id: The live-view clip identifier to delete.

    Returns:
        True if a recording file or metadata was removed.
    """
    recordings_dir = _recordings_dir()
    removed = False
    for suffix in (".mp4", ".json"):
        target = recordings_dir / f"{clip_id}{suffix}"
        if target.exists():
            target.unlink()
            removed = True
    thumbnail = recording_thumbnail_path(clip_id)
    if thumbnail.exists():
        thumbnail.unlink()
    return removed


def _recordings_dir() -> Path:
    from blinkapp.services.cache_service import get_recordings_dir

    return get_recordings_dir()


def recording_thumbnail_path(clip_id: ClipId) -> Path:
    """Path to a live-view recording's thumbnail (stored with the recording).

    Kept in the recordings directory (not the cache) so clearing the clip
    cache does not delete recording thumbnails.

    Args:
        clip_id: The live-view clip identifier.

    Returns:
        Path to the recording's JPEG thumbnail.
    """
    return _recordings_dir() / f"{clip_id}.jpg"


def _generate_thumbnail(clip_id: ClipId, mp4_path: Path) -> None:
    """Extract a thumbnail frame into the recordings directory."""
    thumbnail_path = recording_thumbnail_path(clip_id)
    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(mp4_path),
            "-ss",
            "1",
            "-vframes",
            "1",
            str(thumbnail_path),
        ],
        capture_output=True,
        timeout=Config.FFMPEG_TIMEOUT,
    )
    if result.returncode != 0:
        logger.warning("Failed to generate thumbnail for %s", clip_id)


def _write_metadata(session: RecordingSession) -> None:
    """Write the JSON sidecar that makes a recording appear in the clip list."""
    metadata: JsonDict = {
        "id": str(session.clip_id),
        "camera_id": session.camera_id,
        "camera_name": session.camera_name,
        "created_at": session.started_at.isoformat(),
        "event_type": "Live View",
    }
    sidecar = _recordings_dir() / f"{session.clip_id}.json"
    sidecar.write_text(json.dumps(metadata))
