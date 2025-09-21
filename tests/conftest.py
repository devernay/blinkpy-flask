"""Pytest configuration for completely isolated testing."""

import os
from collections.abc import Generator
from pathlib import Path
from typing import Any, TextIO

import pytest


@pytest.fixture(autouse=True)
def enable_testing_mode() -> Generator[None, None, None]:
    """Enable testing mode to prevent external API calls."""
    from blinkapp.config import Config

    # Store original values
    original_testing = getattr(Config, "TESTING_MODE", False)

    # Enable testing mode
    Config.TESTING_MODE = True

    yield

    # Restore original values
    Config.TESTING_MODE = original_testing


@pytest.fixture(autouse=True)
def reset_global_state() -> Generator[None, None, None]:
    """Reset all global state between tests."""
    # Reset blink service globals
    import blinkapp.services.blink_service as blink_service

    blink_service._blink = None
    blink_service._blink_connection = None

    # Reset cache service globals
    import blinkapp.services.cache_service as cache_service

    cache_service.clips_cache = None
    cache_service.camera_thumbnail_cache = None
    cache_service._cache_paths = None

    # Reset stream service globals
    import blinkapp.services.stream_service as stream_service

    stream_service.stream_manager = None

    # Reset blinkapp path globals
    import blinkapp

    blinkapp._CACHE_DIR_PATH = None
    blinkapp._CLIPS_CACHE_DIR_PATH = None
    blinkapp._THUMBNAIL_CACHE_DIR_PATH = None
    blinkapp._HLS_OUTPUT_DIR_PATH = None
    blinkapp._CREDENTIALS_FILE_PATH = None
    blinkapp._SETTINGS_FILE_PATH = None

    yield

    # Clean up after test
    blink_service._blink = None
    blink_service._blink_connection = None
    cache_service.clips_cache = None
    cache_service.camera_thumbnail_cache = None
    cache_service._cache_paths = None
    stream_service.stream_manager = None
    blinkapp._CACHE_DIR_PATH = None
    blinkapp._CLIPS_CACHE_DIR_PATH = None
    blinkapp._THUMBNAIL_CACHE_DIR_PATH = None
    blinkapp._HLS_OUTPUT_DIR_PATH = None
    blinkapp._CREDENTIALS_FILE_PATH = None
    blinkapp._SETTINGS_FILE_PATH = None


@pytest.fixture(autouse=True, scope="session")
def enable_strict_patching_by_default() -> None:
    """Enable strict patching for all tests by default or via STRICT_PATCHING env var."""
    import os

    from tests.test_base import disable_strict_patching, enable_strict_patching

    # Check environment variable - enable if STRICT_PATCHING=1 or by default
    strict_patching_env = os.environ.get("STRICT_PATCHING", "1")

    if strict_patching_env == "1":
        enable_strict_patching()
    else:
        disable_strict_patching()


@pytest.fixture(autouse=True)
def mock_cache_paths_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Automatically mock all cache path accessor functions for every test."""
    # Mock all cache path accessor functions directly
    monkeypatch.setattr(
        "blinkapp.services.cache_service.get_cache_dir", lambda: tmp_path
    )
    monkeypatch.setattr(
        "blinkapp.services.cache_service.get_clips_cache_dir",
        lambda: tmp_path / "clips",
    )
    monkeypatch.setattr(
        "blinkapp.services.cache_service.get_thumbnail_cache_dir",
        lambda: tmp_path / "thumbnails",
    )
    monkeypatch.setattr(
        "blinkapp.services.hls_service.get_hls_output_dir", lambda: tmp_path / "hls"
    )
    monkeypatch.setattr(
        "blinkapp.services.auth_service.get_credentials_file_path",
        lambda: tmp_path / "blink.json",
    )
    monkeypatch.setattr(
        "blinkapp.services.settings_service.get_settings_file_path",
        lambda: tmp_path / "settings.json",
    )


@pytest.fixture(autouse=True)
def isolate_all_file_operations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Redirect ALL file operations away from source directory."""
    source_dir = Path().resolve()

    # Store originals
    original_open = open
    original_mkdir = os.mkdir
    original_makedirs = os.makedirs
    original_path_mkdir = Path.mkdir

    def safe_open(file: str | Path, mode: str = "r", **kwargs: Any) -> TextIO:
        file_path = Path(file).resolve()
        if file_path.is_relative_to(source_dir) and any(m in mode for m in "wax+"):
            # Redirect writes to tmp_path
            rel_path = file_path.relative_to(source_dir)
            new_path = tmp_path / rel_path
            new_path.parent.mkdir(parents=True, exist_ok=True)
            return original_open(new_path, mode, **kwargs)  # type: ignore[return-value]
        return original_open(file, mode, **kwargs)  # type: ignore[return-value]

    def safe_mkdir(path: str | Path, mode: int = 0o777) -> None:
        path_obj = Path(path).resolve()
        if path_obj.is_relative_to(source_dir):
            rel_path = path_obj.relative_to(source_dir)
            new_path = tmp_path / rel_path
            new_path.parent.mkdir(parents=True, exist_ok=True)
            return original_mkdir(new_path, mode)
        return original_mkdir(path, mode)

    def safe_makedirs(
        name: str | Path, mode: int = 0o777, exist_ok: bool = False
    ) -> None:
        path_obj = Path(name).resolve()
        if path_obj.is_relative_to(source_dir):
            rel_path = path_obj.relative_to(source_dir)
            new_path = tmp_path / rel_path
            new_path.mkdir(parents=True, exist_ok=True)
            return None
        return original_makedirs(name, mode, exist_ok)

    # Patch all file operations
    monkeypatch.setattr("builtins.open", safe_open)
    monkeypatch.setattr("os.mkdir", safe_mkdir)
    monkeypatch.setattr("os.makedirs", safe_makedirs)

    # Patch pathlib operations
    def safe_path_mkdir(
        self: Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False
    ) -> None:
        if self.resolve().is_relative_to(source_dir):
            rel_path = self.resolve().relative_to(source_dir)
            new_path = tmp_path / rel_path
            return original_path_mkdir(
                new_path, mode=mode, parents=parents, exist_ok=exist_ok
            )
        return original_path_mkdir(self, mode=mode, parents=parents, exist_ok=exist_ok)

    monkeypatch.setattr(Path, "mkdir", safe_path_mkdir)

    # Redirect cache operations
    def mock_initialize_cache_paths() -> None:
        """Mock cache path initialization by setting the private path variables."""
        import blinkapp

        blinkapp._CACHE_DIR_PATH = tmp_path
        blinkapp._THUMBNAIL_CACHE_DIR_PATH = tmp_path / "thumbnails"
        blinkapp._CLIPS_CACHE_DIR_PATH = tmp_path / "clips"
        blinkapp._HLS_OUTPUT_DIR_PATH = tmp_path / "hls"
        blinkapp._SETTINGS_FILE_PATH = tmp_path / "settings.json"
        blinkapp._CREDENTIALS_FILE_PATH = tmp_path / "blink.json"

    monkeypatch.setattr(
        "blinkapp.services.cache_service.initialize_cache_paths",
        mock_initialize_cache_paths,
    )
