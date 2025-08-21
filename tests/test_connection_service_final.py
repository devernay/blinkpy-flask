#!/usr/bin/env python3
"""Final targeted tests for services/connection_service.py - covering missed lines."""

import unittest

from blinkapp.services.connection_service import ensure_executor_initialized


class TestConnectionServiceFinal(unittest.TestCase):
    """Test remaining uncovered connection service functions."""

    def test_ensure_executor_initialized_error(self):
        """Test ensure_executor_initialized raises error when not initialized."""
        # Reset executor to None
        import blinkapp.services.connection_service

        blinkapp.services.connection_service.executor = None

        with self.assertRaises(RuntimeError) as context:
            ensure_executor_initialized()

        self.assertIn("Executor not initialized", str(context.exception))
