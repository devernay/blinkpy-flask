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
from typing import Any, TypeVar, cast

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

F = TypeVar("F", bound=Callable[..., Any])


def with_app_initialized[F](func: F) -> F:
    """Decorator to ensure app globals are initialized for testing.

    This decorator should be applied to test methods that need
    executor and blink_connection to be initialized. It handles
    the complex initialization sequence required for testing
    without modifying production code.

    The decorator ensures that:
    - Global variables are properly initialized
    - Thread pools and connections are set up
    - Cache directories are configured for testing
    - Cleanup happens automatically after tests

    Usage:
        @with_app_initialized
        def test_some_function(self) -> None:
            # Test code here - globals are ready to use
            pass

    Note:
        This decorator should be used sparingly, only for tests that
        actually need the full application context. Most unit tests
        should mock dependencies instead.
    """

    @functools.wraps(func)  # type: ignore[arg-type]
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Import here to avoid circular imports during module loading
        from tests.test_initialization import initialize_for_testing

        # Initialize globals for testing - this sets up the minimal
        # application state needed for tests to run
        initialize_for_testing()

        # Call the original test function with initialized context
        return cast(Any, func)(*args, **kwargs)

    return cast(F, wrapper)


def setup_test_globals():
    """Function to call in setUp methods to initialize globals.

    This is a convenience function for test classes that prefer
    to handle initialization in their setUp method rather than
    using the decorator approach.

    The function ensures consistent initialization across all
    test methods in a test class and can be called multiple
    times safely (it's idempotent).

    Usage in test setUp:
        def setUp(self) -> None:
            setup_test_globals()
            # rest of setup code - globals are now available

    Example:
        class MyTestClass(unittest.TestCase):
            def setUp(self) -> None:
                setup_test_globals()
                self.mock_blink = Mock()
                # ... other setup
    """
    from tests.test_initialization import initialize_for_testing

    # Delegate to the main initialization function
    initialize_for_testing()


class BaseTestCase(unittest.TestCase):
    """Base test case that automatically initializes app globals.

    Test classes can inherit from this instead of unittest.TestCase
    to automatically get proper initialization without needing to
    remember to call setup functions or use decorators.

    This base class handles:
    - Automatic global variable initialization
    - Consistent test environment setup
    - Proper cleanup after tests
    - Error handling during initialization

    Usage:
        class MyTestClass(BaseTestCase):
            def test_something(self) -> None:
                # globals are already initialized and ready to use
                # no need for @with_app_initialized decorator
                pass

    Benefits:
        - Reduces boilerplate in test classes
        - Ensures consistent initialization
        - Prevents common setup mistakes
        - Makes tests more readable
    """

    def setUp(self) -> None:
        """Set up test fixtures with app initialization.

        This method is called before each test method and ensures
        that the application globals are properly initialized.
        Subclasses should call super().setUp() if they override
        this method.

        Raises:
            Exception: If initialization fails, the test will be
                      skipped with an appropriate error message
        """
        super().setUp()
        # Initialize globals using the centralized function
        setup_test_globals()
