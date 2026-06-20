"""Tests for live-view recording behavior."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from blinkapp.models.ids import ClipId


class TestLiveViewClipId:
    """Live-view ClipId construction and detection."""

    def test_from_liveview_roundtrip(self) -> None:
        """Live-view clip IDs round-trip through their parts.

        Tests:
            - from_liveview builds the expected 'liveview-<cam>-<epoch>' value
            - is_liveview is True and is_local is False
            - get_liveview_parts recovers the camera id and epoch
        """
        clip_id = ClipId.from_liveview("400658", 1718880000)
        assert str(clip_id) == "liveview-400658-1718880000"
        assert clip_id.is_liveview() is True
        assert clip_id.is_local() is False
        assert clip_id.get_liveview_parts() == ("400658", 1718880000)

    def test_non_liveview_ids(self) -> None:
        """Cloud and local IDs are not detected as live-view recordings.

        Tests:
            - A numeric cloud id is not a live view
            - A local 'sync~id' clip is not a live view
        """
        assert ClipId("12345").is_liveview() is False
        assert ClipId.from_local("sync", 7).is_liveview() is False


class TestFfmpegRecordingOutput:
    """FFmpeg command construction for parallel recording."""

    def test_record_path_adds_second_output(self) -> None:
        """A record path adds a second MPEG-TS output to the command.

        Tests:
            - The HLS playlist output is still present
            - An mpegts output to the record path is appended
        """
        from blinkapp.services.hls_service import (
            HLSStreamConfig,
            _build_ffmpeg_command,
        )

        config = HLSStreamConfig(segment_time=2, list_size=3)
        cmd = _build_ffmpeg_command(
            "tcp://127.0.0.1:9000",
            Path("/tmp/stream.m3u8"),
            config,
            record_path=Path("/tmp/rec.ts"),
        )
        assert "hls" in cmd
        assert "/tmp/stream.m3u8" in cmd
        assert "mpegts" in cmd
        assert "/tmp/rec.ts" in cmd

    def test_no_record_path_has_no_recording_output(self) -> None:
        """Without a record path, no recording output is added.

        Tests:
            - The command contains no mpegts recording output when record_path
              is omitted
        """
        from blinkapp.services.hls_service import (
            HLSStreamConfig,
            _build_ffmpeg_command,
        )

        cmd = _build_ffmpeg_command(
            "tcp://127.0.0.1:9000", Path("/tmp/stream.m3u8"), HLSStreamConfig()
        )
        assert "mpegts" not in cmd


class TestSaveAllSetting:
    """The 'Save all Live Views' setting accessor."""

    def test_string_true_is_enabled(self, tmp_path: Path) -> None:
        """A persisted string 'true' enables save-all.

        Tests:
            - get_save_all_live_views interprets the string 'true' as enabled
        """
        from blinkapp.services import settings_service

        (tmp_path / "settings.json").write_text(
            json.dumps({"saveAllLiveViews": "true"})
        )
        assert settings_service.get_save_all_live_views() is True

    def test_bool_false_default(self) -> None:
        """The default (no settings file) is disabled.

        Tests:
            - get_save_all_live_views returns False when unset
        """
        from blinkapp.services import settings_service

        assert settings_service.get_save_all_live_views() is False


class TestSaveStateRegistry:
    """Server-side save-state toggle for the active live-view session."""

    def test_set_and_get_save_state(self) -> None:
        """The save state can be read and toggled for an active session.

        Tests:
            - get reflects the session's initial save state
            - set updates the state and returns True for an active session
        """
        from blinkapp.models.ids import CameraId
        from blinkapp.services import stream_service
        from blinkapp.services.liveview_recording import RecordingSession

        cam = CameraId("400658")
        session = RecordingSession(
            clip_id=ClipId.from_liveview("400658", 1718880000),
            camera_id="400658",
            camera_name="Front",
            started_at=datetime.now(UTC),
            working_path=Path("/tmp/rec.ts"),
            save=False,
        )
        stream_service._recording_sessions["400658"] = session
        try:
            assert stream_service.get_live_view_save_state(cam) is False
            assert stream_service.set_live_view_save_state(cam, True) is True
            assert stream_service.get_live_view_save_state(cam) is True
        finally:
            stream_service._recording_sessions.pop("400658", None)

    def test_set_save_state_no_session(self) -> None:
        """Setting save state with no active session returns False.

        Tests:
            - set_live_view_save_state returns False when no session exists
        """
        from blinkapp.models.ids import CameraId
        from blinkapp.services import stream_service

        assert stream_service.set_live_view_save_state(CameraId("999"), True) is False


class TestRecordingListingAndDelete:
    """Listing, merging, and deleting saved recordings."""

    def _write_recording(self, clip_id: ClipId) -> None:
        """Write a fake recording MP4 and metadata sidecar.

        Args:
            clip_id: The live-view clip id to create files for.
        """
        from blinkapp.services.cache_service import get_recordings_dir

        rec_dir = get_recordings_dir()
        rec_dir.mkdir(parents=True, exist_ok=True)
        (rec_dir / f"{clip_id}.mp4").write_bytes(b"fake-mp4")
        (rec_dir / f"{clip_id}.json").write_text(
            json.dumps(
                {
                    "id": str(clip_id),
                    "camera_id": "400658",
                    "camera_name": "Front Door",
                    "created_at": datetime.now(UTC).isoformat(),
                    "event_type": "Live View",
                }
            )
        )

    def test_list_recording_clips(self) -> None:
        """Saved recordings are listed as Live View clips.

        Tests:
            - list_recording_clips returns one clip for one recording
            - The clip carries event_type 'Live View' and its camera name
        """
        from blinkapp.services.liveview_recording import list_recording_clips

        clip_id = ClipId.from_liveview("400658", 1718880000)
        self._write_recording(clip_id)
        clips = list_recording_clips()
        assert len(clips) == 1
        assert clips[0]["id"] == str(clip_id)
        assert clips[0]["event_type"] == "Live View"
        assert clips[0]["camera_name"] == "Front Door"

    def test_merge_liveview_clips_into_empty(self) -> None:
        """Recordings merge into an empty clip listing.

        Tests:
            - merge_liveview_clips includes the recording in the day groups
        """
        from blinkapp.services.clip_service import merge_liveview_clips

        clip_id = ClipId.from_liveview("400658", 1718880000)
        self._write_recording(clip_id)
        groups = merge_liveview_clips([])
        all_ids = [c["id"] for g in groups for c in g["clips"]]
        assert str(clip_id) in all_ids

    def test_delete_recording(self) -> None:
        """Deleting a recording removes its files.

        Tests:
            - delete_recording returns True and removes the mp4 and sidecar
        """
        from blinkapp.services.cache_service import get_recordings_dir
        from blinkapp.services.liveview_recording import delete_recording

        clip_id = ClipId.from_liveview("400658", 1718880000)
        self._write_recording(clip_id)
        assert delete_recording(clip_id) is True
        assert not (get_recordings_dir() / f"{clip_id}.mp4").exists()
        assert not (get_recordings_dir() / f"{clip_id}.json").exists()


class TestRecordingRetention:
    """Retention cleanup for saved recordings and stray working files."""

    def _write_recording_with_age(self, clip_id: ClipId, days_old: int) -> None:
        """Write a recording whose sidecar created_at is N days in the past.

        Args:
            clip_id: Live-view clip id to create.
            days_old: How many days old the recording's created_at should be.
        """
        from blinkapp.services.cache_service import get_recordings_dir

        rec_dir = get_recordings_dir()
        rec_dir.mkdir(parents=True, exist_ok=True)
        (rec_dir / f"{clip_id}.mp4").write_bytes(b"fake")
        created = datetime.now(UTC) - timedelta(days=days_old)
        (rec_dir / f"{clip_id}.json").write_text(
            json.dumps(
                {
                    "id": str(clip_id),
                    "camera_id": "400658",
                    "camera_name": "Front",
                    "created_at": created.isoformat(),
                    "event_type": "Live View",
                }
            )
        )

    def _set_retention(self, tmp_path: Path, value: str) -> None:
        """Write a settings file with the given localClipRetention value.

        Args:
            tmp_path: Per-test temp dir (where settings.json is patched to live).
            value: The localClipRetention value to persist.
        """
        (tmp_path / "settings.json").write_text(
            json.dumps({"localClipRetention": value})
        )

    def test_never_keeps_all(self, tmp_path: Path) -> None:
        """localClipRetention 'never' keeps recordings regardless of age.

        Tests:
            - cleanup_recordings removes nothing when retention is 'never'
        """
        from blinkapp.services.cache_service import get_recordings_dir
        from blinkapp.services.liveview_recording import cleanup_recordings

        self._set_retention(tmp_path, "never")
        old = ClipId.from_liveview("400658", 1)
        self._write_recording_with_age(old, days_old=100)
        assert cleanup_recordings() == 0
        assert (get_recordings_dir() / f"{old}.mp4").exists()

    def test_deletes_old_keeps_recent(self, tmp_path: Path) -> None:
        """A day-based retention deletes old recordings and keeps recent ones.

        Tests:
            - With retention '7', a 30-day-old recording is removed
            - A 1-day-old recording is kept
        """
        from blinkapp.services.cache_service import get_recordings_dir
        from blinkapp.services.liveview_recording import cleanup_recordings

        self._set_retention(tmp_path, "7")
        old = ClipId.from_liveview("400658", 111)
        recent = ClipId.from_liveview("400658", 222)
        self._write_recording_with_age(old, days_old=30)
        self._write_recording_with_age(recent, days_old=1)

        removed = cleanup_recordings()
        assert removed == 1
        rec_dir = get_recordings_dir()
        assert not (rec_dir / f"{old}.mp4").exists()
        assert not (rec_dir / f"{old}.json").exists()
        assert (rec_dir / f"{recent}.mp4").exists()

    def test_sweeps_stray_working_files(self, tmp_path: Path) -> None:
        """Orphaned working .ts files older than the threshold are removed.

        Tests:
            - An old .working/*.ts file is deleted by cleanup_recordings
            - A fresh working file is retained
        """
        import os
        import time

        from blinkapp.services.cache_service import get_recordings_working_dir
        from blinkapp.services.liveview_recording import cleanup_recordings

        self._set_retention(tmp_path, "never")
        working = get_recordings_working_dir()
        working.mkdir(parents=True, exist_ok=True)
        old_ts = working / "old.ts"
        fresh_ts = working / "fresh.ts"
        old_ts.write_bytes(b"x")
        fresh_ts.write_bytes(b"x")
        old_mtime = time.time() - 7 * 3600  # 7 hours old (> 6h threshold)
        os.utime(old_ts, (old_mtime, old_mtime))

        cleanup_recordings()
        assert not old_ts.exists()
        assert fresh_ts.exists()


class TestFinalizeDiscard:
    """Discarding an unsaved recording on session end."""

    def test_discard_removes_working_file(self, tmp_path: Path) -> None:
        """An unsaved session discards its working file.

        Tests:
            - finalize_session(save=False) returns False
            - The working .ts file is removed
        """
        from blinkapp.services.liveview_recording import (
            RecordingSession,
            finalize_session,
        )

        working = tmp_path / "rec.ts"
        working.write_bytes(b"data")
        session = RecordingSession(
            clip_id=ClipId.from_liveview("400658", 1718880000),
            camera_id="400658",
            camera_name="Front",
            started_at=datetime.now(UTC),
            working_path=working,
            save=False,
        )
        kept = finalize_session(session, save=False)
        assert kept is False
        assert not working.exists()


class TestFinalizeOnTeardown:
    """Recording sessions are finalized on every teardown path, not just stop."""

    def _register_session(self, camera_id: str, working: Path) -> None:
        """Register an unsaved recording session for a camera.

        Args:
            camera_id: Camera id to register the session under.
            working: Working .ts path that should be removed on discard.
        """
        from blinkapp.services import stream_service
        from blinkapp.services.liveview_recording import RecordingSession

        working.write_bytes(b"data")
        stream_service._recording_sessions[camera_id] = RecordingSession(
            clip_id=ClipId.from_liveview(camera_id, 1718880000),
            camera_id=camera_id,
            camera_name="Front",
            started_at=datetime.now(UTC),
            working_path=working,
            save=False,
        )

    def test_schedule_finalize_wait_pops_and_discards(self, tmp_path: Path) -> None:
        """Synchronous finalize pops the session and discards the working file.

        Tests:
            - _schedule_finalize(wait=True) removes the session from the registry
            - The unsaved working file is deleted
        """
        from blinkapp.services import stream_service

        working = tmp_path / "rec.ts"
        self._register_session("777", working)
        try:
            stream_service._schedule_finalize("777", wait=True)
            assert "777" not in stream_service._recording_sessions
            assert not working.exists()
        finally:
            stream_service._recording_sessions.pop("777", None)

    def test_shutdown_finalizes_registered_session(self, tmp_path: Path) -> None:
        """StreamManager.shutdown finalizes any in-progress recording session.

        Tests:
            - A session registered with no active stream is finalized on
              shutdown (removed from the registry; working file discarded)
        """
        from blinkapp.services import stream_service
        from blinkapp.services.hls_service import HLSStreamConfig
        from blinkapp.services.stream_service import StreamManager

        working = tmp_path / "rec.ts"
        self._register_session("778", working)
        try:
            manager = StreamManager(HLSStreamConfig())
            manager.shutdown()
            assert "778" not in stream_service._recording_sessions
            assert not working.exists()
        finally:
            stream_service._recording_sessions.pop("778", None)

    def test_failed_start_discards_even_when_save_enabled(self, tmp_path: Path) -> None:
        """A failed live-view start never keeps the recording, even if save=True.

        Tests:
            - _abort_failed_stream discards a save=True session (forces no-save)
            - The working file is removed and the session deregistered
        """
        from unittest.mock import Mock

        from blinkapp.models.ids import CameraId
        from blinkapp.services import stream_service
        from blinkapp.services.liveview_recording import RecordingSession

        working = tmp_path / "rec.ts"
        working.write_bytes(b"partial")
        stream_service._recording_sessions["779"] = RecordingSession(
            clip_id=ClipId.from_liveview("779", 1718880000),
            camera_id="779",
            camera_name="Front",
            started_at=datetime.now(UTC),
            working_path=working,
            save=True,  # "Save all Live Views" was enabled
        )
        try:
            stream_service._abort_failed_stream(Mock(), CameraId("779"), Mock())
            assert "779" not in stream_service._recording_sessions
            assert not working.exists()
        finally:
            stream_service._recording_sessions.pop("779", None)
