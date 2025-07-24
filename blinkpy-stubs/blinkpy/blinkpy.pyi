# Stubs for blinkpy.blinkpy module
from pathlib import Path
from typing import Any

from .auth import Auth
from .camera import BlinkCamera
from .sync_module import BlinkSyncModule

class Blink:
    """Main Blink class for interacting with Blink camera systems."""

    auth: Auth
    sync: dict[str, BlinkSyncModule]
    cameras: dict[str, BlinkCamera]
    available: bool
    key_required: bool

    # Additional attributes found in usage
    account_id: str | None
    client_id: str | None
    last_refresh: int | None
    refresh_rate: int
    motion_interval: int
    network_ids: list[int]
    version: str
    homescreen: dict[str, Any]

    def __init__(
        self,
        session: Any | None = None,
        no_owls: bool = False,
        no_prompt: bool = False,
    ) -> None: ...
    async def start(self) -> bool: ...
    async def setup_post_verify(self) -> None: ...
    async def save(self, file_path: str | Path) -> bool: ...
    async def refresh(self, force: bool = False, force_cache: bool = False) -> bool: ...
    def get_videos_metadata(
        self,
        since: int | None = None,
        camera: str = "all",
        stop: int = 10,
    ) -> dict[str, Any]: ...
    def setup_camera_list(self) -> None: ...
    def setup_sync_module(
        self, name: str, network_id: int, cameras: dict[str, Any]
    ) -> None: ...
    def merge_cameras(self) -> None: ...
    def get_homescreen(self) -> dict[str, Any]: ...
    def get_status(self) -> dict[str, Any]: ...
    def set_status(self, data_dict: dict[str, Any] = {}) -> bool: ...
    def check_if_ok_to_update(self) -> bool: ...
    def do_http_get(self, address: str) -> dict[str, Any]: ...

    # Properties that might be accessed
    @property
    def networks(self) -> dict[str, Any]: ...
    @property
    def login_ids(self) -> dict[str, Any]: ...
