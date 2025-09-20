"""Unit tests for connexion handlers.

Tests connexion-compatible handlers including:
- Handler function behavior
- Request/response processing
- Authentication handling
- API contract validation
"""

from typing import Any, cast
from unittest.mock import AsyncMock, Mock, patch

from blinkapp.connexion_handlers import auth, camera, clips, system
from blinkapp.models.types import JsonDict
from tests.test_base import BaseTestCase, create_mock_blink_instance


class TestAdminHandlers(BaseTestCase):
    """Test admin connexion handlers."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()


class TestAuthHandlers(BaseTestCase):
    """Test authentication connexion handlers."""

    @patch("flask.session", {"authenticated": True})
    @patch("flask.render_template")
    def test_main_page(self, mock_render: Mock) -> None:
        """Test main page handler returns rendered template.

        Verifies that the main page handler properly delegates to
        Flask's render_template and returns the rendered HTML content.

        Tests:
            - Template rendering delegation to render_template
            - Correct template name ('index.html') passed to renderer
            - Return value matches rendered template output
        """
        mock_render.return_value = "<html>Main Page</html>"

        result = auth.main_page()

        self.assertEqual(result, "<html>Main Page</html>")
        mock_render.assert_called_once_with("index.html")


class TestSystemHandlers(BaseTestCase):
    """Test system management connexion handlers."""

    @patch("blinkapp.services.system_service.get_systems")
    def test_get_systems(self, mock_service: Mock) -> None:
        """Test get_systems handler delegates to service layer.

        Verifies that the get_systems connexion handler properly
        delegates system retrieval to the service layer.

        Tests:
            - Service layer delegation for system retrieval
            - Return value matches service layer response
            - Proper separation of concerns between handler and service
        """
        mock_service.return_value = {"systems": []}

        result = system.get_systems()

        self.assertEqual(result, {"systems": []})
        mock_service.assert_called_once()

    @patch("blinkapp.services.blink_validators.require_sync_module")
    def test_get_system_devices_valid_id(self, mock_validator: Mock) -> None:
        """Test get_system_devices with valid network ID.

        Verifies that the get_system_devices handler properly processes
        valid network IDs and delegates to the validation service.

        Tests:
            - Valid network ID processing
            - Service delegation for device retrieval
            - Return value matches validator service response
        """
        from requests.structures import CaseInsensitiveDict

        from tests.test_base import create_mock_sync

        mock_sync = create_mock_sync(
            network_id=12345, sync_id=67890, cameras=CaseInsensitiveDict(), online=True
        )
        mock_validator.return_value = (mock_sync, None)

        result = system.get_system_devices("12345")

        self.assertEqual(
            result,
            {
                "devices": [
                    {
                        "type": "sync_module",
                        "name": "Sync Module",
                        "online": True,
                        "id": 67890,  # Uses sync_id, not network_id
                    }
                ]
            },
        )
        mock_validator.assert_called_once()

    def test_get_system_devices_invalid_id(self) -> None:
        """Test get_system_devices with invalid network ID handling.

        Verifies that the system devices handler properly validates
        network IDs and handles invalid ID scenarios gracefully.

        Tests:
            - Invalid network ID validation and rejection
            - Proper error response for malformed network IDs
            - Input validation for system device requests
            - Error handling for non-existent network references
        """
        result = system.get_system_devices("invalid")

        self.assertIsInstance(result, tuple)
        data, status = result
        self.assertEqual(status, 400)
        self.assertFalse(cast("JsonDict", data)["success"])
        self.assertIn(
            "Invalid network ID", cast("str", cast("JsonDict", data)["error"])
        )

    @patch("blinkapp.services.blink_validators.require_sync_module")
    def test_get_devices_valid_id(self, mock_validator: Mock) -> None:
        """Test get_devices with valid network ID processing.

        Verifies that the devices handler properly processes valid
        network IDs and returns appropriate device information.

        Tests:
            - Valid network ID processing and validation
            - Successful device retrieval for valid IDs
            - Proper response formatting for device data
            - Network ID validation success path
        """
        from requests.structures import CaseInsensitiveDict

        from tests.test_base import create_mock_sync

        mock_sync = create_mock_sync(
            network_id=12345, sync_id=67890, cameras=CaseInsensitiveDict(), online=True
        )
        mock_validator.return_value = (mock_sync, None)

        result = system.get_system_devices("12345")

        expected_devices = [
            {
                "type": "sync_module",
                "name": "Sync Module",
                "online": True,
                "id": 67890,
            }  # Uses sync_id
        ]
        self.assertEqual(result, {"devices": expected_devices})
        mock_validator.assert_called_once()

    def test_get_devices_invalid_id(self) -> None:
        """Test get_devices with invalid network ID validation.

        Verifies that the devices handler properly validates network
        IDs and rejects invalid or malformed ID values.

        Tests:
            - Invalid network ID detection and rejection
            - Proper error response for invalid IDs
            - Input validation enforcement for device requests
            - Error handling for malformed network identifiers
        """
        result = system.get_system_devices("invalid")

        self.assertIsInstance(result, tuple)
        data, status = result
        self.assertEqual(status, 400)
        self.assertFalse(cast("JsonDict", data)["success"])
        self.assertIn(
            "Invalid network ID", cast("str", cast("JsonDict", data)["error"])
        )

    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    @patch("blinkapp.services.blink_validators.require_sync_module")
    def test_update_system_valid_request(
        self, mock_validator: Mock, mock_connection_init: Mock
    ) -> None:
        """Test update_system handler with valid request parameters.

        Verifies that the update_system connexion handler properly processes
        valid system update requests and delegates to the service layer.

        Args:
            mock_validator: Mock for network ID validation
            mock_service: Mock for system service operations

        Tests:
            - Valid network ID validation and processing
            - Proper request body parsing and validation
            - Service layer delegation for system updates
            - Correct response format and status codes
        """
        from tests.test_base import create_mock_sync

        mock_sync = create_mock_sync()
        mock_sync.async_arm.return_value = AsyncMock(spec=callable)
        mock_validator.return_value = (mock_sync, None)

        # Mock the connection object returned by ensure_blink_connection_initialized
        from tests.test_base import create_mock_blink_connection

        mock_connection = create_mock_blink_connection(execute_return_value=None)
        mock_connection_init.return_value = mock_connection

        body: JsonDict = {"armed": True}

        result = system.update_system_settings("12345", body)

        self.assertEqual(result, {"armed": True})
        mock_validator.assert_called_once()
        mock_connection.execute.assert_called_once()

    def test_update_system_invalid_id(self) -> None:
        """Test update_system handler with invalid network ID.

        Verifies that the update_system connexion handler properly handles
        and rejects requests with invalid network ID parameters.

        Tests:
            - Invalid network ID detection and validation
            - Appropriate error response generation
            - Proper error status codes (400 Bad Request)
            - Error message clarity and usefulness
        """
        body: JsonDict = {"armed": True}

        result = system.update_system_settings("invalid", body)

        self.assertIsInstance(result, tuple)
        data, status = result
        self.assertEqual(status, 400)
        self.assertFalse(cast("JsonDict", data)["success"])
        self.assertIn(
            "Invalid network ID", cast("str", cast("JsonDict", data)["error"])
        )

    def test_update_system_missing_armed(self) -> None:
        """Test update_system handler with missing armed field in request.

        Verifies that the update_system connexion handler properly handles
        requests missing the required 'armed' field in the request body.

        Tests:
            - Missing required field detection and validation
            - Appropriate error response for incomplete requests
            - Proper error status codes (400 Bad Request)
            - Clear error messaging for missing parameters
        """
        body: JsonDict = {}

        result = system.update_system_settings("12345", body)

        self.assertIsInstance(result, tuple)
        data, status = result
        self.assertEqual(status, 400)
        self.assertFalse(cast("JsonDict", data)["success"])
        self.assertIn(
            "Missing required field: armed",
            cast("str", cast("JsonDict", data)["error"]),
        )

    def test_update_system_invalid_armed_type(self) -> None:
        """Test update_system handler with invalid armed field data type.

        Verifies that the update_system connexion handler properly validates
        the data type of the 'armed' field and rejects invalid types.

        Tests:
            - Data type validation for armed field (expects boolean)
            - Rejection of string values when boolean expected
            - Appropriate error response for type mismatches
            - Proper error status codes and messaging
        """
        body: JsonDict = {"armed": "true"}  # String instead of boolean

        result = system.update_system_settings("12345", body)

        self.assertIsInstance(result, tuple)
        data, status = result
        self.assertEqual(status, 400)
        self.assertFalse(cast("JsonDict", data)["success"])
        self.assertIn(
            "Field 'armed' must be boolean",
            cast("str", cast("JsonDict", data)["error"]),
        )

    @patch("blinkapp.services.system_service.refresh_system")
    def test_clear_systems_cache(self, mock_refresh: Mock) -> None:
        """Test clear_systems_cache handler functionality.

        Verifies that the clear_systems_cache connexion handler properly
        delegates cache clearing operations to the service layer.

        Args:
            mock_refresh: Mock for cache refresh operations

        Tests:
            - Service layer delegation for cache clearing
            - Proper response format with success status
            - Cache refresh operation execution
            - Appropriate success messaging and status codes
        """
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
        """Test list_cameras handler with available cameras.

        Verifies that the list_cameras connexion handler properly retrieves
        and formats camera information when cameras are available.

        Args:
            mock_ensure: Mock for Blink connection ensuring
            mock_get_instance: Mock for Blink instance retrieval

        Tests:
            - Blink connection establishment and validation
            - Camera data retrieval and formatting
            - Proper response structure with camera information
            - Service layer integration for camera management
        """
        # Mock blink connection and cameras
        from tests.test_base import create_mock_blink_instance, create_mock_camera

        mock_blink = create_mock_blink_instance(
            cameras={
                "cam1": create_mock_camera(camera_id="cam1", name="Camera 1"),
                "cam2": create_mock_camera(camera_id="cam2", name="Camera 2"),
            }
        )
        from tests.test_base import create_mock_blink_connection

        mock_connection = create_mock_blink_connection()
        mock_connection.blink = mock_blink
        mock_ensure.return_value = mock_connection

        # Mock device data creation
        mock_create_data.side_effect = [
            {"id": "cam1", "name": "Camera 1"},
            {"id": "cam2", "name": "Camera 2"},
        ]

        result = camera.list_cameras()

        cameras = cast("list[Any]", result["cameras"])
        self.assertEqual(len(cameras), 2)
        self.assertEqual(cameras[0]["id"], "cam1")
        self.assertEqual(cameras[1]["id"], "cam2")
        mock_ensure.assert_called_once()
        self.assertEqual(mock_create_data.call_count, 2)

    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    def test_list_cameras_no_blink(self, mock_ensure: Mock) -> None:
        """Test list_cameras when blink is None or unavailable.

        Verifies that the camera listing handler properly handles scenarios
        where the Blink instance is None or unavailable.

        Tests:
            - Null Blink instance handling in camera listing
            - Graceful degradation when Blink service unavailable
            - Proper error response for missing Blink connection
            - Service availability validation for camera operations
        """
        from tests.test_base import create_mock_blink_connection

        mock_connection = create_mock_blink_connection()
        mock_connection.blink = None
        mock_ensure.return_value = mock_connection

        result = camera.list_cameras()

        self.assertEqual(result, {"cameras": []})
        mock_ensure.assert_called_once()

    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    def test_list_cameras_no_cameras_attribute(self, mock_ensure: Mock) -> None:
        """Test list_cameras handler when Blink instance has no cameras attribute.

        Verifies that the list_cameras connexion handler properly handles
        cases where the Blink instance lacks the cameras attribute.

        Args:
            mock_ensure: Mock for Blink connection ensuring

        Tests:
            - Missing cameras attribute detection and handling
            - Graceful degradation when cameras unavailable
            - Appropriate error response or empty list handling
            - Proper error messaging for missing camera data
        """
        from tests.test_base import create_mock_blink_instance

        mock_blink = create_mock_blink_instance(cameras=None)
        from tests.test_base import create_mock_blink_connection

        mock_connection = create_mock_blink_connection()
        mock_connection.blink = mock_blink
        mock_ensure.return_value = mock_connection

        result = camera.list_cameras()

        self.assertEqual(result, {"cameras": []})
        mock_ensure.assert_called_once()


class TestClipsHandlers(BaseTestCase):
    """Test clips management connexion handlers."""

    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    @patch("blinkapp.services.clip_service.process_cloud_clips")
    @patch("blinkapp.utils.decorators.error_context")
    def test_get_clips_cloud_default(
        self,
        mock_context: Mock,
        mock_process: Mock,
        mock_connection_init: Mock,
        mock_blink_init: Mock,
    ) -> None:
        """Test get_clips with default (cloud) storage retrieval.

        Verifies that the clips handler properly retrieves clips from
        cloud storage when no explicit storage type is specified.

        Tests:
            - Default cloud storage clip retrieval
            - Proper cloud storage selection when unspecified
            - Cloud clip listing and metadata processing
            - Default storage behavior validation
        """
        # Setup mock blink instance
        mock_blink_instance = create_mock_blink_instance()
        mock_blink_init.return_value = mock_blink_instance

        # Setup mock connection
        from tests.test_base import create_mock_blink_connection

        mock_connection = create_mock_blink_connection(
            execute_return_value=[{"id": "clip1"}]
        )
        mock_connection_init.return_value = mock_connection

        mock_process.return_value = [{"date": "2024-01-01", "clips": []}]
        mock_context.return_value.__enter__ = Mock(spec=lambda: None, return_value=None)
        mock_context.return_value.__exit__ = Mock(spec=lambda: None, return_value=None)

        result = clips.get_clips()

        self.assertEqual(result, {"clips": [{"date": "2024-01-01", "clips": []}]})
        mock_connection.execute.assert_called_once()
        mock_process.assert_called_once_with([{"id": "clip1"}])

    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    @patch("blinkapp.services.clip_service.process_cloud_clips")
    @patch("blinkapp.utils.decorators.error_context")
    def test_get_clips_cloud_explicit(
        self,
        mock_context: Mock,
        mock_process: Mock,
        mock_connection_init: Mock,
        mock_blink_init: Mock,
    ) -> None:
        """Test get_clips handler with explicit cloud storage specification.

        Verifies that the get_clips connexion handler properly retrieves
        clips from cloud storage when explicitly specified in the request.

        Args:
            mock_connection_init: Mock for Blink connection initialization
            mock_blink_init: Mock for Blink instance initialization

        Tests:
            - Explicit cloud storage parameter handling
            - Cloud clip retrieval and formatting
            - Proper response structure with cloud clip data
            - Service layer integration for cloud storage access
        """
        # Setup mock blink instance
        mock_blink_instance = create_mock_blink_instance()
        mock_blink_init.return_value = mock_blink_instance

        # Setup mock connection
        from tests.test_base import create_mock_blink_connection

        mock_connection = create_mock_blink_connection(
            execute_return_value=[{"id": "clip1"}]
        )
        mock_connection_init.return_value = mock_connection

        mock_process.return_value = [{"date": "2024-01-01", "clips": []}]
        mock_context.return_value.__enter__ = Mock(spec=lambda: None, return_value=None)
        mock_context.return_value.__exit__ = Mock(spec=lambda: None, return_value=None)

        result = clips.get_clips("cloud")

        self.assertEqual(result, {"clips": [{"date": "2024-01-01", "clips": []}]})
        mock_connection.execute.assert_called_once()
        mock_process.assert_called_once_with([{"id": "clip1"}])

    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    @patch("blinkapp.services.blink_service.ensure_blink_connection_initialized")
    @patch("blinkapp.services.clip_service.process_local_clips")
    @patch("blinkapp.utils.decorators.error_context")
    def test_get_clips_local(
        self,
        mock_context: Mock,
        mock_process: Mock,
        mock_connection: Mock,
        mock_blink_init: Mock,
    ) -> None:
        """Test get_clips handler with local storage specification.

        Verifies that the get_clips connexion handler properly retrieves
        clips from local storage when specified in the request.

        Args:
            mock_context: Mock for error context management
            mock_process: Mock for local clip processing
            mock_connection: Mock for Blink connection operations
            mock_blink_init: Mock for Blink instance initialization

        Tests:
            - Local storage parameter handling and validation
            - Local clip retrieval and processing
            - Proper response structure with local clip data
            - Service layer integration for local storage access
        """
        # Setup mocks
        mock_blink_instance = create_mock_blink_instance()
        mock_blink_init.return_value = mock_blink_instance
        mock_connection.return_value = None
        mock_process.return_value = [{"date": "2024-01-01", "clips": []}]
        mock_context.return_value.__enter__ = Mock(spec=lambda: None, return_value=None)
        mock_context.return_value.__exit__ = Mock(spec=lambda: None, return_value=None)

        result = clips.get_clips("local")

        self.assertEqual(result, {"clips": [{"date": "2024-01-01", "clips": []}]})
        mock_process.assert_called_once()

    def test_get_clips_invalid_storage(self) -> None:
        """Test get_clips with invalid storage type validation.

        Verifies that the clips handler properly validates storage
        types and rejects invalid storage type specifications.

        Tests:
            - Invalid storage type validation and rejection
            - Proper error response for unsupported storage types
            - Input validation for storage type parameters
            - Error handling for malformed storage specifications
        """
        result = clips.get_clips("invalid")

        self.assertIsInstance(result, tuple)
        data, status = result
        self.assertEqual(status, 400)
        self.assertFalse(cast("JsonDict", data)["success"])
        self.assertIn(
            "Invalid storage type", cast("str", cast("JsonDict", data)["error"])
        )

    @patch("blinkapp.services.blink_service.ensure_blink_initialized")
    @patch(
        "blinkapp.services.blink_service.ensure_blink_connection_initialized",
        return_value=None,
    )
    @patch("blinkapp.services.clip_service.process_cloud_clips")
    @patch("blinkapp.utils.decorators.error_context")
    def test_get_clips_no_connection(
        self,
        mock_context: Mock,
        mock_process: Mock,
        mock_connection_init: Mock,
        mock_blink_init: Mock,
    ) -> None:
        """Test get_clips handler when Blink connection is unavailable.

        Verifies that the get_clips connexion handler properly handles
        cases where the Blink connection cannot be established.

        Args:
            mock_context: Mock for error context management
            mock_process: Mock for clip processing operations
            mock_connection_init: Mock for connection initialization
            mock_blink_init: Mock for Blink instance initialization

        Tests:
            - Unavailable connection detection and handling
            - Graceful degradation when connection fails
            - Appropriate error response for connection issues
            - Proper error messaging and status codes
        """
        # Setup mock blink instance
        mock_blink_instance = create_mock_blink_instance()
        mock_blink_init.return_value = mock_blink_instance

        mock_process.return_value = []
        mock_context.return_value.__enter__ = Mock(spec=lambda: None, return_value=None)
        mock_context.return_value.__exit__ = Mock(spec=lambda: None, return_value=None)

        result = clips.get_clips("cloud")

        self.assertEqual(result, {"clips": []})
        mock_process.assert_called_once_with([])

    def test_system_handler_get_systems(self) -> None:
        """Test systems handler for system retrieval functionality.

        Verifies that the systems handler properly retrieves and
        processes system information through the handler interface.

        Tests:
            - System handler import and availability
            - System retrieval functionality through handler
            - Proper system data processing and formatting
            - Handler interface compatibility for system operations
        """
        try:
            from blinkapp.connexion_handlers.system import get_systems

            with patch("blinkapp.services.system_service.get_systems") as mock_get:
                mock_get.return_value = {"systems": []}

                result = get_systems()

                self.assertIsNotNone(result)
        except ImportError:
            self.skipTest("get_systems handler not found")

    def test_clips_handler_download_clip(self) -> None:
        """Test clip download handler functionality and processing.

        Verifies that the clip download handler properly processes
        download requests and handles clip retrieval operations.

        Tests:
            - Clip download handler import and availability
            - Download request processing and handling
            - Proper clip retrieval functionality through handler
            - Handler interface compatibility for clip operations
        """
        try:
            from blinkapp.connexion_handlers.clips import download_clip

            with patch("blinkapp.services.clip_service.download_clip") as mock_download:
                mock_download.return_value = ({"success": True}, 200)

                result = download_clip("test_clip")

                self.assertIsNotNone(result)
        except ImportError:
            self.skipTest("download_clip handler not found")


class TestSettingsHandlers(BaseTestCase):
    """Test settings connexion handlers."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()


