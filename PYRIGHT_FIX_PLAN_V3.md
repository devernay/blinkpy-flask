# Pyright Error Fix Plan V3 - Final Push to <40 Errors

**Current Status:** 32 errors → **🎯 WEEK 1 TARGET ACHIEVED! (<40 errors)**

## Error Pattern Analysis

### 🔥 **Phase 6: Type Narrowing Issues ✅ COMPLETED**
**Pattern:** `Cannot access attribute "get" for class "str/int/float/bool/None"`
**Files:** `blinkapp/connexion_handlers/system.py`
**Root Cause:** JsonValue union type too broad - pyright sees all possible types
**Priority:** HIGH - Many errors from single location

**Solution Applied:**
```python
# Fixed by adding isinstance checks for type narrowing
systems_response = get_systems()

# Type narrowing: ensure response is a dict
if not isinstance(systems_response, dict):
    return {"success": False, "error": "Invalid systems response"}, 500

# Type narrowing: ensure data is a dict  
data = systems_response.get("data", {})
if not isinstance(data, dict):
    return {"success": False, "error": "Invalid systems data"}, 500

# Type narrowing: ensure system is a dict
if isinstance(system, dict) and str(system.get("network_id")) == str(network_id_obj):
    return {"success": True, "data": system}
```

**Impact:** 11 errors fixed (43 → 32 errors)

**Key Fix:** Added isinstance() checks before calling .get() method on JsonValue types

---

### 🔥 **Phase 7: Return Type Mismatches (5 errors)**
**Pattern:** `Type "X" is not assignable to return type "JsonDict"`
**Files:** Various connexion handlers
**Root Cause:** Functions returning wrong types (bool, bytes, dict[str, object])
**Priority:** HIGH - Core API functionality

**Specific Issues:**
```python
# Issue 1: Boolean return instead of JsonDict
return True  # Should be {"success": True}

# Issue 2: dict[str, object] vs JsonDict mismatch  
return {"data": some_object}  # object not JsonValue

# Issue 3: ResponseReturnValue vs expected types
return send_file(...)  # bytes vs JsonDict
```

**Solution Strategy:**
```python
# Fix 1: Wrap booleans in proper response
return {"success": True, "data": result}

# Fix 2: Ensure object values are JsonValue compatible
return {"data": convert_to_json_value(some_object)}

# Fix 3: Handle file responses with proper typing
if file_response:
    return file_response  # Flask handles this
else:
    return {"success": False, "error": "File not found"}, 404
```

---

### 🔥 **Phase 8: Validation Function Type Issues (3 errors)**
**Pattern:** `dict[str, type[CameraId]]" cannot be assigned to parameter "validate_params"`
**Files:** Route decorators with validation
**Root Cause:** Validation functions expect callable validators, not type constructors
**Priority:** MEDIUM - API validation functionality

**Specific Issues:**
```python
# Current (BROKEN):
@api_route_with_validation(validate_params={"camera_id": CameraId})
# CameraId is a type, not a validation function

# Expected signature:
ValidationFunction = Callable[[str], Any]
```

**Solution Strategy:**
```python
# Option 1: Create wrapper validation functions
def validate_camera_id(value: str) -> CameraId:
    return CameraId(value)

@api_route_with_validation(validate_params={"camera_id": validate_camera_id})

# Option 2: Use lambda wrappers
@api_route_with_validation(validate_params={"camera_id": lambda x: CameraId(x)})
```

**Recommended:** Option 1 - Explicit validation functions for clarity

---

### 🔥 **Phase 9: Async/Await Issues (3 errors)**
**Pattern:** `"None" is not awaitable`, `"BlinkCamera" is not awaitable`
**Files:** Services with async operations
**Root Cause:** Awaiting non-coroutine objects or None values
**Priority:** MEDIUM - Runtime functionality

**Specific Issues:**
```python
# Issue 1: Awaiting None
result = await some_function()  # some_function returns None

# Issue 2: Awaiting non-coroutine
camera = await find_camera()  # find_camera returns BlinkCamera, not coroutine
```

**Solution Strategy:**
```python
# Fix 1: Check for None before await
result = some_function()
if result is not None:
    await result

# Fix 2: Don't await non-coroutines
camera = find_camera()  # Remove await
```

---

### 🔥 **Phase 10: Missing Arguments (1 error)**
**Pattern:** `Arguments missing for parameters "sync_name", "filename"`
**Files:** Function calls with incomplete parameters
**Root Cause:** Function signature changes or missing required parameters
**Priority:** LOW - Single error, likely easy fix

---

## Implementation Priority

### Week 1 Target: <40 errors (need 4+ fixes)

**✅ Day 1: Phase 6 - Type Narrowing (11 errors) - COMPLETED**
- ✅ Added isinstance() checks for JsonValue type narrowing in system.py
- ✅ Fixed .get() method calls on union types with proper validation
- ✅ **Result:** 43 → 32 errors (11 fixed) - **EXCEEDED WEEK 1 TARGET!**

**Day 2: Phase 7 - Return Types (5 errors)**  
- Fix boolean/object returns to proper JsonDict format
- Handle file response typing correctly
- **Expected:** 5 errors → 0 errors

**Stretch: Phase 8-10 if time permits**
- Validation function fixes (3 errors)
- Async/await fixes (3 errors)  
- Missing arguments (1 error)

## Success Metrics

- **Week 1:** <40 errors (currently 43, need 4+ fixes)
- **Week 2:** <30 errors (stretch goal)
- **Code Quality:** All fixes maintain functionality and improve type safety

## Key Insights

1. **Type Narrowing:** JsonValue union too broad - need isinstance checks
2. **Return Types:** Consistent JsonDict responses for API endpoints
3. **Validation:** Need proper validation functions, not type constructors
4. **Async:** Careful await usage - only for actual coroutines

**Next Action:** Start with Phase 6 (type narrowing) for maximum impact!
