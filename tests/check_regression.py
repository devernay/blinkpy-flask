#!/usr/bin/env python3
"""Test regression checker.

This script compares current test results against the baseline to detect regressions.
"""

import subprocess
import sys
from pathlib import Path
from typing import TypedDict


def run_tests_and_get_results() -> list[str]:
    """Run tests and return sorted list of test results."""
    result = subprocess.run(
        ["python", "-m", "pytest", "--tb=no", "-v"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent,
    )

    # Extract test results (PASSED/FAILED/SKIPPED/ERROR lines)
    lines = result.stdout.split("\n")
    test_lines = [
        line
        for line in lines
        if any(status in line for status in ["PASSED", "FAILED", "SKIPPED", "ERROR"])
    ]

    return sorted(test_lines)


def load_baseline() -> list[str]:
    """Load baseline test results."""
    baseline_file = Path(__file__).parent / "test_baseline.txt"
    if not baseline_file.exists():
        print("❌ Baseline file not found. Run 'python update_baseline.py' first.")
        sys.exit(1)

    with open(baseline_file) as f:
        return [line.strip() for line in f if line.strip()]


class TestDiff(TypedDict):
    """Type definition for test regression analysis results."""

    regressions: list[str]
    new_passed: list[str]
    new_failed: list[str]
    new_skipped: list[str]
    missing_passed: list[str]
    missing_failed: list[str]
    total_current: int
    total_baseline: int


def compare_results(current: list[str], baseline: list[str]) -> TestDiff:
    """Compare current results with baseline and report differences."""
    current_set = set(current)
    baseline_set = set(baseline)

    # Find differences
    new_tests = current_set - baseline_set
    missing_tests = baseline_set - current_set

    # Separate by status
    new_passed = [t for t in new_tests if "PASSED" in t]
    new_failed = [t for t in new_tests if "FAILED" in t]
    new_skipped = [t for t in new_tests if "SKIPPED" in t]

    missing_passed = [t for t in missing_tests if "PASSED" in t]
    missing_failed = [t for t in missing_tests if "FAILED" in t]

    # Check for regressions (tests that were passing but now fail)
    regressions = []
    for test_line in current:
        if "FAILED" in test_line:
            test_name = test_line.split(" ")[0]
            # Check if this test was passing in baseline
            baseline_match = [b for b in baseline if test_name in b and "PASSED" in b]
            if baseline_match:
                regressions.append(test_line)

    return {
        "new_passed": new_passed,
        "new_failed": new_failed,
        "new_skipped": new_skipped,
        "missing_passed": missing_passed,
        "missing_failed": missing_failed,
        "regressions": regressions,
        "total_current": len(current),
        "total_baseline": len(baseline),
    }


def main() -> None:
    """Main regression check function."""
    print("🔍 Running regression check...")

    # Run current tests
    current_results = run_tests_and_get_results()

    # Load baseline
    baseline_results = load_baseline()

    # Compare results
    diff = compare_results(current_results, baseline_results)

    # Report results
    print("\n📊 Test Summary:")
    print(f"   Current: {diff['total_current']} tests")
    print(f"   Baseline: {diff['total_baseline']} tests")

    has_issues = False

    # Check for regressions (most important)
    if diff["regressions"]:
        print(f"\n❌ REGRESSIONS DETECTED ({len(diff['regressions'])} tests):")
        for test in diff["regressions"]:
            print(f"   {test}")
        has_issues = True

    # Check for new failures
    if diff["new_failed"]:
        print(f"\n❌ NEW FAILURES ({len(diff['new_failed'])} tests):")
        for test in diff["new_failed"]:
            print(f"   {test}")
        has_issues = True

    # Report new tests (informational)
    if diff["new_passed"]:
        print(f"\n✅ NEW PASSING TESTS ({len(diff['new_passed'])} tests):")
        for test in diff["new_passed"][:5]:  # Show first 5
            print(f"   {test}")
        if len(diff["new_passed"]) > 5:
            print(f"   ... and {len(diff['new_passed']) - 5} more")

    # Report missing tests (could be removed tests)
    if diff["missing_passed"]:
        print(f"\n⚠️  MISSING TESTS ({len(diff['missing_passed'])} tests):")
        for test in diff["missing_passed"][:5]:  # Show first 5
            print(f"   {test}")
        if len(diff["missing_passed"]) > 5:
            print(f"   ... and {len(diff['missing_passed']) - 5} more")

    # Final result
    if has_issues:
        print("\n❌ REGRESSION CHECK FAILED")
        print(
            "   Run 'python update_baseline.py' to update baseline if changes are expected"
        )
        sys.exit(1)
    elif diff["new_passed"] or diff["missing_passed"]:
        print("\n⚠️  TEST CHANGES DETECTED")
        print("   Run 'python update_baseline.py' to update baseline")
        sys.exit(0)
    else:
        print("\n✅ NO REGRESSIONS DETECTED")
        sys.exit(0)


if __name__ == "__main__":
    main()
