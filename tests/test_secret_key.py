"""Tests for persistent SECRET_KEY resolution."""

import unittest
from unittest.mock import patch

import pytest


class TestSecretKeyResolution(unittest.TestCase):
    """SECRET_KEY resolution: env override, keychain, and file fallback."""

    def test_env_override_wins(self) -> None:
        """An explicit SECRET_KEY environment variable is used as-is.

        Tests:
            - _resolve_secret_key returns the SECRET_KEY env value unchanged
        """
        import blinkapp

        with patch.dict("os.environ", {"SECRET_KEY": "fixed-env-key"}):
            self.assertEqual(blinkapp._resolve_secret_key(), "fixed-env-key")

    def test_keychain_roundtrip_is_stable(self) -> None:
        """The keychain-backed key is generated once and reused on next load.

        Tests:
            - First load stores a 64-hex-char key via keyring
            - A subsequent load returns the same key (stable across restarts)
        """
        import keyring

        import blinkapp

        store: dict[tuple[str, str], str] = {}
        with (
            patch.object(keyring, "get_password", lambda s, k: store.get((s, k))),
            patch.object(
                keyring,
                "set_password",
                lambda s, k, v: store.__setitem__((s, k), v),
            ),
        ):
            first = blinkapp._load_or_create_persistent_secret_key()
            second = blinkapp._load_or_create_persistent_secret_key()
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_file_fallback_when_keychain_unavailable(self) -> None:
        """When the keychain is unavailable, a stable key file is used.

        Tests:
            - keyring failure falls back to a key file
            - The key file persists the same key across loads
        """
        import keyring

        import blinkapp

        def _raise(*_args: object, **_kwargs: object) -> str:
            raise RuntimeError("no keychain backend")

        with pytest.MonkeyPatch.context() as mp:
            import tempfile
            from pathlib import Path

            keyfile = Path(tempfile.mkdtemp()) / ".secret_key"
            mp.setattr(keyring, "get_password", _raise)
            mp.setattr(blinkapp, "_secret_key_file_path", lambda: keyfile)
            first = blinkapp._load_or_create_persistent_secret_key()
            second = blinkapp._load_or_create_persistent_secret_key()
        self.assertEqual(first, second)
        self.assertTrue(keyfile.exists())


class TestSessionLifetimeSetting(unittest.TestCase):
    """The configurable login-session lifetime preference."""

    def _write_settings(self, value: str) -> None:
        """Persist a settings file containing sessionLifetimeDays.

        Args:
            value: The sessionLifetimeDays value to store.
        """
        import json

        from blinkapp.services.settings_service import get_settings_file_path

        get_settings_file_path().write_text(json.dumps({"sessionLifetimeDays": value}))

    def test_getter_parses_value(self) -> None:
        """A valid stored value is parsed to an int.

        Tests:
            - get_session_lifetime_days returns the configured day count
        """
        from blinkapp.services import settings_service

        self._write_settings("30")
        self.assertEqual(settings_service.get_session_lifetime_days(), 30)

    def test_getter_invalid_falls_back_to_default(self) -> None:
        """An invalid or non-positive value falls back to the default.

        Tests:
            - A non-numeric value returns Config.SESSION_LIFETIME_DAYS
        """
        from blinkapp.config import Config
        from blinkapp.services import settings_service

        self._write_settings("not-a-number")
        self.assertEqual(
            settings_service.get_session_lifetime_days(), Config.SESSION_LIFETIME_DAYS
        )

    def test_refresh_applies_to_app(self) -> None:
        """Refreshing applies the setting to the app's session lifetime.

        Tests:
            - refresh_session_lifetime sets app.permanent_session_lifetime
              to the configured number of days
        """
        from datetime import timedelta

        from blinkapp import app
        from blinkapp.config import Config
        from blinkapp.services.auth_service import refresh_session_lifetime

        previous = app.permanent_session_lifetime
        try:
            self._write_settings("7")
            refresh_session_lifetime()
            self.assertEqual(app.permanent_session_lifetime, timedelta(days=7))
        finally:
            app.permanent_session_lifetime = previous or timedelta(
                days=Config.SESSION_LIFETIME_DAYS
            )
