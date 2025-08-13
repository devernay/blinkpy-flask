# Stubs for blinkpy.sync_module module
from typing import TYPE_CHECKING, Any

from requests.structures import CaseInsensitiveDict

if TYPE_CHECKING:
    from .blinkpy import Blink
    from .camera import BlinkCamera
else:
    from .camera import BlinkCamera

class BlinkSyncModule:
    """Sync module class for Blink systems."""

    # Core attributes from __init__
    blink: Blink  # Blink instance
    network_id: str
    name: str
    response: dict[str, Any]
    cameras: CaseInsensitiveDict[str, BlinkCamera]
    local_storage: dict[str, Any]
    sync_id: int | None
    local_storage_manifest_ready: bool
    _local_storage: dict[str, Any]
    attributes: dict[str, Any]
    network_info: dict[str, Any]
    summary: dict[str, Any]
    region_id: str | None
    serial: str | None
    status: str
    host: str | None
    events: list[dict[str, Any]]
    motion_interval: int
    motion: dict[str, Any]
    last_records: dict[str, list[dict[str, Any]]]
    _version: str | None

    def __init__(
        self,
        blink: Blink,
        network_name: str,
        network_id: int,
        camera_list: dict[str, Any],
    ) -> None: ...

    # Async methods
    async def start(self) -> None: ...
    async def async_arm(self, value: bool) -> bool: ...
    async def sync_initialize(self) -> None: ...
    async def _init_local_storage(self, sync_id: str) -> None: ...
    async def update_cameras(
        self, camera_type: type[BlinkCamera] = BlinkCamera
    ) -> None: ...
    async def get_events(self, **kwargs: Any) -> dict[str, Any]: ...
    async def get_camera_info(
        self, camera_id: str, **kwargs: Any
    ) -> dict[str, Any]: ...
    async def get_network_info(self) -> dict[str, Any]: ...
    async def refresh(self, force_cache: bool = False) -> bool: ...
    async def check_new_videos(self) -> None: ...
    async def get_owl_info(self) -> dict[str, Any]: ...
    async def update_local_storage_manifest(self) -> bool: ...
    async def prepare_download(self, item_id: int) -> bool: ...
    async def download_video(self, item_id: int, filename: str) -> bool: ...

    # Sync methods
    def get_unique_info(self, name: str) -> dict[str, Any]: ...
    def check_new_video_time(
        self, timestamp: int, reference: int | None = None
    ) -> bool: ...
    def get_videos_metadata(
        self,
        since: int | None = None,
        stop: int = 10,
    ) -> dict[str, Any]: ...

    # Properties
    @property
    def attributes(self) -> dict[str, Any]: ...
    @property
    def urls(self) -> dict[str, str]: ...
    @property
    def version(self) -> str: ...
    @property
    def arm(self) -> bool: ...
    @property
    def online(self) -> bool: ...
    @property
    def wifi_strength(self) -> int: ...
    @property
    def temperature(self) -> float | None: ...
    @property
    def battery(self) -> str | None: ...
    @property
    def local_storage(self) -> dict[str, Any]: ...
    @property
    def local_storage_manifest_ready(self) -> bool: ...
    @property
    def network_id(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def status(self) -> str: ...
    @property
    def serial(self) -> str: ...
    @property
    def host(self) -> str: ...
    @property
    def last_record(self) -> dict[str, Any]: ...

class BlinkOwl(BlinkSyncModule):
    """Blink Owl (Mini) sync module class."""

    pass

class BlinkLotus(BlinkSyncModule):
    """Blink Lotus sync module class."""

    pass
