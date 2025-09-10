"""Pytest configuration for completely isolated testing."""

import os
from pathlib import Path
from typing import Any, TextIO

import pytest


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
def isolate_all_file_operations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect ALL file operations away from source directory."""
    source_dir = Path(".").resolve()

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
            return original_open(new_path, mode, **kwargs)
        return original_open(file, mode, **kwargs)

    def safe_mkdir(path: str | Path, mode: int = 0o777) -> None:
        path_obj = Path(path).resolve()
        if path_obj.is_relative_to(source_dir):
            rel_path = path_obj.relative_to(source_dir)
            new_path = tmp_path / rel_path
            new_path.parent.mkdir(parents=True, exist_ok=True)
            return original_mkdir(new_path, mode)
        return original_mkdir(path, mode)

    def safe_makedirs(name: str | Path, mode: int = 0o777, exist_ok: bool = False) -> None:
        path_obj = Path(name).resolve()
        if path_obj.is_relative_to(source_dir):
            rel_path = path_obj.relative_to(source_dir)
            new_path = tmp_path / rel_path
            new_path.mkdir(parents=True, exist_ok=True)
            return
        return original_makedirs(name, mode, exist_ok)

    # Patch all file operations
    monkeypatch.setattr("builtins.open", safe_open)
    monkeypatch.setattr("os.mkdir", safe_mkdir)
    monkeypatch.setattr("os.makedirs", safe_makedirs)

    # Patch pathlib operations
    def safe_path_mkdir(self: Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False) -> None:
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
        import blinkapp

        blinkapp.CACHE_DIR = str(tmp_path)
        blinkapp.THUMBNAIL_CACHE_DIR = str(tmp_path / "thumbnails")
        blinkapp.CLIPS_CACHE_DIR = str(tmp_path / "clips")
        blinkapp.HLS_OUTPUT_DIR = str(tmp_path / "hls")
        blinkapp.SETTINGS_FILE = str(tmp_path / "settings.json")
        blinkapp.CREDENTIALS_FILE = str(tmp_path / "blink.json")

    monkeypatch.setattr(
        "blinkapp.services.cache_service.initialize_cache_paths",
        mock_initialize_cache_paths,
    )
