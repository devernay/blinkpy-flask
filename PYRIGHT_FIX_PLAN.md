# Pyright Type Issues Fix Plan

## Summary
Pyright analysis found **83 errors** across the codebase. This document outlines a systematic plan to fix these type issues, organized by priority and complexity.

## Error Categories Analysis

### Top Issues by Frequency:
1. **Route Return Type Issues (15 errors)** - `tuple[JsonDict, int]` not assignable to `RouteResult`
2. **Validation Parameter Issues (14 errors)** - Type validation parameters not matching expected types
3. **Response Type Mismatches (6 errors)** - Werkzeug vs Flask Response types
4. **TypedDict Attribute Access (5 errors)** - Using dot notation instead of bracket notation
5. **JsonValue Type Issues (5 errors)** - Various types not assignable to JsonValue

## Phase 1: Critical Type Infrastructure (Priority: HIGH) ✅ COMPLETED

### 1.1 Fix Route Decorator Type System ✅ DONE
**Files:** `blinkapp/models/types.py`
**Issues:** 15+ route return type errors
**Root Cause:** `RouteResult` type definition didn't include `tuple[JsonDict, int]`

**Solution Applied:**
```python
# Updated RouteResult type to include tuple[JsonDict, int]
RouteResult = FlaskResponse | JsonDict | tuple[JsonDict, int]  # What route functions can return
```

**Impact:** Fixed route return type compatibility issues

### 1.2 Fix JsonValue Type Hierarchy ✅ DONE
**Files:** `blinkapp/models/types.py`
**Issues:** Various types not assignable to JsonValue
**Root Cause:** JsonValue definition too restrictive

**Solution Applied:**
```python
# Expanded JsonValue to include app-specific types
JsonValue = (
    str | int | float | bool | None |
    list["JsonValue"] | dict[str, "JsonValue"] |
    list["SystemDict"] | list["DeviceDict"] | list["ClipDayGroup"]  # Add app-specific types
)
```

### 1.3 Fix Validation Function Types ✅ DONE
**Files:** All route files + new `blinkapp/utils/validation_helpers.py`
**Issues:** 14 validation parameter type errors
**Root Cause:** Using class types instead of validation functions

**Solution Applied:**
```python
# Created proper validation functions
def validate_camera_id(value: str) -> CameraId:
    return CameraId(value)

# Updated all routes to use validation functions:
validate_params={"camera_id": validate_camera_id}
```

**Results:**
- ✅ **Error Reduction:** 83 → 69 errors (14 errors fixed)
- ✅ **All Tests Pass:** 582/582 tests passing
- ✅ **No Regressions:** Functionality maintained

## Phase 2: Response Type Standardization (Priority: HIGH)

### 2.1 Fix Werkzeug vs Flask Response Types ✅ DONE
**Files:** `blinkapp/connexion_handlers/auth.py`
**Issues:** 6 Response type mismatches
**Root Cause:** Mixing werkzeug.Response and flask.Response

**Solution Applied:**
```python
type ResponseReturnValue = str | tuple[str, int] | "FlaskResponse" | "WerkzeugResponse"
# Updated all function return types to use ResponseReturnValue
```

**Impact:** Fixed all 13 auth handler response type errors

### 2.2 Standardize Error Response Types
**Files:** All connexion handlers
**Issues:** `tuple[str, int]` not assignable to Response
**Root Cause:** Inconsistent error response patterns

**Solution:**
```python
# Create standardized error response helper
def error_response(message: str, status: int) -> FlaskResponse:
    return FlaskResponse(message, status=status)
```

## Phase 3: TypedDict and Data Structure Fixes (Priority: MEDIUM)

### 3.1 Fix ClipCacheEntry Attribute Access
**Files:** `blinkapp/connexion_handlers/clips.py`
**Issues:** 5 TypedDict attribute access errors
**Root Cause:** Using dot notation instead of bracket notation

**Solution:**
```python
# Change from:
entry.thumbnail
# To:
entry["thumbnail"]
```

### 3.2 Fix System Service Type Issues ✅ COMPLETED BY PHASE 1.2
**Files:** `blinkapp/services/system_service.py`
**Issues:** SystemDict/DeviceDict not assignable to JsonValue
**Root Cause:** Custom dict types not in JsonValue union

**Solution Applied in Phase 1.2:**
```python
# Expanded JsonValue to include app-specific types (Phase 1.2)
JsonValue = (
    str | int | float | bool | None |
    list["JsonValue"] | dict[str, "JsonValue"] |
    list["SystemDict"] | list["DeviceDict"] | list["ClipDayGroup"]
)
```

