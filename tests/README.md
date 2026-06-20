# Test Suite Documentation

## Overview

This directory contains the test suite for the Blink Camera Flask Web Interface with **73% code coverage** and **777 passing tests**.

## Test Files

| File | Focus |
|------|-------|
| `test_app.py` | Core application, API endpoints, authentication |
| `test_services.py` | Service-layer logic (auth, streaming, clips, cache) |
| `test_routes.py` | Flask route registration and wiring |
| `test_connexion.py`, `test_connexion_handlers.py`, `test_connexion_schema.py` | Connexion handlers and schema |
| `test_models.py` | Data models, IDs, cache structures |
| `test_utils.py` | Utility/helper functions and validators |
| `test_logs.py` | Log viewer and `/api/log` endpoint |
| `test_auth_guard.py` | `/api/*` authentication guard (401 vs login redirect) |
| `test_liveview_recording.py` | Live-view recording lifecycle and clip-list integration |
| `test_docstrings.py` | Docstring presence/quality checks |
| `test_testing_mode.py` | Test-isolation behaviour |
| `test_services_no_isolation.py` | Service tests that opt out of fs isolation |
| `test_base.py` | Shared mock builders and base test case |

## Running Tests

### Quick Start

```bash
# Run all core tests with coverage
cd tests
python run_tests.py --coverage

# Run fast test suite (core tests only)
python run_tests.py --fast

# Generate HTML coverage report
python run_tests.py --html
```

### Using pytest directly

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=blinkapp --cov-report=term-missing

# Run specific test file
pytest test_app.py

# Run with HTML coverage report
pytest --cov=blinkapp --cov-report=html --cov-report=term
```

### Test Runner Options

The `run_tests.py` script provides several options:

```bash
# Basic usage
python run_tests.py                    # All core tests
python run_tests.py --coverage        # With detailed coverage
python run_tests.py --html            # Generate HTML report
python run_tests.py --fast            # Core tests only
python run_tests.py --verbose         # Verbose output

# Specific test suites
python run_tests.py --specific core      # test_app.py only
python run_tests.py --specific critical  # test_critical_coverage.py only
python run_tests.py --specific boost     # test_coverage_boost.py only
python run_tests.py --specific advanced  # Experimental tests
python run_tests.py --specific all       # All tests including experimental

# Additional options
python run_tests.py --no-warnings     # Suppress warnings
```

## Test Coverage

### Current Status
- **Coverage**: 73% (2763/3786 lines)
- **Passing Tests**: 777
- **Total Tests**: 777 (all passing)

### Coverage by Area

#### Well covered
- Core API endpoints (authentication, camera operations, clip management)
- Data validation classes (CameraId, ClipId, BaseId methods)
- Cache operations (LRU cache, ThreadSafeCache)
- Configuration management (Config class, constants)
- Utility functions (API response creation, error handling)
- The `/api/*` authentication guard
- Live-view recording lifecycle (ClipId, finalize/discard, listing, teardown)

#### Less covered (improvement targets)
- Deep system integration (Blink API, network protocols)
- Advanced video processing (FFmpeg operations, HLS transcoding)
- Complex streaming operations (TCP to HLS conversion)
- Rare error conditions (network failures, cascading failures)
- Background processing (thumbnail updates, clip processing)
- File system operations (complex I/O, cleanup procedures)

## Test Architecture

### Organization
- **Modular structure** with logical grouping by functionality
- **Clear naming conventions** with descriptive test method names
- **Comprehensive documentation** with detailed docstrings

### Mocking Strategy
- **Proper isolation** ensuring each test runs independently
- **Resource cleanup** with automatic teardown
- **Realistic scenarios** with mocks that accurately represent real conditions

### Test Types
- **Unit tests**: Individual function and method testing
- **Integration tests**: Component interaction testing
- **Functional tests**: End-to-end workflow testing
- **Error condition tests**: Exception and edge case handling

## Key Testing Patterns

### 1. Async Operation Testing
```python
@patch('app.blink_connection')
@patch('aiohttp.ClientSession')
async def test_async_operation(self, mock_session, mock_connection):
    # Comprehensive async workflow testing
```

### 2. Thread Safety Validation
```python
def test_thread_safety(self):
    # Multi-threaded operations with result validation
    cache = LRUCache(maxsize=100)
    # ... threading test logic
```

### 3. Error Condition Coverage
```python
def test_error_conditions(self):
    with self.assertRaises(NotImplementedError):
        base_id._get_pattern()  # Covers specific error paths
```

### 4. Cache Operations Testing
```python
def test_cache_operations(self):
    cache = ThreadSafeCache()
    cache["key"] = "value"
    self.assertIn("key", cache)  # Covers __contains__ method
```

## Dependencies

### Required for Testing
```bash
pip install pytest pytest-cov coverage
```

### Optional for Enhanced Testing
```bash
pip install pytest-html pytest-xdist pytest-mock
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure you're in the tests directory
   cd tests
   # Or run from project root
   python -m pytest tests/
   ```

2. **Coverage Not Working**
   ```bash
   # Install coverage tools
   pip install coverage pytest-cov
   # Run with explicit coverage
   python -m pytest --cov=blinkapp --cov-report=term-missing
   ```

3. **Tests Failing**
   ```bash
   # Run with verbose output for details
   python run_tests.py --verbose
   # Or run specific failing test
   pytest test_app.py::TestSpecificClass::test_specific_method -v
   ```

### Performance Tips

1. **Faster Test Runs**
   ```bash
   # Run core tests only
   python run_tests.py --fast
   # Run in parallel (if pytest-xdist installed)
   pytest -n auto
   ```

2. **Focused Testing**
   ```bash
   # Run specific test file
   pytest test_coverage_boost.py
   # Run tests matching pattern
   pytest -k "test_cache"
   ```

## Contributing

### Adding New Tests

1. **Choose appropriate test file** based on functionality
2. **Follow naming conventions**: `test_*` for methods, `Test*` for classes
3. **Include proper mocking** for external dependencies
4. **Add docstrings** explaining test purpose
5. **Test both success and error paths**

### Test Quality Guidelines

1. **Independence**: Each test should run independently
2. **Clarity**: Test names should clearly indicate what's being tested
3. **Coverage**: Aim to test both happy path and error conditions
4. **Performance**: Keep tests fast and focused
5. **Maintainability**: Use clear, readable code with good documentation

## Future Improvements

### Planned Enhancements
1. **Integration testing** with real service interactions
2. **Property-based testing** with Hypothesis
3. **Mutation testing** to validate test quality
4. **Performance benchmarking** under load conditions
5. **Contract testing** for API compatibility

### Coverage Goals
- **Target**: maintain >= 72% coverage; raise streaming/video-processing and error-path coverage over time
- **Focus areas**: Video processing, streaming operations, error handling
- **Advanced scenarios**: Network failures, concurrent operations, resource exhaustion
