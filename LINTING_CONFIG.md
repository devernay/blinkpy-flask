# Linting Configuration: Mandatory Docstrings and Type Hints

This project enforces mandatory docstrings and type hints through Ruff and Pyright configuration.

## Ruff Configuration

### Docstring Enforcement (D rules)
- **D101**: Missing docstring in public class ❌
- **D102**: Missing docstring in public method ❌
- **D103**: Missing docstring in public function ❌
- **Convention**: Google-style docstrings required

### Type Annotation Enforcement (ANN rules)
- **ANN001**: Missing type annotation for function argument ❌
- **ANN201**: Missing return type annotation for public function ❌
- **ANN401**: Dynamically typed expressions (Any) are disallowed ⚠️ (ignored)

## Pyright Configuration

### Type Hint Enforcement
- **reportMissingTypeAnnotation**: error - Require type hints on all functions
- **reportMissingParameterType**: error - Require type hints on all parameters
- **reportMissingReturnType**: error - Require return type hints
- **reportUnknownParameterType**: error - Flag unknown parameter types
- **reportUnknownVariableType**: error - Flag unknown variable types

## Usage

### Check all files
```bash
# Run Ruff for docstrings and type hints
ruff check .

# Run Pyright for type checking
pyright .
```

### Check specific rules
```bash
# Check only docstrings
ruff check . --select=D

# Check only type annotations
ruff check . --select=ANN

# Check specific file
ruff check path/to/file.py
pyright path/to/file.py
```

### Integration with CI/CD
Add to your CI pipeline:
```bash
ruff check . --select=D,ANN  # Enforce docstrings and type hints
pyright .                    # Enforce type checking
```

## Exceptions

### Allowed to skip docstrings:
- Private methods/functions (starting with `_`)
- Module-level docstrings (D100)
- Package-level docstrings (D104)

### Allowed to skip type hints:
- `self` parameter in methods (automatically handled)
- `cls` parameter in classmethods (automatically handled)

All other public functions, methods, and classes **must** have complete Google-style docstrings and full type annotations.
