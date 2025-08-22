# Duplicate Test Analysis Report

## Summary
Analyzed test files for duplicates and compared coverage to identify the best tests to keep.

## Analysis Results

### 1. Auth Service Tests
**Files analyzed:**
- `test_auth_service_extra.py` - **25% coverage** (70 missed lines)
- `test_auth_service_pure.py` - **27% coverage** (68 missed lines) ✅ **BEST**
- `test_auth_service_final.py` - **23% coverage** (72 missed lines)

**Duplicates found:**
- `test_is_valid_email_format_none` (in extra & pure) - **REMOVED from extra**
- `test_extract_username_domain_multiple_at_symbols` (in extra & final) - **REMOVED from extra**

**Recommendation:** Keep `test_auth_service_pure.py` as primary, remove remaining duplicates from other files.

### 2. Stream Service Tests
**Files analyzed:**
- `test_stream_service_simple.py` - **28% coverage** (165 missed lines)
- `test_stream_service_boost.py` - **41% coverage** (135 missed lines) ✅ **BEST**
- `test_stream_service_expansion.py` - **28% coverage** (165 missed lines)

**Duplicates found:**
- `test_validate_camera_id_*` (across all files) - **REMOVED from simple**
- `test_validate_tcp_url_*` (across all files)
- `test_parse_tcp_url_*` (across all files)
- `test_ensure_stream_manager_initialized_*` (across all files)

**Recommendation:** Keep `test_stream_service_boost.py` as primary, remove remaining duplicates from other files.

### 3. Utils Service Tests
**Files analyzed:**
- `test_utils_service_boost.py` - **19% coverage** (121 missed lines)
- `test_utils_service_final.py` - **20% coverage** (120 missed lines) ✅ **BEST**

**Duplicates found:**
- `test_format_battery_level_*` (similar tests in both)
- `test_format_device_temperature_*` (similar tests in both)

**Recommendation:** Keep `test_utils_service_final.py` as primary, remove duplicates from boost.

### 4. Decorators Tests
**Files analyzed:**
- `test_decorators_simple.py` - **34% coverage** (130 missed lines)
- `test_decorators_final.py` - **39% coverage** (120 missed lines) ✅ **BEST**

**Duplicates found:**
- `test_safe_execute_success` (in both)
- `test_safe_execute_exception*` (similar tests in both)

**Recommendation:** Keep `test_decorators_final.py` as primary, remove duplicates from simple.

## Actions Taken
1. **REMOVED** `test_is_valid_email_format_none` from `test_auth_service_extra.py`
2. **REMOVED** `test_extract_username_domain_multiple_at_symbols` from `test_auth_service_extra.py`
3. **REMOVED** `test_validate_camera_id_*` tests from `test_stream_service_simple.py`

## Coverage Impact
- **Auth Service**: Keeping pure.py saves 2 lines (68 vs 70 missed)
- **Stream Service**: Keeping boost.py saves 30 lines (135 vs 165 missed)
- **Utils Service**: Keeping final.py saves 1 line (120 vs 121 missed)
- **Decorators**: Keeping final.py saves 10 lines (120 vs 130 missed)

**Total potential coverage improvement: ~43 lines**

## Recommendations for Further Cleanup
1. Remove remaining duplicate `test_validate_tcp_url_*` and `test_parse_tcp_url_*` from simple/expansion files
2. Remove duplicate `test_format_*` functions from utils boost file
3. Remove duplicate `test_safe_execute_*` functions from decorators simple file
4. Consider consolidating similar test files that test the same modules
