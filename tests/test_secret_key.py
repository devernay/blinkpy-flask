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
