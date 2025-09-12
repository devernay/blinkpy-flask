#!/usr/bin/env python3
"""Script to carefully fix old constant patches in test files."""

import re
from pathlib import Path


def fix_patches_carefully(file_path: Path) -> None:
    """Fix old constant patches in a test file more carefully."""
    content = file_path.read_text()

    # Replace specific patch decorators
    content = re.sub(r'@patch\("blinkapp\.CACHE_DIR"[^)]*\)\s*\n', "", content)
    content = re.sub(r'@patch\("blinkapp\.CLIPS_CACHE_DIR"[^)]*\)\s*\n', "", content)
    content = re.sub(
        r'@patch\("blinkapp\.THUMBNAIL_CACHE_DIR"[^)]*\)\s*\n', "", content
    )
    content = re.sub(r'@patch\("blinkapp\.CREDENTIALS_FILE"[^)]*\)\s*\n', "", content)
    content = re.sub(r'@patch\("blinkapp\.SETTINGS_FILE"[^)]*\)\s*\n', "", content)

    # Replace inline patch calls - be more specific
    content = re.sub(
        r'patch\("blinkapp\.CACHE_DIR", "[^"]*"\)',
        'patch("blinkapp.services.cache_service.get_cache_dir", return_value=tmp_path)',
        content,
    )
    content = re.sub(
        r'patch\("blinkapp\.CLIPS_CACHE_DIR", "[^"]*"\)',
        'patch("blinkapp.services.cache_service.get_clips_cache_dir", return_value=tmp_path / "clips")',
        content,
    )
    content = re.sub(
        r'patch\("blinkapp\.THUMBNAIL_CACHE_DIR", "[^"]*"\)',
        'patch("blinkapp.services.cache_service.get_thumbnail_cache_dir", return_value=tmp_path / "thumbnails")',
        content,
    )
    content = re.sub(
        r'patch\("blinkapp\.CREDENTIALS_FILE", "[^"]*"\)',
        'patch("blinkapp.services.cache_service.get_credentials_file", return_value=tmp_path / "credentials.json")',
        content,
    )
    content = re.sub(
        r'patch\("blinkapp\.SETTINGS_FILE", "[^"]*"\)',
        'patch("blinkapp.services.cache_service.get_settings_file", return_value=tmp_path / "settings.json")',
        content,
    )

    # Replace direct references to constants
    content = re.sub(r"blinkapp\.CACHE_DIR", "str(tmp_path)", content)
    content = re.sub(r"blinkapp\.CLIPS_CACHE_DIR", 'str(tmp_path / "clips")', content)
    content = re.sub(
        r"blinkapp\.THUMBNAIL_CACHE_DIR", 'str(tmp_path / "thumbnails")', content
    )
    content = re.sub(
        r"blinkapp\.CREDENTIALS_FILE", 'str(tmp_path / "credentials.json")', content
    )
    content = re.sub(
        r"blinkapp\.SETTINGS_FILE", 'str(tmp_path / "settings.json")', content
    )

    file_path.write_text(content)
    print(f"Fixed patches in {file_path}")


if __name__ == "__main__":
    test_file = Path("tests/test_app.py")
    if test_file.exists():
        fix_patches_carefully(test_file)
        print("Done!")
    else:
        print("test_app.py not found")
