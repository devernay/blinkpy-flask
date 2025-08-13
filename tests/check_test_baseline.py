#!/usr/bin/env python3
"""Check current test results against baseline."""

import subprocess
import sys
from pathlib import Path


def get_current_passing_tests():
    """Get list of currently passing tests."""
    result = subprocess.run(
        ["python", "-m", "pytest", "--tb=no", "-v"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent,
    )

    passing_tests = []
    for line in result.stdout.split("\n"):
        if "PASSED" in line:
            test_name = line.split()[0]
            passing_tests.append(test_name)

    return sorted(passing_tests)


def load_baseline():
    """Load baseline test names."""
    baseline_file = Path(__file__).parent / "test_results_baseline.txt"
    if not baseline_file.exists():
        return []

    with open(baseline_file) as f:
        return [line.strip() for line in f if line.strip()]


def main():
    """Compare current tests against baseline."""
    print("🔍 Checking test results against baseline...")

    current_tests = set(get_current_passing_tests())
    baseline_tests = set(load_baseline())

    print(f"📊 Current: {len(current_tests)} passing tests")
    print(f"📊 Baseline: {len(baseline_tests)} tests")

    # Check for regressions (tests that were passing but now fail)
    regressions = baseline_tests - current_tests
    if regressions:
        print(f"❌ REGRESSIONS DETECTED: {len(regressions)} tests now failing:")
        for test in sorted(regressions):
            print(f"   - {test}")
        return 1

    # Check for new tests
    new_tests = current_tests - baseline_tests
    if new_tests:
        print(f"✅ NEW TESTS: {len(new_tests)} tests added:")
        for test in sorted(new_tests):
            print(f"   + {test}")
        print("💡 Run 'python update_test_baseline.py' to update baseline")

    if not regressions and not new_tests:
        print("✅ NO CHANGES: All tests match baseline")

    return 0


if __name__ == "__main__":
    sys.exit(main())
