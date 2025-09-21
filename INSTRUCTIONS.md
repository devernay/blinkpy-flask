# Instructions for expanding test coverage

- Never disable strict patching
- All Mocks, existing or newly created, must have a spec. The spec should be a proper type, not a list of members. Use mock factories (create_mock_*) for all types that have a factory. Add more parameters to factories if necessary. Mocks with no specs are not necessarily Mocks with no parameters (i.e. "Mock()") or mocks with a generic spec ("Mock(spec=object)").
- There are factory functions for creating mocks in test_base.py, use them.
- Do not delete tests, even newly created ones. Work on them until they are fixed.
- tests that don't expand coverage should not be added
- some tests may require running in a non-isolated environment to test the original implementation rather than the test-isolated mock versions of some functions. See doctring at the top of test_services_no_isolation.py for a full explanation.
- Work on expanding coverage for the full test suite. Start with the module that has the highest number of lines uncovered, or from a module that looks like a low hanging fruit for testing. Carefully examine that module, and find a code path that would allow testing as many extra lines as possible. Try several times if needed . Don't add redundant tests. Work carefully on tests that will cover almost 100% of the code in that module. Then go to the next module.
- Keep tests well organized: All unit tests for a given Python module should go to the corresponding test class, named after the module, inside the test file named after the module directory. For example tests for the cache service should go in class TestCacheService in test_services.py. Tests should be sorted inside each class, and test classes should be sorted inside each test file. Integration tests go to test_app.py, but if test_app.py is too large you can split it into logical parts. DON'T REMOVE EXISTING TESTS! Merge them!
- Are there more tests to reorganize? Be systematic in building test classes and test files for unit tests: one file per directory, one class per file. For example, tests for functions in blinkapp/services/blink_validators.py go to tests/test_services.py in class TestBlinkValidators. Be systematic: check that each file has its class and each class corresponds to a file.
- Move each unit test to the corresponding test class in the right test file. Work test by test, one at a time. Each time you move a test, test it before and after moving.

Append to tests/test_verification_log.md a list of tests that have not yet been verified, and explain what it is. If you don't know the exact list, you can check the docstrings: tests with no docstring of with a one-line docstring were definitely not verified. This line will be updated as we verify more tests (explain that in tests/test_verification_log.md)

Continue checking that tests are properly named, do what they claim, have full google-style docstrings, and update test_verification_log.md (which contains the list of already fixed tests, among other things). Use mock factories from test_base.py and avoid unspec'ed Mocks. If there is already a full docstring, then check that it's consistent with the function implementation and name, and don't modify it in this case: it was probably fixed in a previous batch. Process all the remaining tests listed in section "Current Unverified Tests" of tests/test_verification_log.md. Update the file, once done. You must read each test and make sure you understood it. Each docstring must be specific. If you write a script for batch replacement, make sure each test gets a distinctive docstring. Run ruff check after running the script.

"Mock object for testing" is not very specific to describe mock arguments, please be more specific, for example by saying which class it mocks.

Did you finish testing that all tests are properly named, and that they have a full google-style docstring which is specific enough and describes the test?

Do all test docstrings have a "Tests:" section? If not, report the list of test missing the "Tests:" section in tests/test_verification_log.md, and we will work on fixing those docstrings. Also check that no test has "double docstrings" (two docstrings in a row, which are probably the result of buggy modifications). Merge "double docstrings" into a single one by reading the two texts and creating a single one (don't just concatenate them).

Many "Tests:" section just say "Test functionality and behavior", which is not specific enough. fix this.

# Instructions to fix bugs

If the app exists before a clip was completely downloaded, or if clip download fails in the middle, is the partial clip download deleted properly? Same for camera thumbnail download and cloud storage clip thumbnail download. Add Unit tests for these (use the appropriate existing test classes).

Maybe there's a safe way to do that at the system level: create file, download, and if I didn't confirm that the file was completely downloaded without error and the process exits, delete it

Now answer the question: If the app exists before a clip was completely downloaded, or if clip download fails in the middle, is the partial clip download deleted properly?

In the web app, in the settings panel, there should be a button to view the log file, which should open it in a new tab or window. The log file viewer should have its own URL, so that we can reload it. The log file should have a scrollable text area showing the latest application log. The log file viewer should by default show the end of the log.
At the bottom, there should be:
- a "Update" button, which reloads the log (a simple implementation would be to just reload the log viewer page)
- a "Level:" pulldown which allows to filter messages which have a level higher (or equal to) than the selected logging level (see logging levels from the logging module) - default is DEBUG
- a "Module:" pulldown with the list of loggers names sorted alphabetically, which allows filtering only the selected component. Default is "*", meaning all components.
The API entry point should be /api/log. The flask route should be a thin wrapper over a connexion handler, just like the other routes. Also add the new API entry points to api.json, with the proper operationId, and add unit tests for both the flask route and the connexion handler.

The thumbnail endpoint is returning "Thumbnail not found" even though the file exists. The problem is that the thumbnail endpoint only checks the cache, but doesn't fall back to checking the file system directly like the clip listing does. Shouldn't the cache also be updated if the thumbnail exists on disk? This functionality should probably be implemented in the cache service. When I got {"error":"Thumbnail not found","success":false} was there a 404 error? I don't think an error was shown by the browser.

I clicked "Update 4 clips" in the UI, and saw that in the console: "WARNING: Video file not found for local clip Maison~3647673306: /Users/deverf/Documents/third_party/blinkpy-flask/cache/clips/Maison~3647673306.mp4". The UI is never updated and no error message is shown. 1. Could the UI display a message when an action fails, rather than giving no feedback? Check that all other UI actions display a proper error message in case of failure. 2. fix the "Update xx clips" functionality, which should download all local-storage clips that are not in the cache and generate thumbnail, and update the thumbnails in the list as soon as they are available.

Is strict patching still enabled? Make a note in the code to NEVER disable it permanently. Let us keep the test quality bar high!

Why is ensure_blink_connection_initialized in blink_service and not blink_connection? Maybe it's the right place, but do you have an explanation?

Shouldn't we use create_mock_blink_connection each time we patch ensure_blink_connection_initialized or get_blink_connection, and create_mock_blink_instance each time we patch ensure_blink_initialized or get_blink_instance? Can you check on existing passing tests if it breaks them or makes them better to systematically use mock factories?

what about when we patch get_blink_connection or get_blink_instance? shouldn't we patch ensure_blink_connection_initialized and ensure_blink_initialized instead?

Start systematically updating these tests to use the correct ensure_* function patches. But start by making a list of tests to fix. Each time you start fixing a test, first check that it passes, then fix it, then check that it passes after fixing, then mark it as done in the list and commit. If the test does't pass before fixing, mark it as "broken", and git commit. If the fixed test does't pass after fixing, revert the change, mark it as "breaking", and git commit. Then go to the next test. Be careful that some test may actually test when get_blink_connection or get_blink_instance return None.

TODO:

When I am on the "Clips" or "Settings" tab, I would like the URL to change so that I stay on the same tab when reloading the page. This could be done either by adding "#clips" or "#settings" to the page URL, or by using a different base URL (and thus a separate flask route and connexion handler). Which solution do you recommend?
