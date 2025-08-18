"""Minimal tests for utils_service.py to improve coverage."""

from pathlib import Path
from unittest.mock import Mock, patch

from blinkapp.services.utils_service import (
    check_credentials_file_exists,
    create_device_data,
    handle_dump_system,
)


def test_create_device_data():
    """Test device data creation with correct signature."""
    mock_device = Mock()
    mock_device.name = "Test Camera"
    mock_device.device_type = "camera"
    mock_device.serial = "12345"
    mock_device.enabled = True
    mock_device.battery_voltage = 110
    mock_device.battery_state = "ok"
    mock_device.temperature = 72
    mock_device.wifi_strength = -50

    # Use correct function signature with integer timestamps
    from blinkapp.models.ids import CameraId

    result = create_device_data(
        mock_device, CameraId("cache_key"), 1609459200, 1609459100
    )

    assert result["name"] == "Test Camera"
    assert result["type"] == "camera"
    assert result["serial"] == "12345"
    assert result["enabled"] is True


def test_check_credentials_file_exists():
    """Test credentials file existence check."""
    mock_path = Mock(spec=Path)
    mock_path.exists.return_value = True

    result = check_credentials_file_exists(mock_path)
    assert result is True

    mock_path.exists.return_value = False
    result = check_credentials_file_exists(mock_path)
    assert result is False


def test_handle_dump_system_no_credentials():
    """Test dump system when no credentials exist."""
    mock_checker = Mock(return_value=False)

    with (
        patch("blinkapp.services.utils_service.initialize_cache_paths"),
        patch("blinkapp.services.utils_service.logger") as mock_logger,
        patch("sys.exit") as mock_exit,
    ):
        handle_dump_system(credentials_checker=mock_checker)

        assert mock_logger.error.called
        mock_exit.assert_called_with(1)
