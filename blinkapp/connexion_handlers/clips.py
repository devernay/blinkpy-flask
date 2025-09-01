"""Connexion-compatible clips management handlers."""

from ..config import Config
from ..models.types import ClipsResponse, JsonDict


def get_clips(
    storage: str | None = None,
) -> ClipsResponse | tuple[JsonDict, int]:
    """Get clips from cloud or local storage.

    Args:
        storage: Storage type ('cloud' or 'local'), defaults to 'cloud'

    Returns:
        Clips list dictionary
    """
    from ..services.blink_service import blink, blink_connection
    from ..services.clip_service import process_cloud_clips, process_local_clips
    from ..utils.decorators import error_context

    if storage is None:
        storage = "cloud"

    if storage not in ["cloud", "local"]:
        return {
            "success": False,
            "error": "Invalid storage type. Must be 'cloud' or 'local'",
        }, 400

    assert blink is not None

    with error_context(f"get {storage} clips"):
        if storage == "cloud":
            # Get cloud clips via blink operation
            if blink_connection:
                videos_metadata = blink_connection.execute(
                    blink.get_videos_metadata(stop=Config.CLIPS_PER_STORAGE_TYPE)
                )
            else:
                videos_metadata = []
            return {"clips": process_cloud_clips(videos_metadata)}
        else:
            # Get local clips from sync modules
            return {"clips": process_local_clips()}
