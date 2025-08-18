"""Simple tests for low-coverage services."""

from blinkapp.services.auth_service import (
    create_auth_config,
    extract_username_domain,
    is_valid_email_format,
    validate_credentials,
)
from blinkapp.services.stream_service import (
    generate_hls_url,
    parse_tcp_url,
    validate_camera_id,
    validate_tcp_url,
)
from blinkapp.services.utils_service import (
    format_battery_level,
    format_device_temperature,
)


def test_validate_credentials():
    """Test credential validation."""
    assert validate_credentials("user@test.com", "pass") is True
    assert validate_credentials("", "pass") is False
    assert validate_credentials("user@test.com", "") is False


def test_create_auth_config():
    """Test auth config creation."""
    result = create_auth_config("user@test.com", "pass")
    assert result == {"username": "user@test.com", "password": "pass"}


def test_extract_username_domain():
    """Test domain extraction."""
    assert extract_username_domain("user@test.com") == "test.com"
    assert extract_username_domain("invalid") == ""


def test_is_valid_email_format():
    """Test email validation."""
    assert is_valid_email_format("user@test.com") is True
    assert is_valid_email_format("invalid") is False


def test_validate_camera_id():
    """Test camera ID validation."""
    assert validate_camera_id("cam123") is True
    assert validate_camera_id("") is False


def test_validate_tcp_url():
    """Test TCP URL validation."""
    assert validate_tcp_url("tcp://192.168.1.1:8080") is True
    assert validate_tcp_url("invalid") is False


def test_parse_tcp_url():
    """Test TCP URL parsing."""
    result = parse_tcp_url("tcp://192.168.1.1:8080")
    assert result["protocol"] == "tcp"
    assert result["host"] == "192.168.1.1"
    assert result["port"] == "8080"


def test_generate_hls_url():
    """Test HLS URL generation."""
    result = generate_hls_url("cam123")
    assert "cam123" in result
    assert "playlist.m3u8" in result


def test_format_device_temperature():
    """Test temperature formatting."""
    assert format_device_temperature(72) == "72.0°F"
    assert format_device_temperature(None) == "N/A"


def test_format_battery_level():
    """Test battery level formatting."""
    assert format_battery_level(130) == "Good"
    assert format_battery_level(115) == "Fair"
    assert format_battery_level(105) == "Low"
