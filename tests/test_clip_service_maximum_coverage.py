"""Test clip service maximum coverage with realistic tests."""

from pathlib import Path
from unittest.mock import patch

from test_base import BaseTestCase, create_mock_blink_instance

from blinkapp.models.ids import ClipId


class TestClipServiceMaximumCoverage(BaseTestCase):
    """Test clip service with maximum coverage - realistic tests only."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()
        self.clip_id = ClipId("123456")
        self.mock_blink = create_mock_blink_instance()
        self.mock_cache_dir = Path("/tmp/test_cache")

    def test_download_cloud_clip_core_sync_no_blink_instance(self) -> None:
        """Test _download_cloud_clip_core_sync with no blink instance."""
        from blinkapp.services.clip_download import _download_cloud_clip_core_sync

        filepath, error = _download_cloud_clip_core_sync(
            self.clip_id, None, self.mock_cache_dir
        )

        assert error is not None
        assert "Error downloading cloud clip 123456" in error
        assert "'NoneType' object has no attribute 'get_clip_url'" in error
        assert filepath is None

    def test_download_cloud_clip_core_sync_success(self) -> None:
        """Test _download_cloud_clip_core_sync successful download."""
        from blinkapp.services.clip_download import _download_cloud_clip_core_sync

        # Mock successful async download
        with patch("asyncio.run") as mock_run:
            mock_run.return_value = (self.mock_cache_dir / "123456.mp4", None)

            filepath, error = _download_cloud_clip_core_sync(
                self.clip_id, self.mock_blink, self.mock_cache_dir
            )

        assert error is None
        assert filepath == self.mock_cache_dir / "123456.mp4"
        mock_run.assert_called_once()
