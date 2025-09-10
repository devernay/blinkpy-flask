#!/usr/bin/env python3
"""Script to fix mock argument type annotations in test files."""

import re
from pathlib import Path


def fix_mock_args(content: str) -> str:
    """Fix mock argument type annotations."""
    # Pattern to match function definitions with mock arguments
    patterns = [
        (r"\bmock_([a-z_]+)\b(?=\s*[,)])", r"mock_\1: Mock"),
        (r"\bfunc\b(?=\s*[,)])", r"func: Callable[..., Any]"),
        (r"\bkey\b(?=\s*[,)])", r"key: str"),
        (r"\bself\b(?=\s*[,)])", r"self: Path"),
        (r"\boperation_id\b(?=\s*[,)])", r"operation_id: int"),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    return content


def fix_return_types(content: str) -> str:
    """Fix missing return type annotations for private functions."""
    # Common patterns for private functions
    patterns = [
        (r"def (execute_[a-z_]+)\([^)]*\):", r"def \1(...) -> Mock:"),
        (r"def (mock_[a-z_]+)\([^)]*\):", r"def \1(...) -> bool:"),
        (r"def (create_[a-z_]+)\([^)]*\):", r"def \1(...) -> tuple[Path, None]:"),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    return content


def process_file(file_path: Path) -> None:
    """Process a single file."""
    try:
        content = file_path.read_text()
        original_content = content

        content = fix_mock_args(content)
        content = fix_return_types(content)

        if content != original_content:
            file_path.write_text(content)
            print(f"Fixed: {file_path}")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")


def main() -> None:
    """Main function."""
    test_files = Path("tests").glob("*.py")
    for file_path in test_files:
        process_file(file_path)


if __name__ == "__main__":
    main()
