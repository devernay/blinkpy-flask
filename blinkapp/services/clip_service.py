"""Clip service for Blink Camera Flask application.

This module handles all clip-related business logic including
cloud and local clip processing, downloading, and thumbnail generation.
"""

from __future__ import annotations

__all__ = [
    "process_cloud_clips",
    "process_local_clips",
    "download_cloud_clip",
    "download_local_clip",
    "process_cloud_clip_background",
]

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from blinkapp.models.ids import ClipId

logger = logging.getLogger(__name__)


def process_cloud_clips(page: int = 1, since: int = 0) -> dict[str, Any]:
    """Process cloud clips with pagination and filtering.

    Args:
        page: Page number for pagination
        since: Timestamp filter for clips

    Returns:
        Dictionary with processed clips data
    """
    from blinkapp import process_cloud_clips as _process_cloud_clips

    return _process_cloud_clips(page, since)


def process_local_clips() -> list[dict[str, Any]]:
    """Process local clips from USB storage.

    Returns:
        List of processed local clips
    """
    from blinkapp import process_local_clips as _process_local_clips

    return _process_local_clips()


def download_cloud_clip(clip_id: ClipId):
    """Download a cloud clip.

    Args:
        clip_id: The clip ID to download

    Returns:
        Flask response with clip file or error
    """
    from blinkapp import download_cloud_clip as _download_cloud_clip

    return _download_cloud_clip(clip_id)


def download_local_clip(clip_id: ClipId):
    """Download a local clip.

    Args:
        clip_id: The clip ID to download

    Returns:
        Flask response with clip file or error
    """
    from blinkapp import download_local_clip as _download_local_clip

    return _download_local_clip(clip_id)


def process_cloud_clip_background(clip_id: ClipId) -> None:
    """Process cloud clip in background.

    Args:
        clip_id: The clip ID to process
    """
    from blinkapp import process_cloud_clip_background as _process_cloud_clip_background

    _process_cloud_clip_background(clip_id)


def process_local_clip_background(clip_id: ClipId) -> None:
    """Process local clip in background.

    Args:
        clip_id: The clip ID to process
    """
    from blinkapp import process_local_clip_background as _process_local_clip_background

    _process_local_clip_background(clip_id)