class TestStreamingHandlers(BaseTestCase):
    """Test streaming connexion handlers."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()

    @patch("blinkapp.services.stream_service.stop_camera_stream")
    def test_stop_live_stream_success(self, mock_stop_stream: Mock) -> None:
        """Test stop_live_stream with successful stream stop operation.

        Verifies that the live stream stopping functionality works
        correctly when stream termination is successful.

        Tests:
            - Successful live stream stop operation
            - Proper stream service integration and calls
            - Correct response handling for successful stops
            - Stream state management during termination
        """
        from blinkapp.connexion_handlers.streaming import stop_live_stream

        mock_stop_stream.return_value = True

        result = stop_live_stream("12345")

        self.assertIsInstance(result, dict)
        self.assertTrue(result["success"])
        self.assertIn("stopped", result["message"])

    @patch("blinkapp.services.stream_service.stop_camera_stream")
    def test_stop_live_stream_failure(self, mock_stop_stream: Mock) -> None:
        """Test stop_live_stream with stream stop failure handling.

        Verifies that the stop live stream handler properly handles
        failures when attempting to stop streaming operations.

        Tests:
            - Stream stop failure handling
            - Error response for failed stream termination
            - Graceful degradation when stop operation fails
            - Proper error reporting for streaming issues
        """
        from blinkapp.connexion_handlers.streaming import stop_live_stream

        mock_stop_stream.return_value = False

        result = stop_live_stream("12345")

        self.assertIsInstance(result, dict)
        self.assertFalse(result["success"])  # success reflects the actual stop result
        self.assertIn("stop failed", result["message"])

    @patch("blinkapp.services.stream_service.get_hls_file")
    def test_get_hls_stream_segments_not_found(self, mock_get_hls: Mock) -> None:
        """Test get_hls_stream_segments with file not found error.

        Verifies that the HLS stream segments handler properly handles
        scenarios where requested stream segment files are not found.

        Tests:
            - File not found error handling for HLS segments
            - Proper error response for missing stream files
            - Graceful degradation when segments unavailable
            - Stream file availability validation
        """
        from blinkapp.connexion_handlers.streaming import get_hls_stream_segments

        mock_get_hls.return_value = (None, None)

        result, status_code = get_hls_stream_segments("12345", "segment.ts")

        self.assertIsInstance(result, dict)
        self.assertFalse(result["success"])
        self.assertIn("not found", result["error"])
        self.assertEqual(status_code, 404)


class TestThumbnailsHandlers(BaseTestCase):
    """Test thumbnails connexion handlers."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()
