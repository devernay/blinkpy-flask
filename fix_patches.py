#!/usr/bin/env python3
"""Script to fix old constant patches in test files."""

import re
import sys
from pathlib import Path


def fix_patches(file_path: Path) -> None:
    """Fix old constant patches in a test file."""
    content = file_path.read_text()

    # Remove all old constant patches
    patterns_to_remove = [
        r'@patch\("blinkapp\.CACHE_DIR"[^)]*\)\s*\n',
        r'@patch\("blinkapp\.CLIPS_CACHE_DIR"[^)]*\)\s*\n',
        r'@patch\("blinkapp\.THUMBNAIL_CACHE_DIR"[^)]*\)\s*\n',
        r'@patch\("blinkapp\.CREDENTIALS_FILE"[^)]*\)\s*\n',
        r'@patch\("blinkapp\.SETTINGS_FILE"[^)]*\)\s*\n',
        r'patch\("blinkapp\.CACHE_DIR"[^)]*\)',
        r'patch\("blinkapp\.CLIPS_CACHE_DIR"[^)]*\)',
        r'patch\("blinkapp\.THUMBNAIL_CACHE_DIR"[^)]*\)',
        r'patch\("blinkapp\.CREDENTIALS_FILE"[^)]*\)',
        r'patch\("blinkapp\.SETTINGS_FILE"[^)]*\)',
    ]

    for pattern in patterns_to_remove:
        content = re.sub(pattern, "", content)

    # Remove nested with statements that are now empty
    # This is a simple approach - might need manual cleanup for complex cases
    content = re.sub(
        r"with patch\([^)]*\):\s*\n\s*with patch\([^)]*\):\s*\n\s*with patch\([^)]*\):\s*\n\s*with patch\([^)]*\):\s*\n\s*with patch\([^)]*\):\s*\n",
        "",
        content,
    )
    content = re.sub(
        r"with patch\([^)]*\):\s*\n\s*with patch\([^)]*\):\s*\n\s*with patch\([^)]*\):\s*\n\s*with patch\([^)]*\):\s*\n",
        "",
        content,
    )
    content = re.sub(
        r"with patch\([^)]*\):\s*\n\s*with patch\([^)]*\):\s*\n\s*with patch\([^)]*\):\s*\n",
        "",
        content,
    )
    content = re.sub(
        r"with patch\([^)]*\):\s*\n\s*with patch\([^)]*\):\s*\n", "", content
    )

    # Remove references to old constants in assertions and other code
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
        fix_patches(test_file)
        print("Done!")
    else:
        print("test_app.py not found")
        sys.exit(1)
