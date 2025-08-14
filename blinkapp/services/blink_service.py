"""Blink service for Blink Camera Flask application.

This module handles all Blink-related business logic including
Blink API client management, connection management, and initialization.
"""

from __future__ import annotations

__all__ = [
    "initialize_blink_objects",
    "ensure_blink_initialized",
    "ensure_blink_connection_initialized",
]

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from blinkapp.services.connection_service import BlinkConnection

from blinkpy.blinkpy import Blink

logger = logging.getLogger(__name__)

# Global Blink instances
blink: Blink | None = None
blink_connection: BlinkConnection | None = None


def initialize_blink_objects() -> None:
    """Initialize the global Blink objects."""
    global blink_connection
    from blinkapp.config import Config
    from blinkapp.services.connection_service import BlinkConnection

    # Initialize async Blink connection manager for API operations
    blink_connection = BlinkConnection(timeout=Config.BLINK_CONNECTION_TIMEOUT)


def ensure_blink_initialized() -> Any:
    """Ensure blink is initialized.

    Returns:
        Initialized blink instance

    Raises:
        RuntimeError: If blink hasn't been initialized
    """
    if blink is None:
        raise RuntimeError("Blink not initialized. Call initialize_blink() first.")
    return blink


def ensure_blink_connection_initialized() -> Any:
    """Ensure blink_connection is initialized.

    Returns:
        Initialized blink_connection instance

    Raises:
        RuntimeError: If blink_connection hasn't been initialized
    """
    if blink_connection is None:
        raise RuntimeError(
            "Blink connection not initialized. Call initialize_blink() first."
        )
    return blink_connection
