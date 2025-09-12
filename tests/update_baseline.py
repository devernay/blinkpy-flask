#!/usr/bin/env python3
"""Update test baseline.

This script runs the full test suite and updates the baseline file.
"""

import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Update the test baseline."""
    print("🔄 Updating test baseline...")

    # Run tests and capture results
    result = subprocess.run(
        ["python", "-m", "pytest", "--tb=no", "-v"],
        check=False,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent,
    )

    if result.returncode != 0:
        print("❌ Tests failed. Cannot update baseline with failing tests.")
        print("Fix failing tests first, then run this script again.")
        sys.exit(1)

    # Extract and sort test results
    lines = result.stdout.split("\n")
    test_lines = [
        line
        for line in lines
        if any(status in line for status in ["PASSED", "FAILED", "SKIPPED", "ERROR"])
    ]
    test_lines.sort()

    # Write to baseline file
    baseline_file = Path(__file__).parent / "test_baseline.txt"
    with open(baseline_file, "w") as f:
        f.writelines(line + "\n" for line in test_lines)

    print(f"✅ Baseline updated with {len(test_lines)} tests")
    print(f"   File: {baseline_file}")


if __name__ == "__main__":
    main()
