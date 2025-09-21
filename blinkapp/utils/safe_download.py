"""Safe download utilities with automatic cleanup of partial downloads."""

import logging
import tempfile
from collections.abc import Callable
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
            logger.debug(f"Successfully downloaded to {target_path}")
            return True
        else:
            # Download failed, cleanup temp file
            if temp_path.exists():
                temp_path.unlink()
            return False

    except Exception as e:
        logger.error(f"Error during safe download to {target_path}: {e}")
        # Cleanup temp file on any exception
        if temp_file and Path(temp_file.name).exists():
            Path(temp_file.name).unlink()
        return False
