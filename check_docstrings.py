#!/usr/bin/env python3
"""Standalone script to check for missing or incomplete Google-style docstrings."""

import sys

from tests.test_docstrings import (
    check_docstring_completeness,
    extract_functions_and_classes,
    get_all_python_files,
)


def main() -> None:
    """Main function to check all files for docstring completeness."""
    all_files = get_all_python_files()
    all_issues = []

    for file_path in all_files:
        items = extract_functions_and_classes(file_path)

        for name, line_no, node_type, docstring, has_params, has_return in items:
            # Skip private methods and special methods
            if name.startswith("_"):
                continue

            is_complete, docstring_issues = check_docstring_completeness(
                docstring, name, has_params, has_return
            )
            if not is_complete:
                issue = f"{file_path}:{line_no} - {node_type} '{name}': {', '.join(docstring_issues)}"
                all_issues.append(issue)

    if all_issues:
        print("Found docstring issues:")
        for issue in all_issues:
            print(f"  {issue}")
        print(f"\nTotal issues: {len(all_issues)}")
        print(
            "\nAll public functions and classes must have complete Google-style docstrings"
        )
        print("with Args sections (for functions with parameters) and Returns sections")
        print("(for functions with return types).")
        sys.exit(1)
    else:
        print("✅ All functions and classes have complete Google-style docstrings!")
        sys.exit(0)


if __name__ == "__main__":
    main()
