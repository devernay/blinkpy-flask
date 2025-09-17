"""Test module to ensure all functions and classes have complete Google-style docstrings."""

import ast
import os

import pytest


def check_docstring_completeness(
    docstring: str, func_name: str, has_params: bool, has_return: bool
) -> tuple[bool, list[str]]:
    """Check if a docstring follows Google style and is complete.

    Args:
        docstring: The docstring text to check.
        func_name: Name of the function being checked.
        has_params: Whether the function has parameters.
        has_return: Whether the function has a return type annotation.

    Returns:
        Tuple[bool, List[str]]: (is_complete, list_of_issues)
    """
    if not docstring:
        return False, ["Missing docstring"]

    issues = []
    lines = docstring.strip().split("\n")

    # Check for basic structure
    if len(lines) < 1:
        issues.append("Empty docstring")
        return False, issues

    # First line should be a brief description
    if not lines[0].strip():
        issues.append("Missing brief description")

    # Check for Google-style sections
    docstring_lower = docstring.lower()

    # Check for Args section if function has parameters
    if has_params and "args:" not in docstring_lower:
        issues.append("Missing Args section for function with parameters")

    # Check for Returns section if function has return annotation (and not None)
    if (
        has_return
        and "returns:" not in docstring_lower
        and "return:" not in docstring_lower
    ):
        issues.append("Missing Returns section for function with return type")

    # Check for proper formatting
    if len(lines) > 1:
        # Should have blank line after summary if multi-line
        if lines[1].strip() != "":
            issues.append("Missing blank line after summary")

    return len(issues) == 0, issues


def extract_functions_and_classes(
    file_path: str,
) -> list[tuple[str, int, str, str, bool, bool]]:
    """Extract all functions and classes with their docstrings and metadata.

    Args:
        file_path: Path to the Python file to analyze.

    Returns:
        List of tuples: (name, line_no, node_type, docstring, has_params, has_return)
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        items = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                name = node.name
                line_no = node.lineno
                node_type = "class" if isinstance(node, ast.ClassDef) else "function"

                # Check if function has parameters (excluding self/cls)
                has_params = False
                has_return = False

                if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                    # Check parameters (excluding self/cls)
                    params = [arg.arg for arg in node.args.args]
                    if params and params[0] in ["self", "cls"]:
                        params = params[1:]
                    has_params = len(params) > 0

                    # Check return annotation
                    if node.returns:
                        # Check if return type is not None
                        if not (
                            isinstance(node.returns, ast.Constant)
                            and node.returns.value is None
                        ):
                            has_return = True

                # Get docstring
                docstring = ""
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    docstring = node.body[0].value.value

                items.append(
                    (name, line_no, node_type, docstring, has_params, has_return)
                )

        return items
    except Exception as e:
        pytest.fail(f"Error parsing {file_path}: {e}")


def get_all_python_files() -> list[str]:
    """Get all Python files in main app and test_base.py.

    Returns:
        List[str]: List of Python file paths to check.
    """
    # Check main app files
    app_files = []
    for root, dirs, files in os.walk("./blinkapp"):
        for file in files:
            if file.endswith(".py"):
                app_files.append(os.path.join(root, file))

    # Add test_base.py
    test_files = ["./tests/test_base.py"]

    return sorted(app_files) + [f for f in test_files if os.path.exists(f)]


class TestDocstrings:
    """Test class for docstring completeness."""

    def test_all_functions_have_complete_docstrings(self) -> None:
        """Test that all public functions and classes have complete Google-style docstrings.

        Verifies that the codebase maintains high documentation standards
        by ensuring all public functions and classes include comprehensive
        Google-style docstrings with proper formatting and content.

        Tests:
            - Public function docstring presence and completeness
            - Google-style format compliance (Args, Returns, etc.)
            - Class docstring availability and quality
            - Documentation coverage across modules
        """
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
            issue_summary = "\n".join(f"  {issue}" for issue in all_issues)
            pytest.fail(
                f"Found {len(all_issues)} docstring issues:\n{issue_summary}\n\n"
                + "All public functions and classes must have complete Google-style docstrings "
                + "with Args sections (for functions with parameters) and Returns sections "
                + "(for functions with return types)."
            )

    def test_docstring_examples(self) -> None:
        """Test that demonstrates proper Google-style docstring format.

        Provides examples and validation of proper Google-style docstring
        formatting to ensure consistency across the codebase.

        Tests:
            - Google-style docstring format examples
            - Proper section formatting (Args, Returns, Raises)
            - Docstring structure validation
            - Format consistency verification
        """
        # This test serves as documentation for the expected format

        def good_example(param1: str, param2: int = 5) -> bool:
            """Brief description of what the function does.

            Longer description if needed, explaining the function's purpose,
            behavior, or important details.

            Args:
                param1: Description of the first parameter.
                param2: Description of the second parameter (default: 5).

            Returns:
                bool: Description of what the function returns.

            Raises:
                ValueError: When param1 is empty.
            """
            if not param1:
                raise ValueError("param1 cannot be empty")
            return len(param1) > param2

        # This function should pass docstring validation
        docstring = good_example.__doc__
        if docstring is not None:
            is_complete, issues = check_docstring_completeness(
                docstring, "good_example", True, True
            )
            assert is_complete, f"Example docstring should be complete: {issues}"
