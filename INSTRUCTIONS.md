# Instructions for expanding test coverage

- never disable strict patching
- All Mocks, existing or newly created, must have a spec. The spec should be a proper type, not a list of members. Use mock factories (create_mock_*) for all types that have a factory. Add more parameters to factories if necessary.
- blink_connection should net be imported from blinkapp.services.blink_connection. we should ALWAYS use get_blink_connection(). Fix all tests that are using blink_connection
- many tests are patching ensure_blink_connection_initialized or ensure_blink_initialized, but shouldn't they use create_mock_blink_instance and create_mock_blink_connection to return a mock value? I'm just wondering
- there are factory functions for creating mocks in test_base.py, use them
- do not delete tests, even newly created ones. Work on them until they are fixed
- tests that don't expand coverage should not be added
- work on expanding coverage for the full test suite. Start with the module that has the highest number of lines uncovered, or from a module that looks like a low hanging fruit for testing. Carefully examine that module, and find a code path that would allow testing as many extra lines as possible. Try several times if needed . Don't add redundant tests. Work carefully on tests that will cover almost 100% of the code in that module. Then go to the next module.
- Keep tests well organized: All unit tests for a given Python module should go to the corresponding test class, named after the module, inside the test file named after the module directory. For example tests for the cache service should go in class TestCacheService in test_services.py. Tests should be sorted inside each class, and test classes should be sorted inside each test file. Integration tests go to test_app.py, but if test_app.py is too large you can split it into logical parts. DON'T REMOVE EXISTING TESTS! Merge them!
