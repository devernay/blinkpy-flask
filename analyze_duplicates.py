#!/usr/bin/env python3
"""Analyze duplicate test methods across test files."""

import re
from collections import defaultdict
from pathlib import Path


def extract_test_methods(file_path):
    """Extract test methods from a Python file."""
    with open(file_path) as f:
        content = f.read()

    # Find all test methods with their line numbers and content
    methods = []
    lines = content.split("\n")

    for i, line in enumerate(lines):
        if re.match(r"\s*def test_", line):
            method_name = re.search(r"def (test_\w+)", line).group(1)

            # Find the end of the method (next def or class, or end of file)
            method_lines = [line]
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                if re.match(r"\s*def ", next_line) or re.match(r"\s*class ", next_line):
                    break
                method_lines.append(next_line)
                j += 1

            methods.append(
                {
                    "name": method_name,
                    "line_start": i + 1,
                    "line_count": len(method_lines),
                    "content": "\n".join(method_lines),
                }
            )

    return methods


def main():
    test_dir = Path("tests")
    all_methods = defaultdict(list)

    # Collect all test methods from all files
    for test_file in test_dir.glob("test_*.py"):
        methods = extract_test_methods(test_file)
        for method in methods:
            all_methods[method["name"]].append(
                {"file": str(test_file), "method": method}
            )

    # Find duplicates
    duplicates = {
        name: instances for name, instances in all_methods.items() if len(instances) > 1
    }

    print(f"Found {len(duplicates)} duplicate test method names:")
    print()

    for method_name, instances in sorted(duplicates.items()):
        print(f"=== {method_name} ===")

        # Sort by line count (coverage) descending
        instances.sort(key=lambda x: x["method"]["line_count"], reverse=True)

        for i, instance in enumerate(instances):
            file_name = instance["file"]
            method = instance["method"]
            print(
                f"  {i + 1}. {file_name}:{method['line_start']} ({method['line_count']} lines)"
            )

            # Show first few lines of content for comparison
            content_lines = method["content"].split("\n")[:5]
            for line in content_lines:
                if line.strip():
                    print(f"     {line}")
            if len(method["content"].split("\n")) > 5:
                print("     ...")

        print(f"  KEEP: {instances[0]['file']} (best coverage)")
        print()


if __name__ == "__main__":
    main()
