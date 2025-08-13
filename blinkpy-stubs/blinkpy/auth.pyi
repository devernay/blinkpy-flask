# Stubs for blinkpy.auth module
from typing import Any

class Auth:
    """Authentication class for Blink API."""

    session: Any
    token: str | None
    host: str | None
    region_id: str | None
    client_id: str | None
    account_id: str | None
    data: dict[str, Any]

    def __init__(
        self,
        login_data: dict[str, str] | None = None,
        session: Any | None = None,
        host: str | None = None,
        token: str | None = None,
        no_prompt: bool = False,
    ) -> None: ...
    async def startup(self) -> bool: ...
    async def login(self, username: str, password: str) -> bool: ...
    async def send_auth_key(self, blink: Any, key: str) -> bool: ...
    async def validate_login(self) -> bool: ...
    async def refresh_token(self) -> bool: ...
    def prepare_request(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...
    async def query(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        is_retry: bool = False,
    ) -> dict[str, Any]: ...
    @property
    def check_key_required(self) -> bool: ...
    @property
    def key_required(self) -> bool: ...
