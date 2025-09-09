"""Test coverage for cache_service.py functions."""

from unittest.mock import patch

from blinkapp.services import cache_service

from .test_base import (
    create_mock_cache_instance,
    create_mock_camera_cache,
    create_mock_clips_cache,
)


class TestInitializeCaches:
    """Test initialize_caches function."""

    def test_initialize_caches_success(self):
        """Test successful cache initialization."""
        config: dict[str, object] = {"cache_dir": "/test/cache"}

        cache_service.initialize_caches(config)

        # Just verify it doesn't raise an exception
        assert True


class TestCleanupGlobalCaches:
    """Test cleanup_global_caches function."""

    @patch(
        "blinkapp.services.cache_service.camera_thumbnail_cache",
        create_mock_cache_instance(),
    )
    @patch("blinkapp.services.cache_service.clips_cache", create_mock_cache_instance())
    def test_cleanup_global_caches_success(self):
        """Test successful cache cleanup."""
        cache_service.cleanup_global_caches()
        # Function should complete without error


class TestEnsureCachePathsInitialized:
    """Test ensure_cache_paths_initialized function."""

    @patch("blinkapp.CACHE_DIR", "/test/cache")
    @patch("blinkapp.CREDENTIALS_FILE", "/test/creds")
    @patch("blinkapp.THUMBNAIL_CACHE_DIR", "/test/thumbs")
    @patch("blinkapp.CLIPS_CACHE_DIR", "/test/clips")
    @patch("blinkapp.SETTINGS_FILE", "/test/settings")
    def test_ensure_cache_paths_initialized_success(self):
        """Test cache paths initialization."""
        cache_service.ensure_cache_paths_initialized()

        # Just verify it doesn't raise an exception
        assert True


class TestGetCacheStats:
    """Test get_cache_stats function."""

    @patch("blinkapp.services.cache_service.camera_thumbnail_cache")
    @patch("blinkapp.services.cache_service.clips_cache")
    def test_get_cache_stats_success(self, mock_clips_cache, mock_thumb_cache):
        """Test getting cache statistics."""
        mock_thumb_cache.get_stats.return_value = {"size": 10, "hit_rate": 0.8}
        mock_clips_cache.get_stats.return_value = {"size": 5, "hit_rate": 0.9}

        result = cache_service.get_cache_stats()

        assert "camera_thumbnail_cache" in result
        assert "clips_cache" in result


class TestClearAllCaches:
    """Test clear_all_caches function."""

    @patch("blinkapp.services.connection_service.ensure_executor_initialized")
    @patch("blinkapp.services.cache_service.ensure_camera_thumbnail_cache_initialized")
    @patch("blinkapp.services.cache_service.ensure_clips_cache_initialized")
    @patch("blinkapp.services.cache_service.clear_camera_thumbnail_cache_files")
    @patch("blinkapp.services.cache_service.clear_clips_cache_files")
    def test_clear_all_caches_success(
        self,
        mock_clear_clips,
        mock_clear_thumb,
        mock_clips_cache,
        mock_thumb_cache,
        mock_executor,
    ):
        """Test clearing all caches."""
        mock_clear_thumb.return_value = {"status": "success"}
        mock_clear_clips.return_value = {"status": "success"}
        mock_thumb_cache.return_value = create_mock_camera_cache()
        mock_clips_cache.return_value = create_mock_clips_cache()

        result = cache_service.clear_all_caches()

        assert result["status"] == "success"
        assert "message" in result
