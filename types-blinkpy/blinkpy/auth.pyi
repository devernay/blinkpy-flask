# Stubs for blinkpy.auth module
from typing import TYPE_CHECKING, Any

from aiohttp import ClientResponse, ClientSession

if TYPE_CHECKING:
    from .blinkpy import Blink

class LoginError(Exception): ...
class TokenRefreshFailed(Exception): ...
class BlinkBadResponse(Exception): ...
class UnauthorizedError(Exception): ...

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
        login_data: dict[str, Any] | None = None,
        no_prompt: bool = False,
        session: ClientSession | None = None,
        agent: str = "27.0ANDROID_28373244",
        app_build: str = "ANDROID_28373244",
    ) -> None: ...

    # Properties
    @property
    def login_attributes(self) -> dict[str, Any]: ...
    @property
    def header(self) -> dict[str, str]: ...
    @property
    def check_key_required(self) -> bool: ...

    # Sync methods
    def validate_login(self) -> bool: ...
    def logout(self, blink: Blink) -> None: ...
    def extract_login_info(self) -> None: ...

    # Async methods
    async def login(self, login_url: str = ...) -> dict[str, Any]: ...
    async def refresh_token(self) -> bool: ...
    async def startup(self) -> bool: ...
    async def validate_response(
        self, response: ClientResponse, json_resp: bool
    ) -> dict[str, Any] | ClientResponse: ...
    async def query(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        reqtype: str = "get",
        stream: bool = False,
        json_resp: bool = True,
        is_retry: bool = False,
        timeout: int = 30,
    ) -> dict[str, Any] | ClientResponse | None: ...
    async def send_auth_key(self, blink: Blink, key: str) -> bool: ...
