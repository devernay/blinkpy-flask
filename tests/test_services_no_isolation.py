"""Service tests without test isolation.

This file contains tests for service functions that need to test the original
implementation rather than the test-isolated mock versions. The main test_services.py
file uses test isolation which replaces certain functions (like initialize_cache_paths)
with mocks to prevent file system operations during testing.

When we need to test the actual implementation behavior (like verifying that pathlib.Path
is called correctly), we use this separate file that imports the real functions before
test isolation can replace them.

Key differences from test_services.py:
- No test isolation fixture (functions run as-is)
- Can test actual pathlib operations and file system logic
- Uses strict patching for safety
- Imports real functions at module level before pytest fixtures run
"""

from unittest.mock import Mock

# Import real functions BEFORE pytest fixtures run
from blinkapp.services.cache_service import (
    initialize_cache_paths as real_initialize_cache_paths,
)

# Import strict patching from test_base
from tests.test_base import strict_patch


class TestCacheServiceNoIsolation:
    """Test cache service functions without test isolation."""

    def test_initialize_cache_paths_calls_pathlib(self) -> None:
        """Test that initialize_cache_paths calls pathlib.Path correctly."""
        with (
            strict_patch("pathlib.Path") as mock_path_class,
            strict_patch(
                "blinkapp.services.cache_service._get_cache_dir_config",
                return_value="/test/cache",
            ),
        ):
            mock_path = Mock()
            mock_path_class.return_value = mock_path
            mock_path.__truediv__ = Mock(return_value=Mock())

            real_initialize_cache_paths()

            # Verify pathlib.Path was called
            assert mock_path_class.called, "pathlib.Path should have been called"
            assert mock_path.mkdir.called, "mkdir should have been called"

    def test_initialize_cache_paths_with_config(self) -> None:
        """Test cache path initialization with app config (non-isolated version)."""
        with (
            strict_patch("pathlib.Path") as mock_path_class,
            strict_patch(
                "blinkapp.services.cache_service._get_cache_dir_config",
                return_value="/custom/cache",
            ),
        ):
            mock_path = Mock()
            mock_path_class.return_value = mock_path
            mock_path.__truediv__ = Mock(return_value=Mock())

            real_initialize_cache_paths()

            # Should have created Path instances and called mkdir
            mock_path_class.assert_called()
            mock_path.mkdir.assert_called()
