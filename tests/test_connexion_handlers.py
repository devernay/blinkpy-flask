"""Unit tests for connexion handlers.

Tests connexion-compatible handlers including:
- Handler function behavior
- Request/response processing
- Authentication handling
- API contract validation
"""

from typing import Any, cast
from unittest.mock import Mock, patch

from blinkpy.blinkpy import Blink
from blinkpy.camera import BlinkCamera

from blinkapp.connexion_handlers import auth, camera, clips, system
from blinkapp.models.types import JsonDict
from tests.test_base import BaseTestCase


class TestAuthHandlers(BaseTestCase):
    """Test authentication connexion handlers."""

    @patch("flask.session", {"authenticated": True})
    @patch("flask.render_template")
    def test_main_page(self, mock_render: Mock) -> None:
        """Test main page handler returns rendered template."""
        mock_render.return_value = "<html>Main Page</html>"

        result = auth.main_page()

        self.assertEqual(result, "<html>Main Page</html>")
        mock_render.assert_called_once_with("index.html")


class TestSystemHandlers(BaseTestCase):
    """Test system management connexion handlers."""

    @patch("blinkapp.services.system_service.get_systems")
    def test_get_systems(self, mock_service: Mock) -> None:
        """Test get_systems handler delegates to service."""
        mock_service.return_value = {"systems": []}

        result = system.get_systems()

        self.assertEqual(result, {"systems": []})
        mock_service.assert_called_once()

    @patch("blinkapp.services.blink_validators.require_sync_module")
    def test_get_system_devices_valid_id(self, mock_validator: Mock) -> None:
        """Test get_system_devices with valid network ID."""
        mock_sync = Mock()
        mock_sync.cameras = {}  # Empty cameras dict
        mock_sync.online = True
        mock_sync.sync_id = 12345
        mock_validator.return_value = (mock_sync, None)

        result = system.get_system_devices("12345")

        self.assertEqual(result, {"devices": [{"type": "sync_module", "name": "Sync Module", "online": True, "id": 12345}]})
        mock_validator.assert_called_once()

    def test_get_system_devices_invalid_id(self) -> None:
        """Test get_system_devices with invalid network ID."""
        result = system.get_system_devices("invalid")

        self.assertIsInstance(result, tuple)
        data, status = result
        self.assertEqual(status, 400)
        self.assertFalse(cast(JsonDict, data)["success"])
        self.assertIn("Invalid network ID", cast(str, cast(JsonDict, data)["error"]))

    @patch("blinkapp.services.blink_validators.require_sync_module")
    def test_get_devices_valid_id(self, mock_validator: Mock) -> None:
        """Test get_devices with valid network ID."""
        from blinkpy.sync_module import BlinkSyncModule
        
        mock_sync = Mock(spec=BlinkSyncModule)
        mock_sync.cameras = {}
        mock_sync.online = True
        mock_sync.sync_id = 12345
        mock_validator.return_value = (mock_sync, None)

        result = system.get_system_devices("12345")

        expected_devices = [{"type": "sync_module", "name": "Sync Module", "online": True, "id": 12345}]
        self.assertEqual(result, {"devices": expected_devices})
        mock_validator.assert_called_once()

    def test_get_devices_invalid_id(self) -> None:
        """Test get_devices with invalid network ID."""
        result = system.get_system_devices("invalid")

        self.assertIsInstance(result, tuple)
        data, status = result
        self.assertEqual(status, 400)
        self.assertFalse(cast(JsonDict, data)["success"])
        self.assertIn("Invalid network ID", cast(str, cast(JsonDict, data)["error"]))

    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.blink_validators.require_sync_module")
    def test_update_system_valid_request(self, mock_validator: Mock, mock_connection: Mock) -> None:
        """Test update_system with valid request."""
        from blinkpy.sync_module import BlinkSyncModule
        from blinkapp.services.blink_connection import BlinkConnection
        
        mock_sync = Mock(spec=BlinkSyncModule)
        mock_sync.async_arm.return_value = Mock()  # Mock coroutine
        mock_validator.return_value = (mock_sync, None)
        
        mock_connection.execute.return_value = None
        
        body: JsonDict = {"armed": True}

        result = system.update_system_settings("12345", body)

        self.assertEqual(result, {"armed": True})
        mock_validator.assert_called_once()
        mock_connection.execute.assert_called_once()

    def test_update_system_invalid_id(self) -> None:
        """Test update_system with invalid network ID."""
        body: JsonDict = {"armed": True}

        result = system.update_system_settings("invalid", body)

        self.assertIsInstance(result, tuple)
        data, status = result
        self.assertEqual(status, 400)
        self.assertFalse(cast(JsonDict, data)["success"])
        self.assertIn("Invalid network ID", cast(str, cast(JsonDict, data)["error"]))

    def test_update_system_missing_armed(self) -> None:
        """Test update_system with missing armed field."""
        body: JsonDict = {}

        result = system.update_system_settings("12345", body)

        self.assertIsInstance(result, tuple)
        data, status = result
        self.assertEqual(status, 400)
        self.assertFalse(cast(JsonDict, data)["success"])
        self.assertIn(
            "Missing required field: armed", cast(str, cast(JsonDict, data)["error"])
        )

    def test_update_system_invalid_armed_type(self) -> None:
        """Test update_system with invalid armed field type."""
        body: JsonDict = {"armed": "true"}  # String instead of boolean

        result = system.update_system_settings("12345", body)

        self.assertIsInstance(result, tuple)
        data, status = result
        self.assertEqual(status, 400)
        self.assertFalse(cast(JsonDict, data)["success"])
        self.assertIn(
            "Field 'armed' must be boolean", cast(str, cast(JsonDict, data)["error"])
        )

    @patch("blinkapp.services.system_service.refresh_system")
    def test_clear_systems_cache(self, mock_refresh: Mock) -> None:
        """Test clear_systems_cache handler."""
        mock_refresh.return_value = {"success": True, "message": "Cache cleared"}

        result = system.clear_systems_cache()

        self.assertEqual(result, {"success": True, "message": "Cache cleared"})
        mock_refresh.assert_called_once()


