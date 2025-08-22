"""File system operations with dependency injection for better testability."""

from collections.abc import Callable
from pathlib import Path

__all__ = [
    "write_file_safely",
    "read_file_safely",
    "check_file_exists",
    "create_directory_safely",
]


def write_file_safely(
    filepath: Path, content: bytes, writer: Callable[[Path, bytes], None] | None = None
) -> bool:
    """Write file with injectable writer for testing."""
    if writer is None:

        def default_writer(p: Path, c: bytes) -> None:
            p.write_bytes(c)

        writer = default_writer

    try:
        writer(filepath, content)
        return True
    except OSError:
        return False


def read_file_safely(
    filepath: Path, reader: Callable[[Path], bytes] | None = None
) -> bytes | None:
    """Read file with injectable reader for testing."""
    if reader is None:

        def default_reader(p: Path) -> bytes:
            return p.read_bytes()

        reader = default_reader

    try:
        return reader(filepath)
    except OSError:
        return None


def check_file_exists(
    filepath: Path, checker: Callable[[Path], bool] | None = None
) -> bool:
    """Check if file exists with injectable checker for testing."""
    if checker is None:

        def default_checker(p: Path) -> bool:
            return p.exists()

        checker = default_checker

    return checker(filepath)


def create_directory_safely(
    dirpath: Path, creator: Callable[[Path], None] | None = None
) -> bool:
    """Create directory with injectable creator for testing."""
    if creator is None:

        def default_creator(p: Path) -> None:
            p.mkdir(parents=True, exist_ok=True)

        creator = default_creator

    try:
        creator(dirpath)
        return True
    except OSError:
        return False
