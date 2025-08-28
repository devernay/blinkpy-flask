#!/usr/bin/env python3
"""Script to fix Mock() usages by adding appropriate spec parameters and imports."""

import re
from pathlib import Path

# Mock patterns and their specs + required imports
MOCK_SPECS = {
    "mock_blink": ("Blink", "from blinkpy.blinkpy import Blink"),
    "self.mock_blink": ("Blink", "from blinkpy.blinkpy import Blink"),
    "mock_sync": (
        "BlinkSyncWireless",
        "from blinkpy.sync_wireless import BlinkSyncWireless",
    ),
    "mock_camera": ("BlinkCamera", "from blinkpy.camera import BlinkCamera"),
    "mock_response": ("Response", "from requests import Response"),
    "mock_connection": (
        "BlinkConnection",
        "from blinkapp.services.blink_connection import BlinkConnection",
    ),
    "mock_executor": (
        "ThreadPoolExecutor",
        "from concurrent.futures import ThreadPoolExecutor",
    ),
    "mock_executor_instance": (
        "ThreadPoolExecutor",
        "from concurrent.futures import ThreadPoolExecutor",
    ),
    "mock_future": ("Future", "from concurrent.futures import Future"),
    "mock_http_session": ("Session", "from requests import Session"),
    "mock_filepath": ("Path", "from pathlib import Path"),
    "mock_path": ("Path", "from pathlib import Path"),
    "mock_path_instance": ("Path", "from pathlib import Path"),
    "mock_item": (
        "LocalStorageMediaItem",
        "from blinkpy.local_storage import LocalStorageMediaItem",
    ),
}


def fix_mocks_in_file(filepath):
    """Fix Mock() usages in a single file."""
    with open(filepath) as f:
        content = f.read()

    changes_made = 0
    imports_to_add = set()

    # Fix each mock pattern - replace existing spec= with correct one
    for mock_name, (spec_type, import_stmt) in MOCK_SPECS.items():
        # Pattern: mock_name = Mock(spec=something)
        pattern = rf"({re.escape(mock_name)}\s*=\s*)Mock\(spec=[^)]+\)"
        replacement = rf"\1Mock(spec={spec_type})"

        new_content, count = re.subn(pattern, replacement, content)
        if count > 0:
            content = new_content
            changes_made += count
            imports_to_add.add(import_stmt)
            print(f"  Fixed {count} instances of {mock_name}")

    # Add missing imports at the top of the file
    if imports_to_add:
        lines = content.split("\n")

        # Find where to insert imports (after all existing imports and docstrings)
        insert_idx = 0
        in_multiline_import = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip docstrings and comments at the top
            if i < 10 and (
                stripped.startswith('"""')
                or stripped.startswith("'''")
                or stripped.startswith("#")
            ):
                insert_idx = i + 1
                continue

            # Handle multiline imports
            if "(" in line and ("import" in line or "from" in line):
                in_multiline_import = True
                insert_idx = i + 1
                continue
            elif in_multiline_import:
                insert_idx = i + 1
                if ")" in line:
                    in_multiline_import = False
                continue
            elif line.startswith("import ") or line.startswith("from "):
                insert_idx = i + 1
            elif stripped == "" and insert_idx > 0:
                continue
            elif insert_idx > 0 and stripped:
                break

        # Check which imports are already present
        existing_imports = set()
        for line in lines:
            if "import" in line:
                existing_imports.add(line.strip())

        # Add new imports
        new_imports = []
        for import_stmt in sorted(imports_to_add):
            if import_stmt not in existing_imports:
                new_imports.append(import_stmt)

        if new_imports:
            # Insert after the last import line
            lines[insert_idx:insert_idx] = new_imports + [""]
            content = "\n".join(lines)
            print(f"  Added {len(new_imports)} imports")

    # Write back if changes were made
    if changes_made > 0:
        with open(filepath, "w") as f:
            f.write(content)
        print(f"✅ Fixed {changes_made} mocks in {filepath}")
        return changes_made

    return 0


def main():
    """Fix all Mock() usages in test files."""
    test_dir = Path("./tests")
    total_fixes = 0

    for test_file in test_dir.glob("test_*.py"):
        print(f"\n🔍 Processing {test_file}")
        fixes = fix_mocks_in_file(test_file)
        total_fixes += fixes

    print(f"\n✅ Total fixes applied: {total_fixes}")


if __name__ == "__main__":
    main()
