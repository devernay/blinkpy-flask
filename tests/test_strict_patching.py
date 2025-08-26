#!/usr/bin/env python3
"""Test strict patching functionality."""

import unittest

from test_utils import disable_strict_patching, enable_strict_patching, strict_patch


class TestStrictPatching(unittest.TestCase):
    """Test that strict patching enforces __all__ exports."""

    def test_strict_patch_allows_exported_symbols(self) -> None:
        """Test that strict_patch allows symbols in __all__."""
        # This should work - 'app' is in blinkapp.__all__
        with strict_patch("blinkapp.app") as mock_app:
            self.assertIsNotNone(mock_app)

    def test_strict_patch_rejects_non_exported_symbols(self) -> None:
        """Test that strict_patch rejects symbols not in __all__."""
        # This should fail - 'Config' is not in blinkapp.__all__
        with self.assertRaises(ValueError) as cm:
            strict_patch("blinkapp.Config")

        self.assertIn("Symbol 'Config' is not exported", str(cm.exception))
        self.assertIn("blinkapp", str(cm.exception))

    def test_strict_patch_allows_modules_without_all(self) -> None:
        """Test that strict_patch allows patching modules without __all__."""
        # This should work - services don't have __all__
        with strict_patch("blinkapp.services.blink_service.blink") as mock_blink:
            self.assertIsNotNone(mock_blink)

    def test_enable_disable_strict_patching(self) -> None:
        """Test enabling and disabling strict patching globally."""
        import unittest.mock

        # Store original
        original = unittest.mock.patch

        # Enable strict patching
        enable_strict_patching()
        self.assertEqual(unittest.mock.patch, strict_patch)

        # Disable strict patching
        disable_strict_patching()
        self.assertEqual(unittest.mock.patch, original)


if __name__ == "__main__":
    unittest.main()