class TestCameraHandlers(BaseTestCase):
    """Test camera management connexion handlers."""

    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    @patch("blinkapp.services.device_service.create_device_data")
    def test_list_cameras_with_cameras(
        self, mock_create_data: Mock, mock_ensure: Mock
    ) -> None:
        """Test list_cameras with available cameras."""
        # Mock blink connection and cameras
        mock_blink = Mock(spec=Blink)
        mock_blink.cameras = {
            "cam1": Mock(spec=BlinkCamera),
            "cam2": Mock(spec=BlinkCamera),
        }
        mock_connection = Mock(spec=callable)
        mock_connection.blink = mock_blink
        mock_ensure.return_value = mock_connection

        # Mock device data creation
        mock_create_data.side_effect = [
            {"id": "cam1", "name": "Camera 1"},
            {"id": "cam2", "name": "Camera 2"},
        ]

        result = camera.list_cameras()

        cameras = cast(list[Any], result["cameras"])
        self.assertEqual(len(cameras), 2)
        self.assertEqual(cameras[0]["id"], "cam1")
        self.assertEqual(cameras[1]["id"], "cam2")
        mock_ensure.assert_called_once()
        self.assertEqual(mock_create_data.call_count, 2)

    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    def test_list_cameras_no_blink(self, mock_ensure: Mock) -> None:
        """Test list_cameras when blink is None."""
        mock_connection = Mock(spec=callable)
        mock_connection.blink = None
        mock_ensure.return_value = mock_connection

        result = camera.list_cameras()

        self.assertEqual(result, {"cameras": []})
        mock_ensure.assert_called_once()

    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    def test_list_cameras_no_cameras_attribute(self, mock_ensure: Mock) -> None:
        """Test list_cameras when blink has no cameras attribute."""
        mock_blink = Mock(spec=Blink)  # Mock without cameras attribute
        mock_connection = Mock(spec=callable)
        mock_connection.blink = mock_blink
        mock_ensure.return_value = mock_connection

        result = camera.list_cameras()

        self.assertEqual(result, {"cameras": []})
        mock_ensure.assert_called_once()


