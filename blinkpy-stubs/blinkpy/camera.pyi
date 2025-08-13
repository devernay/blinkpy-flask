# Stubs for blinkpy.camera module
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aiohttp import ClientResponse

if TYPE_CHECKING:
    from .livestream import BlinkLiveStream
    from .sync_module import BlinkSyncModule

class BlinkCamera:
    """Camera class for individual Blink cameras."""

    # Core attributes from __init__
    sync: BlinkSyncModule  # BlinkSyncModule
    network_id: str
    camera_id: str
    name: str
    response: dict[str, Any]
    motion_detected: bool
    arm: bool
    name: str | None
    camera_id: str | None
    network_id: str | None
    thumbnail: str | None
    serial: str | None
    motion_enabled: bool | None
    battery_level: int | None
    clip: str | None
    recent_clips: list[dict[str, Any]]
    temperature: float | None
    temperature_calibrated: float | None
    battery_state: str | None
    motion_detected: bool | None
    wifi_strength: int | None
    last_record: dict[str, Any] | None
    camera_type: str
    product_type: str | None
    sync_signal_strength: int | None

    # Private attributes
    _version: str | None
    _battery_voltage: float | None
    _cached_image: bytes | None
    _cached_video: bytes | None

    def __init__(self, sync: BlinkSyncModule) -> None: ...

    # Async methods
    async def async_arm(self, value: bool) -> bool: ...
    async def snap_picture(self) -> bool: ...
    async def get_sensor_info(self) -> dict[str, Any]: ...
    async def get_liveview(self) -> dict[str, Any]: ...
    async def init_livestream(self) -> BlinkLiveStream | None: ...
    async def refresh(self) -> None: ...
    async def get_media(self, media_type: str = "image") -> ClientResponse | None: ...
    async def get_thumbnail(self, url: str | None = None) -> ClientResponse | None: ...
    async def get_video_clip(self, url: str | None = None) -> bytes | None: ...
    async def set_motion_detect(self, enable: bool) -> bool: ...
    @property
    async def night_vision(self) -> dict[str, Any] | None: ...
    async def async_set_night_vision(self, value: str) -> dict[str, Any] | None: ...
    async def record(self) -> bool: ...
    async def update(
        self,
        config: dict[str, Any],
        force_cache: bool = False,
        expire_clips: bool = True,
        **kwargs: Any,
    ) -> None: ...
    async def update_images(
        self,
        config: dict[str, Any],
        force_cache: bool = False,
        expire_clips: bool = True,
    ) -> None: ...
    async def save_recent_clips(
        self, output_dir: str | Path, since: int | None = None
    ) -> list[dict[str, Any]]: ...

    # Sync methods
    def get_videos_metadata(
        self,
        since: int | None = None,
        stop: int = 10,
    ) -> dict[str, Any]: ...
    def extract_config_info(self, config: dict[str, Any]) -> None: ...

    # Properties
    @property
    def attributes(self) -> dict[str, Any]: ...
    @property
    def network_id(self) -> str: ...
    @property
    def camera_id(self) -> str: ...
    @property
    def product_type(self) -> str: ...
    @property
    def arm(self) -> bool: ...
    @property
    def battery(self) -> str | None: ...
    @property
    def thumbnail(self) -> str | None: ...
    @property
    def clip(self) -> str | None: ...
    @property
    def temperature(self) -> int | None: ...
    @property
    def wifi_strength(self) -> int: ...
    @property
    def motion_detected(self) -> bool: ...
    @property
    def name(self) -> str: ...
    @property
    def serial(self) -> str: ...
    @property
    def enabled(self) -> bool: ...
    @property
    def privacy_mode(self) -> bool: ...
    @property
    def battery_voltage(self) -> float | None: ...
    @property
    def temperature_c(self) -> float | None: ...
    @property
    def video_from_cache(self) -> bytes | None: ...
    @property
    def image_from_cache(self) -> bytes | None: ...
    @property
    def status(self) -> str: ...
    @property
    def version(self) -> str: ...
    @property
    def online(self) -> bool: ...

    # Stream-related methods (for compatibility)
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def feed(self) -> AsyncGenerator[bytes, None]: ...
    @property
    def is_stream_active(self) -> bool: ...

class BlinkCameraMini(BlinkCamera):
    """Blink Mini camera class."""

    pass

class BlinkDoorbell(BlinkCamera):
    """Blink Doorbell camera class."""

    pass
