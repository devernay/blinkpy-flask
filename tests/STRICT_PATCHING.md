# Strict Patching

This project includes a strict patching system that enforces `__all__` exports when mocking/patching symbols in tests.

## What is Strict Patching?

By default, `unittest.mock.patch` allows patching any symbol in a module, even if it's not intended for public use (not in `__all__`). Strict patching prevents this by only allowing patches of symbols that are explicitly exported via `__all__`.

## Benefits

- **Enforces API boundaries**: Only public interfaces can be mocked
- **Prevents brittle tests**: Tests can't depend on internal implementation details
- **Improves code quality**: Forces proper export declarations
- **Catches refactoring issues**: Tests break when internal symbols are moved/renamed

## Usage

### Enable Strict Patching

Set the `STRICT_PATCHING` environment variable:

```bash
# Enable for all tests
STRICT_PATCHING=1 python -m pytest

# Enable for specific test
STRICT_PATCHING=1 python -m pytest test_app.py::TestClass::test_method
```

### Manual Usage

```python
from test_utils import strict_patch, enable_strict_patching, disable_strict_patching

# Use strict_patch instead of patch
with strict_patch("module.symbol") as mock_symbol:
    # Test code here
    pass

# Or enable globally
enable_strict_patching()
# All patches now use strict mode
with patch("module.symbol"):  # Will check __all__
    pass
disable_strict_patching()  # Restore normal behavior
```

## Error Messages

When strict patching catches an invalid patch:

```
ValueError: Symbol 'internal_function' is not exported by module 'mymodule'.
Available exports: ['public_function', 'PublicClass', 'PUBLIC_CONSTANT']
```

## Fixing Violations

1. **Add to `__all__`** (if symbol should be public):
   ```python
   __all__ = [
       "existing_export",
       "new_public_symbol",  # Add the symbol here
   ]
   ```

2. **Use a different approach** (if symbol should stay internal):
   - Mock at a higher level
   - Test through public interfaces
   - Refactor to make testing easier

## Current Export Status

All commonly patched symbols have been added to appropriate `__all__` lists:

- `blinkapp.*`: Core application symbols
- `blinkapp.services.*`: Service layer symbols
- `blinkapp.routes.*`: Route handler symbols
- `blinkapp.utils.*`: Utility function symbols

## Testing

Run the strict patching tests:

```bash
python -m pytest test_strict_patching.py -v
```
