# Instructions for expanding test coverage

- Never disable strict patching
- All Mocks, existing or newly created, must have a spec. The spec should be a proper type, not a list of members. Use mock factories (create_mock_*) for all types that have a factory. Add more parameters to factories if necessary. Mocks with no specs are not necessarily Mocks with no parameters (i.e. "Mock()") or mocks with a generic spec ("Mock(spec=object)").
- There are factory functions for creating mocks in test_base.py, use them.
- Do not delete tests, even newly created ones. Work on them until they are fixed.
- tests that don't expand coverage should not be added
- Work on expanding coverage for the full test suite. Start with the module that has the highest number of lines uncovered, or from a module that looks like a low hanging fruit for testing. Carefully examine that module, and find a code path that would allow testing as many extra lines as possible. Try several times if needed . Don't add redundant tests. Work carefully on tests that will cover almost 100% of the code in that module. Then go to the next module.
- Keep tests well organized: All unit tests for a given Python module should go to the corresponding test class, named after the module, inside the test file named after the module directory. For example tests for the cache service should go in class TestCacheService in test_services.py. Tests should be sorted inside each class, and test classes should be sorted inside each test file. Integration tests go to test_app.py, but if test_app.py is too large you can split it into logical parts. DON'T REMOVE EXISTING TESTS! Merge them!
- Are there more tests to reorganize? Be systematic in building test classes and test files for unit tests: one file per directory, one class per file. For example, tests for functions in blinkapp/services/blink_validators.py go to tests/test_services.py in class TestBlinkValidators. Be systematic: check that each file has its class and each class corresponds to a file.
- Move each unit test to the corresponding test class in the right test file. Work test by test, one at a time. Each time you move a test, test it before and after moving.
