# Stubs for blinkpy.blinkpy module
from pathlib import Path
from typing import Any

from requests.structures import CaseInsensitiveDict

from .auth import Auth
from .camera import BlinkCamera
from .sync_module import BlinkSyncModule

class BlinkSetupError(Exception): ...

class Blink:
    """Main Blink class for interacting with Blink camera systems."""

    auth: Auth
    sync: CaseInsensitiveDict[str, BlinkSyncModule]
    cameras: CaseInsensitiveDict[str, BlinkCamera]
    video_list: CaseInsensitiveDict[str, Any]
    available: bool
    key_required: bool

    # Core attributes from __init__
    account_id: str | None
    client_id: str | None
    network_ids: list[str]
    urls: dict[str, str] | None
    last_refresh: float | None
    refresh_rate: int
    motion_interval: int
    networks: list[dict[str, Any]]
    version: str
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
    async def start(self) -> bool: ...
    async def setup_post_verify(self) -> bool: ...
    async def save(self, file_name: str | Path) -> None: ...
    async def refresh(self, force: bool = False, force_cache: bool = False) -> bool: ...
    async def setup_sync_module(
        self, name: str, network_id: str, cameras: dict[str, Any]
    ) -> None: ...
    async def get_homescreen(self) -> None: ...
    async def setup_owls(self) -> list[dict[str, dict[str, Any]]]: ...
    async def setup_lotus(self) -> list[dict[str, dict[str, Any]]]: ...
    async def setup_camera_list(self) -> dict[str, list[dict[str, Any]]]: ...
    async def setup_networks(self) -> None: ...
    async def setup_prompt_2fa(self) -> None: ...
    async def get_status(self) -> dict[str, Any]: ...
    async def set_status(self, data_dict: dict[str, Any] = {}) -> bool: ...
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
    async def do_http_get(self, address: str) -> dict[str, Any]: ...
    async def _parse_downloaded_items(
        self,
        result: dict[str, Any],
        camera: str,
        path: str | Path,
        delay: int,
        debug: bool,
    ) -> None: ...

    # Sync methods
    def setup_login_ids(self) -> None: ...
    def setup_urls(self) -> None: ...
    def setup_network_ids(self) -> dict[str, str]: ...
    def merge_cameras(self) -> CaseInsensitiveDict[str, BlinkCamera]: ...
    def check_if_ok_to_update(self) -> bool: ...

    # Properties
    @property
    def login_ids(self) -> dict[str, Any]: ...
    @property
    def account_id(self) -> str | None: ...
    @property
    def client_id(self) -> str | None: ...
    @property
    def network_ids(self) -> list[str]: ...
    @property
    def urls(self) -> dict[str, str] | None: ...
