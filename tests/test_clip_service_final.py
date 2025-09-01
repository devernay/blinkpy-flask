#!/usr/bin/env python3
"""
Final comprehensive tests to achieve 75% coverage for clip_service.py.
Targets remaining uncovered lines with working, minimal tests.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

from blinkapp.models.ids import ClipId

from .test_base import BaseTestCase


class TestClipServiceFinal(BaseTestCase):
    """Final tests to reach 75% coverage."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()
        self.clip_id = ClipId("123456")

    def test_get_clips_cache_dir(self) -> None:
        """Test _get_clips_cache_dir helper function."""
        from blinkapp.services.clip_download import _get_clips_cache_dir

        with patch("blinkapp.CLIPS_CACHE_DIR", "/test/cache"):
            result = _get_clips_cache_dir()
            assert result == "/test/cache"  # Function returns string, not Path

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_download_clip_common_file_not_exists(self, mock_cache: Mock) -> None:
        """Test download_clip_common with non-existent file."""
        from blinkapp.services.clip_download import download_clip_common

        mock_filepath = Mock(spec=Path)
        mock_filepath.exists.return_value = False

        mock_cache.return_value = {}

        with patch(
            "blinkapp.services.connection_service.ensure_executor_initialized"
        ) as mock_executor:
            mock_executor_instance = Mock(spec=ThreadPoolExecutor)
            mock_executor.return_value = mock_executor_instance

            result = download_clip_common(
                mock_filepath,
                self.clip_id,
            )

            # When file doesn't exist, it returns create_api_response tuple
            assert isinstance(result, tuple)
            assert len(result) >= 2
            _response, status_code = result[0], result[1]
            assert status_code == 404

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_download_clip_common_cached_file_exists(self, mock_cache: Mock) -> None:
        """Test download_clip_common with existing cached file."""
        import tempfile
        from pathlib import Path

        from blinkapp.services.clip_download import download_clip_common

        # Create a real temporary file for the test
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            temp_file.write(b"fake video data")
            temp_path = Path(temp_file.name)

        try:
            mock_cache_instance = {self.clip_id: {"filepath": temp_path}}
            mock_cache.return_value = mock_cache_instance

            mock_send_file = Mock(return_value="file_response")

            with patch("blinkapp.services.clip_download.send_file", mock_send_file):
                with patch(
                    "blinkapp.services.connection_service.ensure_executor_initialized"
                ) as mock_executor:
                    mock_executor_instance = Mock(spec=ThreadPoolExecutor)
                    mock_executor.return_value = mock_executor_instance

                    # Need Flask request context for send_file
                    from blinkapp import app

                    with app.test_request_context():
                        result = download_clip_common(temp_path, self.clip_id)

                    mock_send_file.assert_called_once()
                    # When file exists, it returns send_file response directly
                    assert result == "file_response"
        finally:
            # Clean up the temporary file
            if temp_path.exists():
                temp_path.unlink()

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_process_local_clips_default_dependencies(self, mock_cache: Mock) -> None:
        """Test process_local_clips with default dependencies."""
        from blinkapp.services.clip_service import process_local_clips

        mock_cache.return_value = {}

        with patch("blinkapp.services.blink_service.blink") as mock_blink:
            with patch("blinkapp.services.blink_service.blink_connection"):
                with patch(
                    "blinkapp.utils.formatters.format_clips_by_day"
                ) as mock_format:
                    mock_blink.sync = {}
                    mock_format.return_value = []

                    result = process_local_clips()

                    assert result == []

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_process_cloud_clips_empty_metadata(self, mock_cache: Mock) -> None:
        """Test process_cloud_clips with empty metadata."""
        from blinkapp.services.clip_service import process_cloud_clips

        mock_cache.return_value = {}

        with patch("blinkapp.utils.formatters.format_clips_by_day") as mock_format:
            mock_format.return_value = []

            result = process_cloud_clips([])

            assert result == []

    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    def test_download_and_cache_cloud_thumbnail_exception(
        self, mock_cache: Mock
    ) -> None:
        """Test download_and_cache_cloud_thumbnail with exception."""
        from blinkapp.services.clip_processing import download_and_cache_cloud_thumbnail

        mock_cache.return_value = {}

        with (
            patch(
                "blinkapp.services.clip_processing.requests.get",
                side_effect=Exception("Network error"),
            ),
            patch("pathlib.Path.exists", return_value=False),
        ):
            result = download_and_cache_cloud_thumbnail(
                self.clip_id, "http://example.com/thumb.jpg"
            )

            assert result is None
