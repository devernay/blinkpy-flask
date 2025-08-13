#!/usr/bin/env python3
"""Update test baseline with current passing tests."""

import subprocess
import sys
from pathlib import Path


def main():
    """Update baseline with current test results."""
    print("🔄 Updating test baseline...")

    # Run tests and capture passing test names
    result = subprocess.run(
        ["python", "-m", "pytest", "--tb=no", "-v"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent,
    )

    # Extract passing test names
    passing_tests = []
    for line in result.stdout.split("\n"):
        if "PASSED" in line:
            test_name = line.split()[0]
            passing_tests.append(test_name)

    if not passing_tests:
        print("❌ No passing tests found")
        return 1

    # Sort and write to baseline file
    passing_tests.sort()
    baseline_file = Path(__file__).parent / "test_results_baseline.txt"

    with open(baseline_file, "w") as f:
        for test in passing_tests:
            f.write(f"{test}\n")

    print(f"✅ Baseline updated with {len(passing_tests)} tests")
    print(f"   File: {baseline_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
