"""Tests for log viewing functionality."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from blinkapp import app
from blinkapp.connexion_handlers import logs
from tests.test_base import BaseTestCase


class TestLogsConnexionHandler(unittest.TestCase):
    """Test the logs connexion handler."""

    def test_get_logs_no_file(self):
        """Test get_logs when log file doesn't exist.

        Tests:
            - Returns empty logs and modules when log file is missing
            - Handles missing log file gracefully
        """
        with patch(
            "blinkapp.connexion_handlers.logs.Config.get_log_file_path"
        ) as mock_path:
            mock_path.return_value = "/nonexistent/path"

            result = logs.get_logs()

            self.assertEqual(result, {"logs": [], "modules": []})

    def test_get_logs_with_data(self):
        """Test get_logs with actual log data.

        Tests:
            - Parses log entries correctly
            - Extracts modules from log entries
            - Applies level filtering
            - Applies module filtering
        """
        log_content = """2025-01-20 10:30:00,123 - blinkapp.test - INFO - Test info message
2025-01-20 10:30:01,456 - blinkapp.other - DEBUG - Test debug message
2025-01-20 10:30:02,789 - blinkapp.test - ERROR - Test error message
"""

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            f.write(log_content)
            temp_path = f.name

        try:
            with patch(
                "blinkapp.connexion_handlers.logs.Config.get_log_file_path"
            ) as mock_path:
                mock_path.return_value = temp_path

                # Test default filtering (DEBUG level, all modules)
                result = logs.get_logs()

                self.assertEqual(len(result["logs"]), 3)
                self.assertEqual(
                    set(result["modules"]), {"blinkapp.test", "blinkapp.other"}
                )

                # Test level filtering
                result = logs.get_logs(level="INFO")
                self.assertEqual(len(result["logs"]), 2)  # INFO and ERROR

                # Test module filtering
                result = logs.get_logs(module="blinkapp.test")
                self.assertEqual(len(result["logs"]), 2)  # Only blinkapp.test entries

        finally:
            Path(temp_path).unlink()

    def test_get_logs_read_error(self):
        """Test get_logs when file read fails.

        Tests:
            - Returns error response when file cannot be read
            - Handles file read exceptions gracefully
        """
        with patch(
            "blinkapp.connexion_handlers.logs.Config.get_log_file_path"
        ) as mock_path:
            mock_path.return_value = "/dev/null"

            with patch("builtins.open", side_effect=PermissionError("Access denied")):
                result, status = logs.get_logs()

                self.assertEqual(status, 500)
                self.assertIn("error", result)
                self.assertIn("Access denied", result["error"])

    def test_get_logs_multiline_entries(self):
        """Test get_logs with multi-line log entries (stack traces).

        Tests:
            - Handles multi-line log entries correctly
            - Appends continuation lines to previous entry
        """
        log_content = """2025-01-20 10:30:00,123 - blinkapp.test - ERROR - Exception occurred
Traceback (most recent call last):
  File "test.py", line 1, in <module>
    raise ValueError("test error")
ValueError: test error
2025-01-20 10:30:01,456 - blinkapp.other - INFO - Normal message
"""

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            f.write(log_content)
            temp_path = f.name

        try:
            with patch(
                "blinkapp.connexion_handlers.logs.Config.get_log_file_path"
            ) as mock_path:
                mock_path.return_value = temp_path

                result = logs.get_logs()

                self.assertEqual(len(result["logs"]), 2)
                # First entry should contain the stack trace
                self.assertIn("Traceback", result["logs"][0]["message"])
                self.assertIn("ValueError", result["logs"][0]["message"])

        finally:
            Path(temp_path).unlink()


class TestLogsRoutes(BaseTestCase):
    """Test the logs Flask routes."""

    def setUp(self) -> None:
        """Set up test client."""
        super().setUp()
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_log_viewer_route(self):
        """Test the log viewer page route.

        Tests:
            - Returns 200 status for /logs route
            - Renders logs.html template
        """
        response = self.client.get("/logs")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Application Logs", response.data)
        self.assertIn(b"log-container", response.data)

    def test_api_log_route(self):
        """Test the API log endpoint.

        Tests:
            - Returns JSON response for /api/log
            - Accepts level and module parameters
            - Returns proper structure
        """
        # Test without parameters
        response = self.client.get("/api/log")
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertIn("logs", data)
        self.assertIn("modules", data)
        self.assertIsInstance(data["logs"], list)
        self.assertIsInstance(data["modules"], list)

    def test_api_log_with_parameters(self):
        """Test the API log endpoint with filtering parameters.

        Tests:
            - Accepts level parameter
            - Accepts module parameter
            - Returns filtered results
        """
        response = self.client.get("/api/log?level=INFO&module=test")
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertIn("logs", data)
        self.assertIn("modules", data)


if __name__ == "__main__":
    unittest.main()
