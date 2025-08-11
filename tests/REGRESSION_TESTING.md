# Regression Testing

This directory contains a baseline-driven regression testing system to detect test failures and ensure code quality.

## Files

- `test_baseline.txt` - Baseline test results (393 tests)
- `check_regression.py` - Script to check for regressions
- `update_baseline.py` - Script to update baseline with new test results

## Usage

### Check for Regressions
```bash
python check_regression.py
```

### Update Baseline (after adding/removing tests)
```bash
python update_baseline.py
```

## Exit Codes

- `0`: No regressions or only new tests added
- `1`: Regressions detected (tests that were passing now fail)

## Integration

Add to CI/CD pipeline:
```bash
cd tests && python check_regression.py
```

This ensures no regressions are introduced in deployments.
