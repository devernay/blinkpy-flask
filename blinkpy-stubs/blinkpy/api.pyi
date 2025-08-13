# Stubs for blinkpy.api module
from typing import Any

from aiohttp import ClientResponse

# Constants
MIN_THROTTLE_TIME: int
COMMAND_POLL_TIME: int
MAX_RETRY: int

# Authentication functions
async def request_login(
    auth: Any,
    url: str,
    login_data: dict[str, str],
    is_retry: bool = False,
) -> dict[str, Any]: ...
async def request_verify(
    auth: Any,
    blink: Any,
    verify_key: str,
) -> dict[str, Any]: ...

# Network and system functions
async def request_networks(blink: Any) -> dict[str, Any]: ...
async def request_homescreen(blink: Any) -> dict[str, Any]: ...
async def request_syncmodule(blink: Any, network_id: str) -> dict[str, Any]: ...
async def request_network_status(blink: Any, network_id: str) -> dict[str, Any]: ...

# Camera functions
async def request_cameras(blink: Any, network_id: str) -> dict[str, Any]: ...
async def request_camera_status(
    blink: Any, network_id: str, camera_id: str
) -> dict[str, Any]: ...
async def request_camera_sensors(
    blink: Any, network_id: str, camera_id: str
) -> dict[str, Any]: ...
async def request_new_image(blink: Any, network_id: str, camera_id: str) -> bool: ...
async def request_motion_detection_enable(
    blink: Any, network_id: str, camera_id: str
) -> bool: ...
async def request_motion_detection_disable(
    blink: Any, network_id: str, camera_id: str
) -> bool: ...

# Video and media functions
async def request_videos(
    blink: Any,
    time: int | None = None,
    page: int = 1,
) -> dict[str, Any]: ...
async def request_video_count(blink: Any) -> dict[str, Any]: ...

# Live view functions
async def request_get_liveview(
    blink: Any, network_id: str, camera_id: str
) -> dict[str, Any]: ...

# Local storage functions
async def request_local_storage_manifest(
    blink: Any, network_id: str, sync_id: str
) -> dict[str, Any]: ...
async def request_local_storage_clip(
    blink: Any,
    network_id: str,
    sync_id: str,
    manifest_id: str,
) -> dict[str, Any]: ...

# HTTP utility functions
async def http_get(
    blink: Any,
    url: str,
    stream: bool = False,
    json: bool = True,
    timeout: int = 10,
) -> ClientResponse | dict[str, Any]: ...
async def http_post(
    blink: Any,
    url: str,
    data: dict[str, Any] | None = None,
    json_data: bool = True,
    timeout: int = 10,
) -> dict[str, Any]: ...
