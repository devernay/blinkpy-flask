#!/usr/bin/env python3
"""Test Runner for Blink Camera Flask Web Interface

This script provides various options for running the test suite with coverage reporting.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and handle errors."""
    print(f"\n🔄 {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)

    try:
        # Change to tests directory to avoid import issues with blinkpy submodule
        tests_dir = Path(__file__).parent
        subprocess.run(cmd, check=True, capture_output=False, cwd=tests_dir)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run tests for Blink Camera Flask Web Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests with basic coverage
  python run_tests.py --coverage        # Run with detailed coverage report
  python run_tests.py --html            # Generate HTML coverage report

  python run_tests.py --verbose         # Run with verbose output
  python run_tests.py --specific core   # Run specific test suite
        """,
    )

    parser.add_argument(
        "--coverage", action="store_true", help="Generate detailed coverage report"
    )

    parser.add_argument(
        "--html", action="store_true", help="Generate HTML coverage report"
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Run tests with verbose output"
    )

    parser.add_argument(
        "--specific",
        choices=["core", "critical", "boost", "advanced", "all"],
        help="Run specific test suite",
    )

    parser.add_argument(
        "--no-warnings", action="store_true", help="Suppress warnings in test output"
    )

    args = parser.parse_args()

    # Base pytest command
    cmd = ["python", "-m", "pytest"]

    # Determine which tests to run
    if args.specific == "core":
        cmd.append("test_app.py")
    elif args.specific == "critical":
        cmd.append("test_critical_coverage.py")
    elif args.specific == "boost":
        cmd.append("test_coverage_boost.py")
    elif args.specific == "advanced":
        cmd.append("test_advanced_coverage.py")
    # else: Let pytest auto-discover all test_*.py files

    # Add coverage options
    if args.coverage or args.html:
        cmd.extend(["--cov=blinkapp", "--cov-report=term-missing"])
        if args.html:
            cmd.append("--cov-report=html")

    # Add verbosity options
    if args.verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    # Suppress warnings if requested
    if args.no_warnings:
        cmd.append("--disable-warnings")

    # Add traceback options
    cmd.append("--tb=short")

    # Print test configuration
    print("🧪 Blink Camera Flask Web Interface - Test Runner")
    print("=" * 60)
    print(f"Test Suite: {args.specific or 'All'}")
    print(f"Coverage: {'Yes' if args.coverage or args.html else 'No'}")
    print(f"HTML Report: {'Yes' if args.html else 'No'}")
    print(f"Verbose: {'Yes' if args.verbose else 'No'}")

    # Run the tests
    success = run_command(cmd, "Running test suite")

    if args.html and success:
        html_path = Path("htmlcov/index.html")
        if html_path.exists():
            print(f"\n📊 HTML coverage report generated: {html_path.absolute()}")
            print("Open in browser to view detailed coverage information")

    # Print summary
    print("\n" + "=" * 60)
    if success:
        print("🎉 Test execution completed successfully!")
        print("\nNext steps:")
        print("- Review coverage report for areas needing improvement")
        print("- Check failing tests and fix issues")
        print("- Add new tests for uncovered code paths")
    else:
        print("❌ Test execution completed with failures")
        print("\nTroubleshooting:")
        print("- Check test output for specific failure details")
        print("- Ensure all dependencies are installed")
        print("- Verify blinkapp.py is in the parent directory")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
