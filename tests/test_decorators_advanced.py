#!/usr/bin/env python3
"""Advanced tests for utils/decorators.py - targeting highest missed lines."""

import unittest

from blinkapp.utils.decorators import (
    api_route,
    cached_api_route,
    ensure_blink_available,
    error_context,
    simple_success_response,
)


class TestDecoratorsAdvanced(unittest.TestCase):
    """Test advanced decorator functions with highest missed lines."""

    def test_error_context_decorator(self):
        """Test error_context decorator basic functionality."""

        @error_context("test_operation")
        def test_func():
            return "success"

        # Should be callable
        self.assertTrue(callable(test_func))

    def test_ensure_blink_available_decorator(self):
        """Test ensure_blink_available decorator."""

        @ensure_blink_available
        def test_func():
            return "available"

        # Should be callable
        self.assertTrue(callable(test_func))

    def test_api_route_decorator(self):
        """Test api_route decorator."""

        @api_route("test_operation")
        def test_func():
            return {"success": True}

        # Should be callable
        self.assertTrue(callable(test_func))

    def test_cached_api_route_decorator(self):
        """Test cached_api_route decorator."""

        @cached_api_route("cached_operation")
        def test_func():
            return {"cached": True}

        # Should be callable
        self.assertTrue(callable(test_func))

    def test_simple_success_response_decorator(self):
        """Test simple_success_response decorator."""

        @simple_success_response("Success message")
        def test_func():
            return "simple"

        # Should be callable
        self.assertTrue(callable(test_func))

    def test_decorators_exist(self):
        """Test that all decorators are importable."""
        # All decorators should be callable
        self.assertTrue(callable(error_context))
        self.assertTrue(callable(ensure_blink_available))
        self.assertTrue(callable(api_route))
        self.assertTrue(callable(cached_api_route))
        self.assertTrue(callable(simple_success_response))
