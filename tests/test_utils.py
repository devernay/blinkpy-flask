#!/usr/bin/env python3
"""Test utilities for Blink Flask application tests.

Provides decorators and helper functions to properly initialize
the application for testing without modifying production code.
"""

import functools
import os
import sys
import unittest
from collections.abc import Callable
from typing import Any, TypeVar

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

F = TypeVar("F", bound=Callable[..., Any])


def with_app_initialized(func: F) -> F:
    """Decorator to ensure app globals are initialized for testing.

    This decorator should be applied to test methods that need
    executor and blink_connection to be initialized.

    Usage:
        @with_app_initialized
        def test_some_function(self) -> None:
            # Test code here
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Import here to avoid circular imports
        from app import initialize_for_testing

        # Initialize globals for testing
        initialize_for_testing()

        # Call the original test function
        return func(*args, **kwargs)

    return wrapper


def setup_test_globals():
    """Function to call in setUp methods to initialize globals.

    Usage in test setUp:
        def setUp(self) -> None:
            setup_test_globals()
            # rest of setup code
    """
    from app import initialize_for_testing

    initialize_for_testing()


class BaseTestCase(unittest.TestCase):
    """Base test case that automatically initializes app globals.

    Test classes can inherit from this instead of unittest.TestCase
    to automatically get proper initialization.

    Usage:
        class MyTestClass(BaseTestCase):
            def test_something(self) -> None:
                # globals are already initialized
                pass
    """

    def setUp(self) -> None:
        """Set up test fixtures with app initialization."""
        super().setUp()
        setup_test_globals()
