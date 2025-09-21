"""Network guard to prevent external connections during testing."""

from typing import Any, Never
from unittest.mock import patch


class NetworkGuard:
    """Prevents network connections in testing mode."""

    def __init__(self) -> None:
        """Initialize the network guard."""
        self._patches: list[Any] = []
        self._active = False

    def __enter__(self) -> "NetworkGuard":
        """Enable network blocking."""
        from blinkapp.config import Config

        if Config.TESTING_MODE:
            self._active = True

            def blocked_socket(*args: Any, **kwargs: Any) -> Never:
                """Block socket connections in testing mode.

                Raises:
                    RuntimeError: Always raised to prevent socket connections
                """
                raise RuntimeError(
                    "Network connections blocked in testing mode. "
                    + "Tests must properly mock network calls."
                )

            def blocked_aiohttp_request(*args: Any, **kwargs: Any) -> Never:
                """Block aiohttp requests in testing mode.

                Raises:
                    RuntimeError: Always raised to prevent HTTP requests
                """
                raise RuntimeError(
                    "HTTP requests blocked in testing mode. "
                    + "Tests must properly mock aiohttp calls."
                )

            # Block socket connections
            socket_patch = patch("socket.socket", side_effect=blocked_socket)
            self._patches.append(socket_patch)
            socket_patch.start()

            # Block aiohttp requests
            aiohttp_patch = patch(
                "aiohttp.ClientSession", side_effect=blocked_aiohttp_request
            )
            self._patches.append(aiohttp_patch)
            aiohttp_patch.start()

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Restore network access."""
        if self._active:
            for patch_obj in self._patches:
                patch_obj.stop()
            self._patches.clear()
            self._active = False
