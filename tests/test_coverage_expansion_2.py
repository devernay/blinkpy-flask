"""Additional coverage expansion tests targeting low-coverage modules."""

from unittest.mock import patch

import pytest

from blinkapp.models.ids import CameraId, ClipId


class TestSimpleCoverage:
    """Simple tests to expand coverage without complex mocking."""

    def test_clip_id_str_representation(self) -> None:
        """Test ClipId string representation."""
        clip_id = ClipId("test123")
        assert str(clip_id) == "test123"

    def test_camera_id_str_representation(self) -> None:
        """Test CameraId string representation."""
        camera_id = CameraId("cam456")
        assert str(camera_id) == "cam456"

    def test_clip_id_equality(self) -> None:
        """Test ClipId equality comparison."""
        clip1 = ClipId("test123")
        clip2 = ClipId("test123")
        clip3 = ClipId("different")

        assert clip1 == clip2
        assert clip1 != clip3

    def test_camera_id_equality(self) -> None:
        """Test CameraId equality comparison."""
        cam1 = CameraId("cam456")
        cam2 = CameraId("cam456")
        cam3 = CameraId("different")

        assert cam1 == cam2
        assert cam1 != cam3

    def test_cache_basic_operations(self) -> None:
        """Test basic cache operations."""
        from blinkapp.models.cache import Cache

        cache = Cache(maxsize=10)
        cache["key1"] = "value1"

        assert cache.get("key1") == "value1"
        assert cache.get("nonexistent") is None

    def test_cache_contains(self) -> None:
        """Test cache contains operation."""
        from blinkapp.models.cache import Cache

        cache = Cache(maxsize=10)
        cache["key1"] = "value1"

        assert "key1" in cache
        assert "nonexistent" not in cache

    def test_cache_remove(self) -> None:
        """Test cache remove operation."""
        from blinkapp.models.cache import Cache

        cache = Cache(maxsize=10)
        cache["key1"] = "value1"

        removed = cache.pop("key1")
        assert removed == "value1"
        assert cache.get("key1") is None

    def test_cache_keys(self) -> None:
        """Test cache keys operation."""
        from blinkapp.models.cache import Cache

        cache = Cache(maxsize=10)
        cache["key1"] = "value1"
        cache["key2"] = "value2"

        keys = list(cache.keys())
        assert "key1" in keys
        assert "key2" in keys

    def test_error_classes(self) -> None:
        """Test custom error classes."""
        from blinkapp.utils.errors import AuthenticationError, BlinkError

        # Test BlinkError
        error = BlinkError("Test error")
        assert str(error) == "Test error"

        # Test AuthenticationError
        auth_error = AuthenticationError("Auth failed")
        assert str(auth_error) == "Auth failed"

    def test_stream_service_basic(self) -> None:
        """Test basic stream service functions."""
        with patch("blinkapp.services.stream_service.stream_manager", None):
            from blinkapp.services.stream_service import (
                ensure_stream_manager_initialized,
            )

            with pytest.raises(RuntimeError):
                ensure_stream_manager_initialized()

    def test_clip_id_hash(self) -> None:
        """Test ClipId hash functionality."""
        clip_id = ClipId("test123")
        assert hash(clip_id) == hash("test123")

    def test_camera_id_hash(self) -> None:
        """Test CameraId hash functionality."""
        camera_id = CameraId("cam456")
        assert hash(camera_id) == hash("cam456")

    def test_cache_len(self) -> None:
        """Test cache length."""
        from blinkapp.models.cache import Cache

        cache = Cache(maxsize=10)
        assert len(cache) == 0

        cache["key1"] = "value1"
        assert len(cache) == 1

    def test_cache_clear(self) -> None:
        """Test cache clear operation."""
        from blinkapp.models.cache import Cache

        cache = Cache(maxsize=10)
        cache["key1"] = "value1"
        cache["key2"] = "value2"

        cache.clear()
        assert len(cache) == 0

    def test_cache_setdefault(self) -> None:
        """Test cache setdefault operation."""
        from blinkapp.models.cache import Cache

        cache = Cache(maxsize=10)

        # Test setting default for new key
        result = cache.setdefault("key1", "default_value")
        assert result == "default_value"
        assert cache["key1"] == "default_value"

        # Test getting existing key
        result = cache.setdefault("key1", "new_default")
        assert result == "default_value"  # Should return existing value
