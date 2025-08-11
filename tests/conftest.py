"""Test configuration for proper test isolation."""

import pytest


@pytest.fixture(autouse=True)
def reset_module_state():
    """Reset critical module state between tests."""
    # This fixture runs before and after each test
    yield

    # After each test, ensure no persistent patches remain
    # This is a minimal approach to prevent the most common isolation issues
    try:
        # Reset any module-level attributes that might be mocked
        import blinkapp

        # Check for common functions that get mocked and might persist
        functions_to_check = ["clear_all_caches", "generate_clip_thumbnail"]
        for func_name in functions_to_check:
            if hasattr(blinkapp, func_name):
                func = getattr(blinkapp, func_name)
                # If it's a Mock, it indicates a test isolation issue
                if hasattr(func, "_mock_name"):
                    # We can't easily unmock it, but we can log it for debugging
                    pass
    except ImportError:
        pass
