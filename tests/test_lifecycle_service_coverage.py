"""Test coverage for lifecycle_service."""

from unittest.mock import Mock, patch

from blinkapp.services import lifecycle_service

from .test_base import BaseTestCase


class TestStartup(BaseTestCase):
    """Test startup function."""

    @patch("blinkapp.services.cache_service.initialize_cache_paths")
    @patch("blinkapp.services.connection_service.initialize_connections")
    @patch("blinkapp.services.cache_service.initialize_caches")
    @patch("blinkapp.services.stream_service.initialize_stream_manager")
    @patch("blinkapp.services.blink_service.initialize_blink_objects")
    @patch("blinkapp.utils.logging_config.setup_logging")
    @patch("blinkapp.CACHE_DIR", "/mock/cache")
    @patch("blinkapp.THUMBNAIL_CACHE_DIR", "/mock/cache/thumbnails")
    @patch("blinkapp.CLIPS_CACHE_DIR", "/mock/cache/clips")
    @patch("pathlib.Path.mkdir")
    def test_startup_success(
        self,
        mock_mkdir,
        mock_logging,
        mock_blink,
        mock_stream,
        mock_caches,
        mock_connections,
        mock_paths,
    ):
        """Test successful startup."""
        lifecycle_service.startup()

        mock_connections.assert_called_once()
        mock_blink.assert_called_once()
        mock_paths.assert_called_once()
        mock_caches.assert_called_once()
        mock_stream.assert_called_once()

    @patch("blinkapp.services.connection_service.initialize_connections")
    def test_startup_exception(self, mock_connections):
        """Test startup with exception - should log but not raise."""
        mock_connections.side_effect = Exception("Startup error")

        # Should not raise exception, just log warning
        lifecycle_service.startup()
        assert True


class TestCleanupResources(BaseTestCase):
    """Test cleanup_resources function."""

    @patch("blinkapp.services.connection_service.executor", Mock())
    @patch("blinkapp.services.stream_service.ensure_stream_manager_initialized")
    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    def test_cleanup_resources_success(self, mock_blink_conn, mock_stream):
        """Test successful resource cleanup."""
        mock_stream_manager = Mock()
        mock_stream.return_value = mock_stream_manager
        mock_blink_connection = Mock()
        mock_blink_conn.return_value = mock_blink_connection

        lifecycle_service.cleanup_resources()

        mock_stream_manager.shutdown.assert_called_once()
        mock_blink_connection.cleanup_active_streams.assert_called_once()

    @patch("blinkapp.services.stream_service.ensure_stream_manager_initialized")
    def test_cleanup_resources_exception(self, mock_stream):
        """Test cleanup with exception - should raise."""
        mock_stream.side_effect = Exception("Cleanup error")

        try:
            lifecycle_service.cleanup_resources()
            raise AssertionError("Should have raised exception")
        except Exception as e:
            assert "Cleanup error" in str(e)
