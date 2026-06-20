"""Tests for live-view recording behavior."""

import json
from datetime import UTC, datetime
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
