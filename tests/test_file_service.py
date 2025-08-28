"""Tests for file_service module."""

import unittest
from pathlib import Path
from unittest.mock import Mock

from blinkapp.services.file_service import (
    check_file_exists,
    create_directory_safely,
    read_file_safely,
    write_file_safely,
)


class TestFileService(unittest.TestCase):
    """Test file service functions."""

    def test_write_file_safely_success(self) -> None:
        """Test successful file write."""
        mock_writer = Mock(spec=object)
        result = write_file_safely(Path("/test"), b"data", mock_writer)
        self.assertTrue(result)
        mock_writer.assert_called_once_with(Path("/test"), b"data")

    def test_write_file_safely_default_writer(self) -> None:
        """Test write with default writer."""
        mock_path = Mock(spec=Path)
        result = write_file_safely(mock_path, b"data")
        self.assertTrue(result)
        mock_path.write_bytes.assert_called_once_with(b"data")

    def test_write_file_safely_error(self) -> None:
        """Test write with error."""
        mock_writer = Mock(side_effect=OSError("Write error"))
        result = write_file_safely(Path("/test"), b"data", mock_writer)
        self.assertFalse(result)

    def test_read_file_safely_success(self) -> None:
        """Test successful file read."""
        mock_reader = Mock(return_value=b"data")
        result = read_file_safely(Path("/test"), mock_reader)
        self.assertEqual(result, b"data")
        mock_reader.assert_called_once_with(Path("/test"))

    def test_read_file_safely_default_reader(self) -> None:
        """Test read with default reader."""
        mock_path = Mock(spec=Path)
        mock_path.read_bytes.return_value = b"data"
        result = read_file_safely(mock_path)
        self.assertEqual(result, b"data")
        mock_path.read_bytes.assert_called_once()

    def test_read_file_safely_error(self) -> None:
        """Test read with error."""
        mock_reader = Mock(side_effect=OSError("Read error"))
        result = read_file_safely(Path("/test"), mock_reader)
        self.assertIsNone(result)

    def test_check_file_exists_true(self) -> None:
        """Test file exists check returns true."""
        mock_checker = Mock(return_value=True)
        result = check_file_exists(Path("/test"), mock_checker)
        self.assertTrue(result)
        mock_checker.assert_called_once_with(Path("/test"))

    def test_check_file_exists_false(self) -> None:
        """Test file exists check returns false."""
        mock_checker = Mock(return_value=False)
        result = check_file_exists(Path("/test"), mock_checker)
        self.assertFalse(result)

    def test_check_file_exists_default_checker(self) -> None:
        """Test check with default checker."""
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        result = check_file_exists(mock_path)
        self.assertTrue(result)
        mock_path.exists.assert_called_once()

    def test_create_directory_safely_success(self) -> None:
        """Test successful directory creation."""
        mock_creator = Mock(spec=object)
        result = create_directory_safely(Path("/test"), mock_creator)
        self.assertTrue(result)
        mock_creator.assert_called_once_with(Path("/test"))

    def test_create_directory_safely_default_creator(self) -> None:
        """Test create with default creator."""
        mock_path = Mock(spec=Path)
        result = create_directory_safely(mock_path)
        self.assertTrue(result)
        mock_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_create_directory_safely_error(self) -> None:
        """Test create with error."""
        mock_creator = Mock(side_effect=OSError("Create error"))
        result = create_directory_safely(Path("/test"), mock_creator)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