class TestClipsHandlers(BaseTestCase):
    """Test clips management connexion handlers."""

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.clip_service.process_cloud_clips")
    @patch("blinkapp.utils.decorators.error_context")
    def test_get_clips_cloud_default(
        self,
        mock_context: Mock,
        mock_process: Mock,
        mock_connection: Mock,
        mock_blink: Mock,
    ) -> None:
        """Test get_clips with default (cloud) storage."""
        # Setup mocks
        mock_blink.__bool__ = Mock(return_value=True)
        mock_connection.execute.return_value = [{"id": "clip1"}]
        mock_process.return_value = [{"date": "2024-01-01", "clips": []}]
        mock_context.return_value.__enter__ = Mock(return_value=None)
        mock_context.return_value.__exit__ = Mock(return_value=None)

        result = clips.get_clips()

        self.assertEqual(result, {"clips": [{"date": "2024-01-01", "clips": []}]})
        mock_connection.execute.assert_called_once()
        mock_process.assert_called_once_with([{"id": "clip1"}])

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection")
    @patch("blinkapp.services.clip_service.process_cloud_clips")
    @patch("blinkapp.utils.decorators.error_context")
    def test_get_clips_cloud_explicit(
        self,
        mock_context: Mock,
        mock_process: Mock,
        mock_connection: Mock,
        mock_blink: Mock,
    ) -> None:
        """Test get_clips with explicit cloud storage."""
        # Setup mocks
        mock_blink.__bool__ = Mock(return_value=True)
        mock_connection.execute.return_value = [{"id": "clip1"}]
        mock_process.return_value = [{"date": "2024-01-01", "clips": []}]
        mock_context.return_value.__enter__ = Mock(return_value=None)
        mock_context.return_value.__exit__ = Mock(return_value=None)

        result = clips.get_clips("cloud")

        self.assertEqual(result, {"clips": [{"date": "2024-01-01", "clips": []}]})
        mock_connection.execute.assert_called_once()
        mock_process.assert_called_once_with([{"id": "clip1"}])

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.clip_service.process_local_clips")
    @patch("blinkapp.utils.decorators.error_context")
    def test_get_clips_local(
        self, mock_context: Mock, mock_process: Mock, mock_blink: Mock
    ) -> None:
        """Test get_clips with local storage."""
        # Setup mocks
        mock_blink.__bool__ = Mock(return_value=True)
        mock_process.return_value = [{"date": "2024-01-01", "clips": []}]
        mock_context.return_value.__enter__ = Mock(return_value=None)
        mock_context.return_value.__exit__ = Mock(return_value=None)

        result = clips.get_clips("local")

        self.assertEqual(result, {"clips": [{"date": "2024-01-01", "clips": []}]})
        mock_process.assert_called_once()

    def test_get_clips_invalid_storage(self) -> None:
        """Test get_clips with invalid storage type."""
        result = clips.get_clips("invalid")

        self.assertIsInstance(result, tuple)
        data, status = result
        self.assertEqual(status, 400)
        self.assertFalse(cast(JsonDict, data)["success"])
        self.assertIn("Invalid storage type", cast(str, cast(JsonDict, data)["error"]))

    @patch("blinkapp.services.blink_service.blink")
    @patch("blinkapp.services.blink_service.blink_connection", None)
    @patch("blinkapp.services.clip_service.process_cloud_clips")
    @patch("blinkapp.utils.decorators.error_context")
    def test_get_clips_no_connection(
        self, mock_context: Mock, mock_process: Mock, mock_blink: Mock
    ) -> None:
        """Test get_clips when blink_connection is None."""
        # Setup mocks
        mock_blink.__bool__ = Mock(return_value=True)
        mock_process.return_value = []
        mock_context.return_value.__enter__ = Mock(return_value=None)
        mock_context.return_value.__exit__ = Mock(return_value=None)

        result = clips.get_clips("cloud")

        self.assertEqual(result, {"clips": []})
        mock_process.assert_called_once_with([])
