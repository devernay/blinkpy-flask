# Stubs for blinkpy.api module
from typing import TYPE_CHECKING, Any

from aiohttp import ClientResponse

if TYPE_CHECKING:
    from .blinkpy import Blink

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
    blink: Blink,
    verify_key: str,
) -> dict[str, Any]: ...
async def request_logout(blink: Blink) -> dict[str, Any]: ...

# Network and system functions
async def request_networks(blink: Blink) -> dict[str, Any]: ...
async def request_network_update(blink: Blink, network: str) -> dict[str, Any]: ...
async def request_user(blink: Blink) -> dict[str, Any]: ...
async def request_homescreen(blink: Blink, **kwargs: Any) -> dict[str, Any]: ...
async def request_syncmodule(blink: Blink, network_id: str) -> dict[str, Any]: ...
async def request_network_status(blink: Blink, network_id: str) -> dict[str, Any]: ...
async def request_system_arm(
    blink: Blink, network: str, **kwargs: Any
) -> dict[str, Any]: ...
async def request_system_disarm(
    blink: Blink, network: str, **kwargs: Any
) -> dict[str, Any]: ...
async def request_notification_flags(blink: Blink, **kwargs: Any) -> dict[str, Any]: ...
async def request_set_notification_flag(
    blink: Blink, data_dict: dict[str, Any]
) -> dict[str, Any]: ...
async def request_command_status(
    blink: Blink, network: str, command_id: str
) -> dict[str, Any]: ...
async def request_command_done(
    blink: Blink, network: str, command_id: str
) -> dict[str, Any]: ...

# Camera functions
async def request_new_image(
    blink: Blink, network_id: str, camera_id: str, **kwargs: Any
) -> bool: ...
async def request_new_video(
    blink: Blink, network_id: str, camera_id: str, **kwargs: Any
) -> bool: ...
async def request_cameras(blink: Blink, network_id: str) -> dict[str, Any]: ...
async def request_camera_info(
    blink: Blink, network_id: str, camera_id: str
) -> dict[str, Any]: ...
async def request_camera_usage(blink: Blink) -> dict[str, Any]: ...
async def request_camera_liveview(
    blink: Blink, network_id: str, camera_id: str
) -> dict[str, Any]: ...
async def request_camera_sensors(
    blink: Blink, network_id: str, camera_id: str
) -> dict[str, Any]: ...
async def request_motion_detection_enable(
    blink: Blink, network_id: str, camera_id: str, **kwargs: Any
) -> bool: ...
async def request_motion_detection_disable(
    blink: Blink, network_id: str, camera_id: str, **kwargs: Any
) -> bool: ...
async def request_get_config(
    blink: Blink, network_id: str, camera_id: str, product_type: str = "owl"
) -> dict[str, Any]: ...
async def request_update_config(
    blink: Blink,
    network_id: str,
    camera_id: str,
    product_type: str = "owl",
    data: str | None = None,
) -> ClientResponse | None: ...

# Video and media functions
async def request_videos(
    blink: Blink,
    time: int | None = None,
    page: int = 1,
) -> dict[str, Any]: ...
async def request_video_count(blink: Blink) -> dict[str, Any]: ...

# Live view functions
async def request_get_liveview(
    blink: Blink, network_id: str, camera_id: str
) -> dict[str, Any]: ...

# Local storage functions
async def request_local_storage_manifest(
    blink: Blink, network_id: str, sync_id: str
) -> dict[str, Any]: ...
async def request_local_storage_clip(
    blink: Blink,
    network_id: str,
    sync_id: str,
    manifest_id: str,
) -> dict[str, Any]: ...

# HTTP utility functions
async def http_get(
    blink: Blink,
    url: str,
    stream: bool = False,
    json: bool = True,
    timeout: int = 10,
) -> ClientResponse | dict[str, Any]: ...
async def http_post(
    blink: Blink,
    url: str,
    data: dict[str, Any] | None = None,
    json_data: bool = True,
    timeout: int = 10,
) -> dict[str, Any]: ...
