# Stubs for blinkpy.livestream module
import asyncio
import urllib.parse
from collections.abc import AsyncGenerator
from typing import Any

class BlinkLiveStream:
    """Class to initialize individual stream."""

    # Core attributes from __init__
    camera: Any  # BlinkCamera
    command_id: str
    polling_interval: int
    target: urllib.parse.ParseResult
    server: Any | None
    clients: list[Any]
    target_reader: asyncio.StreamReader | None
    target_writer: asyncio.StreamWriter | None

    def __init__(self, camera: Any, response: dict[str, Any]) -> None: ...

    # Methods
    def get_auth_header(self) -> bytearray: ...
    async def start_server(
        self, host: str = "127.0.0.1", port: int = 0
    ) -> tuple[str, int]: ...
    async def stop_server(self) -> None: ...
    async def connect_to_target(self) -> bool: ...
    async def disconnect_from_target(self) -> None: ...
    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None: ...
    async def relay_data(self) -> None: ...

    # Stream-related methods for compatibility
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def feed(self) -> AsyncGenerator[bytes, None]: ...
    @property
    def is_stream_active(self) -> bool: ...
