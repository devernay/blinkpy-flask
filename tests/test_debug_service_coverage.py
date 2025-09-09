"""Test coverage for debug_service.py functions."""

from unittest.mock import Mock, patch

from blinkapp.services import debug_service

from .test_base import (
    create_mock_blink_connection,
    create_mock_blink_instance,
    create_mock_camera,
    create_mock_path,
    create_mock_sync,
)


class TestCheckCredentialsFileExists:
    """Test check_credentials_file_exists function."""

    def test_check_credentials_file_exists_true(self):
        """Test credentials file exists returns True."""
        mock_path = create_mock_path("mock_path")
        mock_path.exists.return_value = True

        result = debug_service.check_credentials_file_exists(mock_path)

        assert result is True

    def test_check_credentials_file_exists_false(self):
        """Test credentials file does not exist returns False."""
        mock_path = create_mock_path("mock_path")
        mock_path.exists.return_value = False

        result = debug_service.check_credentials_file_exists(mock_path)

        assert result is False


class TestDumpCloudVideos:
    """Test dump_cloud_videos function."""

    def test_dump_cloud_videos_empty_list(self):
        """Test dumping empty video list."""
        with patch("blinkapp.services.debug_service.logger") as mock_logger:
            debug_service.dump_cloud_videos([])

            mock_logger.info.assert_called_with("=== CLOUD VIDEOS ===")

    def test_dump_cloud_videos_with_videos(self):
        """Test dumping video list with videos."""
        videos: list[dict[str, object]] = [
            {"id": "123", "name": "video1"},
            {"id": "456", "name": "video2"},
        ]

        with patch("blinkapp.services.debug_service.logger") as mock_logger:
            debug_service.dump_cloud_videos(videos)

            assert mock_logger.info.call_count == 3  # Header + 2 videos


class TestDumpBlinkSystemInfo:
    """Test dump_blink_system_info function."""

    def test_dump_blink_system_info_not_available(self):
        """Test dump when blink system not available."""
        mock_blink = create_mock_blink_instance(available=False)

        with patch(
            "blinkapp.services.blink_service.ensure_blink_initialized",
            return_value=mock_blink,
        ):
            with patch("blinkapp.logger") as mock_logger:
                debug_service.dump_blink_system_info()

                mock_logger.error.assert_called_with("Blink system not available")

    def test_dump_blink_system_info_no_blink(self):
        """Test dump when no blink instance."""
        with patch(
            "blinkapp.services.blink_service.ensure_blink_initialized",
            return_value=None,
        ):
            with patch("blinkapp.logger") as mock_logger:
                debug_service.dump_blink_system_info()

                mock_logger.error.assert_called_with("Blink system not available")

    def test_dump_blink_system_info_success(self):
        """Test successful system info dump."""
        sync_mock = create_mock_sync(network_id=12345, armed=True)
        sync_mock.status = "online"
        cameras = {"cam1": create_mock_camera(name="camera1")}
        mock_blink = create_mock_blink_instance(available=True, cameras=cameras)
        mock_blink.account_id = "test_account"
        mock_blink.homescreen = {"test": "data"}
        mock_blink.sync = {"sync1": sync_mock}

        with patch(
            "blinkapp.services.blink_service.ensure_blink_initialized",
            return_value=mock_blink,
        ):
            with patch("blinkapp.logger"):
                debug_service.dump_blink_system_info()


class TestHandleDumpSystem:
    """Test handle_dump_system function."""

    def test_handle_dump_system_no_credentials(self):
        """Test dump system with no credentials file."""
        mock_checker = Mock(spec=callable, return_value=False)

        with patch("blinkapp.initialize_cache_paths"):
            with patch("blinkapp.CREDENTIALS_FILE", "/test/path"):
                with patch(
                    "blinkapp.services.blink_connection.get_blink_connection",
                    return_value=create_mock_blink_connection(),
                ):
                    with patch(
                        "blinkapp.services.debug_service.ensure_blink_initialized",
                        return_value=create_mock_blink_instance(),
                    ):
                        with patch(
                            "blinkapp.services.blink_service.ensure_blink_connection_initialized",
                            return_value=create_mock_blink_connection(),
                        ):
                            with patch("blinkapp.logger") as mock_logger:
                                with patch("sys.exit") as mock_exit:
                                    debug_service.handle_dump_system(mock_checker)

                                    mock_logger.error.assert_called_with(
                                        "System dump error: Blink not initialized. Call initialize_blink() first."
                                    )
                                    mock_exit.assert_called_with(1)

    def test_handle_dump_system_blink_init_error(self):
        """Test dump system with blink initialization error."""
        mock_checker = Mock(spec=callable, return_value=True)

        with patch("blinkapp.initialize_cache_paths"):
            with patch("blinkapp.CREDENTIALS_FILE", "/test/path"):
                with patch(
                    "blinkapp.services.blink_connection.get_blink_connection",
                    return_value=create_mock_blink_connection(),
                ):
                    with patch(
                        "blinkapp.services.debug_service.ensure_blink_initialized",
                        return_value=None,
                    ):
                        with patch(
                            "blinkapp.services.blink_service.ensure_blink_connection_initialized",
                            return_value=create_mock_blink_connection(),
                        ):
                            with patch("blinkapp.logger") as mock_logger:
                                with patch("sys.exit") as mock_exit:
                                    debug_service.handle_dump_system(mock_checker)

                                    mock_logger.error.assert_called_with(
                                        "Failed to load Blink system from saved credentials."
                                    )
                                    mock_exit.assert_called_with(1)