**Impact:** Original Phase 3.2 issues resolved by Phase 1.2 JsonValue expansion

## Phase 4: Import and Missing Symbol Fixes (Priority: MEDIUM)

### 4.1 Fix Missing Import Symbols
**Files:** Various connexion handlers
**Issues:** Unknown import symbols (record_camera, delete_clip, etc.)
**Root Cause:** Functions not exported in __all__ or missing implementations

**Solution:**
```python
# Add missing functions to service __all__ exports
# Or implement missing functions
```

### 4.2 Fix Request Type Issues
**Files:** Route files
**Issues:** `get_json` attribute unknown
**Root Cause:** Missing Flask Request import

**Solution:**
```python
from flask import Request
# Ensure proper Request type annotation
```

## Phase 5: Service Layer Type Fixes (Priority: LOW)

### 5.1 Fix Async/Coroutine Type Issues
**Files:** `blinkapp/services/debug_service.py`
**Issues:** Accessing attributes on CoroutineType
**Root Cause:** Incorrect async handling

**Solution:**
```python
# Properly await coroutines before accessing attributes
result = await some_coroutine()
result.attribute  # Now safe
```

### 5.2 Fix Optional/Nullable Type Issues
**Files:** Various service files
**Issues:** Accessing attributes on potentially None values
**Root Cause:** Missing null checks

**Solution:**
```python
# Add proper null checks
if value is not None:
    value.attribute
```

## Implementation Strategy

### Phase 1 (Week 1): Infrastructure ✅ COMPLETED
1. ✅ Fix `RouteResult` type definition
2. ✅ Expand `JsonValue` type union
3. ✅ Create validation function helpers
4. **Actual Impact:** 14 errors fixed (83 → 69 errors)

### Phase 2 (Week 1): Response Types ✅ PARTIALLY COMPLETED
1. ✅ Standardize Response imports (auth.py fixed)
2. ⏳ Fix auth handler return types (DONE)
3. ⏳ Create error response helpers (PENDING)
4. **Actual Impact:** 13 errors fixed (69 → 56 errors)

### Phase 3 (Week 2): Data Structures
1. Fix TypedDict access patterns
2. ✅ Update service return types (COMPLETED BY PHASE 1.2)
3. Add proper type casts where needed
4. **Expected Impact:** ~15 errors fixed

### Phase 4 (Week 2): Imports & Symbols
1. Fix missing import symbols
2. Add missing function implementations
3. Update __all__ exports
4. **Expected Impact:** ~10 errors fixed

### Phase 5 (Week 3): Service Layer
1. Fix async/await patterns
2. Add null safety checks
3. Improve type annotations
4. **Expected Impact:** ~3 errors fixed

## Success Metrics

- **Target:** Reduce from 83 errors to 0 errors
- **Phase 1 Complete:** ✅ 83 → 69 errors (14 fixed)
- **Phase 2.1 Complete:** ✅ 69 → 56 errors (13 fixed)
- **Phase 3.2 Complete:** ✅ Completed by Phase 1.2 (JsonValue expansion)
- **Current Status:** 56 errors remaining
- **Milestone 1:** <40 errors after Phase 1-2
- **Milestone 2:** <15 errors after Phase 3-4
- **Final Goal:** 0 errors after Phase 5

## Risk Assessment

**Low Risk:**
- Type annotation updates
- Adding type casts
- Expanding type unions

**Medium Risk:**
- Changing return types (may affect callers)
- Modifying validation patterns
- Response type standardization

**High Risk:**
- Major architectural changes (avoid)
- Breaking API contracts (avoid)

## Testing Strategy

1. **After each phase:** Run full test suite
2. **Type checking:** `pyright blinkapp/ --level=error`
3. **Runtime testing:** Ensure no functional regressions
4. **Integration testing:** Verify API endpoints still work

## Tools and Commands

```bash
# Check current errors
pyright blinkapp/ --level=error

# Run tests
pytest tests/ -v

# Check specific file
pyright blinkapp/utils/route_decorators.py --level=error

# Count errors by type
pyright blinkapp/ --level=error 2>&1 | grep -E "reportReturnType|reportArgumentType" | sort | uniq -c
```

## Notes

- Focus on fixing root causes rather than symptoms
- Maintain backward compatibility
- Document any breaking changes
- Consider using `# type: ignore` sparingly for complex cases
- Prioritize fixes that resolve multiple errors simultaneously
