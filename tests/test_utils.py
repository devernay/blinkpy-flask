#!/usr/bin/env python3
"""Test utilities for enforcing proper import/patch patterns."""

import importlib
from typing import Any
from unittest.mock import patch as original_patch


def strict_patch(target: str, *args, **kwargs) -> Any:
    """Patch function that only allows patching symbols in __all__.

    Args:
        target: The target to patch (e.g., 'module.symbol')
        *args, **kwargs: Arguments passed to original patch

    Raises:
        ValueError: If symbol is not in module's __all__
    """
    if "." not in target:
        return original_patch(target, *args, **kwargs)

    module_path, symbol = target.rsplit(".", 1)

    try:
        module = importlib.import_module(module_path)
    except ImportError:
        # If module doesn't exist, let original patch handle it
        return original_patch(target, *args, **kwargs)

    # Check if module has __all__ and symbol is not in it
    if hasattr(module, "__all__"):
        if symbol not in module.__all__:
            raise ValueError(
                f"Symbol '{symbol}' is not exported by module '{module_path}'. "
                f"Available exports: {sorted(module.__all__)}"
            )

    return original_patch(target, *args, **kwargs)


# Monkey patch unittest.mock.patch to use strict version
def enable_strict_patching() -> None:
    """Enable strict patching that respects __all__ exports."""
    import unittest.mock

    unittest.mock.patch = strict_patch


def disable_strict_patching() -> None:
    """Disable strict patching and restore original behavior."""
    import unittest.mock

    unittest.mock.patch = original_patch
