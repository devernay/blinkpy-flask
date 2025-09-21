"""Safe download utilities with atomic file operations."""

import logging
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


def safe_download(target_path: Path, download_func: Callable[[Path], bool]) -> bool:
    """Safely download to a temporary file, then move to target on success.

    This ensures partial downloads are automatically cleaned up if the process
    exits or the download fails.

    Args:
        target_path: Final destination path for the downloaded file
        download_func: Function that performs the actual download to temp file

    Returns:
        bool: True if download succeeded, False otherwise
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Create temporary file in same directory as target (for atomic move)
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=target_path.parent,
            prefix=f".{target_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

        # Perform download to temporary file
        success = download_func(temp_path)

        if success and temp_path.exists() and temp_path.stat().st_size > 0:
            # Atomic move to final location
            temp_path.replace(target_path)
            return True
        else:
            # Cleanup temp file on failure
            if temp_path.exists():
                temp_path.unlink()
            return False

    except Exception as e:
        logger.error(f"Error during safe download to {target_path}: {e}")
        # Cleanup temp file on exception
        if temp_file and Path(temp_file.name).exists():
            Path(temp_file.name).unlink()
        return False


def safe_download_bytes(target_path: Path, data: bytes) -> bool:
    """Safely write bytes to a file using atomic operations.

    Args:
        target_path: Final destination path for the file
        data: Bytes data to write

    Returns:
        bool: True if write succeeded, False otherwise
    """

    def write_bytes(temp_path: Path) -> bool:
        """Write bytes data to temporary path.

        Args:
            temp_path: Path to write bytes data to

        Returns:
            bool: Always returns True on successful write
        """
        temp_path.write_bytes(data)
        return True

    return safe_download(target_path, write_bytes)


async def safe_download_async(
    target_path: Path, download_func: Callable[[Path], Awaitable[bool]]
) -> tuple[Path | None, str]:
    """Safely download using async function with atomic operations.

    Args:
        target_path: Final destination path for the downloaded file
        download_func: Async function that performs the actual download

    Returns:
        tuple[Path | None, str]: (file_path, error_message)
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)

    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=target_path.parent,
            prefix=f".{target_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

        # Perform async download to temporary file
        success = await download_func(temp_path)

        if success and temp_path.exists() and temp_path.stat().st_size > 0:
            # Atomic move to final location
            temp_path.replace(target_path)
            return target_path, ""
        else:
            # Cleanup temp file on failure
            if temp_path.exists():
                temp_path.unlink()
            return None, "Download failed or resulted in empty file"

    except Exception as e:
        error_msg = f"Error during async safe download to {target_path}: {e}"
        logger.error(error_msg)
        # Cleanup temp file on exception
        if temp_file and Path(temp_file.name).exists():
            Path(temp_file.name).unlink()
        return None, error_msg
