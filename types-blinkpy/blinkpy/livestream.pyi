# Stubs for blinkpy.livestream module
import asyncio
from typing import TYPE_CHECKING, Any
from urllib.parse import ParseResult

if TYPE_CHECKING:
    from .camera import BlinkCamera

class BlinkLiveStream:
    """Class to initialize individual stream."""

    # Core attributes from __init__
    camera: BlinkCamera
    command_id: str
    polling_interval: int
    target: ParseResult
    server: asyncio.Server | None
    clients: list[tuple[asyncio.StreamReader, asyncio.StreamWriter]]
    target_reader: asyncio.StreamReader | None
    target_writer: asyncio.StreamWriter | None

    def __init__(self, camera: BlinkCamera, response: dict[str, Any]) -> None: ...

    # Properties
    @property
    def socket(self) -> tuple[str, int] | None: ...
    @property
    def url(self) -> str: ...
    @property
    def is_serving(self) -> bool: ...

    # Async methods
    async def start(self, host: str = "127.0.0.1", port: int | None = None) -> None: ...
    async def feed(self) -> None: ...
    async def join(
        self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter
    ) -> None: ...
    async def recv(self) -> None: ...
    async def send(self) -> None: ...
    async def poll(self) -> None: ...

    # Sync methods
    def get_auth_header(self) -> bytearray: ...
    def stop(self) -> None: ...
