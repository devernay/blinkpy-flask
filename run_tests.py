#!/usr/bin/env python3
"""Test runner script with coverage reporting.

Runs the complete test suite and generates coverage reports.
Usage: python run_tests.py [--coverage] [--html]
"""

import argparse
import os
import subprocess
import sys


def run_tests(with_coverage=False, html_report=False):
    """Run tests with optional coverage reporting."""

    # Add current directory to Python path
    sys.path.insert(0, os.path.dirname(__file__))

    if with_coverage:
        try:
            import coverage
        except ImportError:
            print("Coverage package not installed. Install with: pip install coverage")
            return False

        # Start coverage
        cov = coverage.Coverage()
        cov.start()

        # Import and run tests
        try:
            import unittest

            import test_app

            # Create test suite
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(test_app)

            # Run tests
            runner = unittest.TextTestRunner(verbosity=2)
            result = runner.run(suite)

            # Stop coverage and save
            cov.stop()
            cov.save()

            # Generate reports
            print("\n" + "=" * 50)
            print("COVERAGE REPORT")
            print("=" * 50)
            cov.report(show_missing=True)

            if html_report:
                cov.html_report(directory="htmlcov")
                print("\nHTML coverage report generated in htmlcov/index.html")

            return result.wasSuccessful()

        except Exception as e:
            print(f"Error running tests with coverage: {e}")
            return False
    else:
        # Run tests without coverage
        try:
            result = subprocess.run(
                [sys.executable, "-m", "unittest", "test_app", "-v"],
                cwd=os.path.dirname(__file__),
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Error running tests: {e}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run Blink Flask application tests")
    parser.add_argument(
        "--coverage", action="store_true", help="Run tests with coverage reporting"
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML coverage report (requires --coverage)",
    )

    args = parser.parse_args()

    if args.html and not args.coverage:
        print("--html requires --coverage")
        sys.exit(1)

    print("Running Blink Flask Application Tests")
    print("=" * 40)

    success = run_tests(with_coverage=args.coverage, html_report=args.html)

    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
