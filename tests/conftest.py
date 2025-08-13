"""Pytest configuration to ensure test_simple.py runs first and integration tests run last."""


def pytest_collection_modifyitems(config, items):
    """Reorder tests: test_simple.py first, integration tests last."""
    simple_tests = []
    integration_tests = []
    other_tests = []

    for item in items:
        if "test_simple.py" in str(item.fspath):
            simple_tests.append(item)
        elif (
            "Integration" in str(item.cls)
            if hasattr(item, "cls") and item.cls
            else False
        ):
            integration_tests.append(item)
        else:
            other_tests.append(item)

    # Order: simple first, others in middle, integration last
    items[:] = simple_tests + other_tests + integration_tests
