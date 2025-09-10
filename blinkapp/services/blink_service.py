"""Blink service for Blink Camera Flask application.

This module handles all Blink-related business logic including
Blink API client management, connection management, and initialization.
"""

from __future__ import annotations

__all__ = [
    "initialize_blink_objects",
    "ensure_blink_initialized",
    "ensure_blink_connection_initialized",
    "initialize_blink_instance",
    "cleanup_blink_session",
    "get_blink_instance",
    "cleanup_blink_instances",
]

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blinkpy.auth import Auth

    from blinkapp.services.blink_connection import BlinkConnection

from blinkpy.blinkpy import Blink

logger = logging.getLogger(__name__)

# Private module-level instances
_blink: Blink | None = None
_blink_connection: BlinkConnection | None = None


async def cleanup_blink_session() -> None:
    """Clean up the Blink session and close aiohttp connections."""
    global _blink
    if _blink is not None and _blink.auth is not None:
        if _blink.auth.session is not None:
            session = _blink.auth.session
            if not session.closed:
                await session.close()
                logger.debug("Closed Blink aiohttp session")


def get_blink_instance() -> Blink | None:
    """Get the current blink instance, or None if not initialized.

    Returns:
        Blink | None: The global Blink instance if available, None otherwise.
    """
    return _blink


def cleanup_blink_instances() -> None:
    """Reset blink instances to None for cleanup/testing."""
    global _blink, _blink_connection
    _blink = None
    _blink_connection = None


def initialize_blink_instance(
    session_obj: Auth, blink_factory: type[Blink] | None = None
) -> Blink:
    """Create and set the global blink instance with the provided session.

    Args:
        session_obj: Session object for Blink authentication.
        blink_factory: Optional Blink class factory (defaults to Blink class).

    Returns:
        Blink: The newly created and initialized Blink instance.
    """
    global _blink
    if blink_factory is None:
        blink_factory = Blink
    _blink = blink_factory(session=session_obj)
    return _blink


def initialize_blink_objects() -> None:
    """Initialize the global Blink objects."""
    global _blink_connection
    from blinkapp.config import Config
    from blinkapp.services.blink_connection import BlinkConnection

    # Initialize async Blink connection manager for API operations
    _blink_connection = BlinkConnection(timeout=Config.BLINK_CONNECTION_TIMEOUT)


def ensure_blink_initialized() -> Blink:
    """Ensure blink is initialized.

    Returns:
        Initialized blink instance

    Raises:
        RuntimeError: If blink hasn't been initialized
    """
    if _blink is None:
        raise RuntimeError("Blink not initialized. Call initialize_blink() first.")
    return _blink


def ensure_blink_connection_initialized() -> BlinkConnection:
    """Ensure blink_connection is initialized and started.

    Returns:
        Initialized and started blink_connection instance

    Raises:
        RuntimeError: If blink_connection hasn't been initialized
    """
    if _blink_connection is None:
        raise RuntimeError(
            "Blink connection not initialized. Call initialize_blink() first."
        )

    # Ensure connection is started
    if not _blink_connection._started:
        _blink_connection.start()

    return _blink_connection
