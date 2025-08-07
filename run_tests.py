#!/usr/bin/env python3
"""Test runner script with coverage reporting.

Runs the complete test suite and generates coverage reports.
Usage: python run_tests.py [--coverage] [--html]
"""

import argparse
import logging
import os
import subprocess
import sys

# Set up console logging for test runner
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def run_tests(with_coverage: bool = False, html_report: bool = False) -> bool:
    """Run tests with optional coverage reporting."""

    # Add current directory to Python path
    sys.path.insert(0, os.path.dirname(__file__))

    if with_coverage:
        import coverage

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
            test_result = runner.run(suite)

            # Stop coverage and save
            cov.stop()
            cov.save()

            # Generate reports
            logger.info("\n" + "=" * 50)
            logger.info("COVERAGE REPORT")
            logger.info("=" * 50)
            cov.report(show_missing=True)

            if html_report:
                cov.html_report(directory="htmlcov")
                logger.info("\nHTML coverage report generated in htmlcov/index.html")

            return test_result.wasSuccessful()

        except Exception as e:
            logger.error(f"Error running tests with coverage: {e}")
            return False
    else:
        # Run tests without coverage
        try:
            subprocess_result = subprocess.run(
                [sys.executable, "-m", "unittest", "test_app", "-v"],
                cwd=os.path.dirname(__file__),
            )
            return subprocess_result.returncode == 0
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return False


def main() -> None:
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
        logger.error("--html requires --coverage")
        sys.exit(1)

    logger.info("Running Blink Flask Application Tests")
    logger.info("=" * 40)

    success = run_tests(with_coverage=args.coverage, html_report=args.html)

    if success:
        logger.info("\n✅ All tests passed!")
        sys.exit(0)
    else:
        logger.error("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
