# Stubs for blinkpy.auth module
from typing import Any

from aiohttp import ClientSession

class LoginError(Exception): ...
class TokenRefreshFailed(Exception): ...

class Auth:
    """Authentication class for Blink API."""

    # Core attributes from __init__
    data: dict[str, Any]
    token: str | None
    host: str | None
    region_id: str | None
    client_id: str | None
    account_id: str | None
    user_id: str | None
    login_response: dict[str, Any] | None
    is_errored: bool
    no_prompt: bool
    session: ClientSession

    # Private attributes
    _agent: str
    _app_build: str

    def __init__(
        self,
        login_data: dict[str, str] | None = None,
        no_prompt: bool = False,
        session: ClientSession | None = None,
        agent: str = "27.0ANDROID_28373244",
        app_build: str = "ANDROID_28373244",
    ) -> None: ...

    # Async methods
    async def startup(self) -> bool: ...
    async def login(self, username: str, password: str) -> bool: ...
    async def send_auth_key(self, blink: Any, key: str) -> bool: ...
    async def validate_login(self) -> bool: ...
    async def refresh_token(self) -> bool: ...
    async def query(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        is_retry: bool = False,
    ) -> dict[str, Any]: ...

    # Sync methods
    def prepare_request(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    # Properties
    @property
    def login_attributes(self) -> dict[str, Any]: ...
    @property
    def check_key_required(self) -> bool: ...
    @property
    def key_required(self) -> bool: ...
