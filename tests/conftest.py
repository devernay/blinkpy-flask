#!/usr/bin/env python3
"""Pytest configuration for strict patching."""

import os

from tests.test_base import disable_strict_patching, enable_strict_patching


def pytest_configure(config):
    """Configure pytest with optional strict patching."""
    # Enable strict patching if environment variable is set
    if os.environ.get("STRICT_PATCHING", "").lower() in ("1", "true", "yes"):
        enable_strict_patching()
        print("✅ Strict patching enabled - only __all__ exports can be patched")


def pytest_unconfigure(config):
    """Clean up after pytest."""
    # Always restore original patching behavior
    disable_strict_patching()
