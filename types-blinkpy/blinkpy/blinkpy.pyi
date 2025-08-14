# Stubs for blinkpy.blinkpy module
from pathlib import Path
from typing import Any, TypeVar

from aiohttp import ClientResponse
from requests.structures import CaseInsensitiveDict

from .auth import Auth
from .camera import BlinkCamera
from .sync_module import BlinkSyncModule

_T = TypeVar("_T")

# Custom type alias for properly typed CaseInsensitiveDict
class SyncDict(dict[str, BlinkSyncModule]): ...
class BlinkSetupError(Exception): ...

class Blink:
    """Main Blink class for interacting with Blink camera systems."""

    # Core attributes from __init__
    auth: Auth
    account_id: str | None
    client_id: str | None
    network_ids: list[str]
    urls: dict[str, str] | None
    sync: SyncDict
    last_refresh: float | None
    refresh_rate: int
    networks: list[dict[str, Any]]
    cameras: CaseInsensitiveDict[str, BlinkCamera]
    video_list: CaseInsensitiveDict[str, Any]
    motion_interval: int
    version: str
    available: bool
    key_required: bool
    homescreen: dict[str, Any]
    no_owls: bool

    def __init__(
        self,
        refresh_rate: int = 30,
        motion_interval: int = 1,
        no_owls: bool = False,
        session: Any | None = None,
    ) -> None: ...

    # Async methods
    async def refresh(self, force: bool = False, force_cache: bool = False) -> bool: ...
    async def start(self) -> bool: ...
    async def setup_prompt_2fa(self) -> bool: ...
    async def setup_post_verify(self) -> bool: ...
    async def setup_sync_module(
        self, name: str, network_id: str, cameras: dict[str, Any]
    ) -> None: ...
    async def get_homescreen(self) -> None: ...
    async def setup_owls(self) -> list[dict[str, dict[str, Any]]]: ...
    async def setup_lotus(self) -> list[dict[str, dict[str, Any]]]: ...
    async def setup_camera_list(self) -> dict[str, list[dict[str, Any]]]: ...
    async def setup_networks(self) -> None: ...
    async def save(self, file_name: str | Path) -> None: ...
    async def get_status(self) -> dict[str, Any] | ClientResponse | None: ...
    async def set_status(
        self, data_dict: dict[str, Any] = {}
    ) -> dict[str, Any] | ClientResponse | None: ...
    async def download_videos(
        self,
        path: str | Path,
        since: int | None = None,
        camera: str = "all",
        stop: int = 10,
        delay: int = 1,
        debug: bool = False,
    ) -> None: ...
    async def get_videos_metadata(
        self,
        since: int | None = None,
        camera: str = "all",
        stop: int = 10,
    ) -> list[dict[str, Any]]: ...
    async def do_http_get(self, address: str) -> ClientResponse: ...
    async def _parse_downloaded_items(
        self,
        result: list[dict[str, Any]],
        camera: str,
        path: str | Path,
        delay: int,
        debug: bool,
    ) -> None: ...

    # Sync methods
    def setup_login_ids(self) -> None: ...
    def setup_urls(self) -> None: ...
    def setup_network_ids(self) -> dict[str, str]: ...
    def check_if_ok_to_update(self) -> bool: ...
    def merge_cameras(self) -> CaseInsensitiveDict[str, BlinkCamera]: ...
