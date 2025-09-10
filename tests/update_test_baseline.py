#!/usr/bin/env python3
"""Update test baseline with current passing tests."""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Update baseline with current test results."""
    print("🔄 Updating test baseline...")

    # Get project root (parent of tests directory)
    project_root = Path(__file__).parent.parent
    tests_dir_name = Path(__file__).parent.name

    # Run tests from project root and capture passing test names
    result = subprocess.run(
        ["python", "-m", "pytest", "--tb=no", "-v", "--no-cov"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )

    # Extract passing test names
    passing_tests = []
    for line in result.stdout.split("\n"):
        if "PASSED" in line:
            test_name = line.split()[0]
            # Remove tests directory prefix if present
            prefix = f"{tests_dir_name}/"
            if test_name.startswith(prefix):
                test_name = test_name[len(prefix) :]
            passing_tests.append(test_name)

    if not passing_tests:
        print("❌ No passing tests found")
        return 1

    # Sort tests for consistent baseline
    passing_tests.sort()

    # Write baseline file
    baseline_file = Path(__file__).parent / "test_results_baseline.txt"
    with open(baseline_file, "w") as f:
        for test in passing_tests:
            f.write(f"{test}\n")

    print(f"✅ Updated baseline with {len(passing_tests)} passing tests")
    print(f"📁 Baseline saved to: {baseline_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
