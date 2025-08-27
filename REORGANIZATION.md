# Services Directory Reorganization Plan

## Current Issues

### **Poorly Organized Services**

1. **`utils_service.py`** - Mixed responsibilities (formatting, device data, debug, file checks)
2. **`cache_service.py` + `cache_management.py`** - Duplicate cache responsibilities
3. **`connection_service.py`** - Generic connections mixed with Blink-specific logic
4. **`lifecycle_service.py`** - Startup/shutdown mixed with cache loading and video dumping
5. **`clip_service.py`** - Overly large (32KB, 800+ lines) with multiple concerns
6. **`stream_service.py`** - Large (17KB, 500+ lines) mixing stream management and HLS processing

### **Poorly Organized Utils**

1. **`utils/validators.py`** - **MIXED RESPONSIBILITIES** (12KB, 350+ lines)
   - ❌ URL parsing (`extract_thumbnail_timestamp`)
   - ❌ CLI argument parsing (`parse_arguments`)
   - ❌ Input validation (`validate_string_input`)
   - ❌ Data parsing (`parse_clip_id`)
   - ❌ Data formatting (`format_clips_by_day`, `format_time_ago`)
   - **This is a "junk drawer" module with unrelated functions**

2. **`utils/decorators.py`** - **OVERLY LARGE** (24KB, 600+ lines)
   - ✅ Core decorators (error handling, blink availability)
   - ❌ Route-specific decorators (API, caching, file responses)
   - ❌ Internal helper functions mixed with public decorators
   - **Should separate core utilities from Flask-specific decorators**

3. **`utils/error_handlers.py`** - **MIXED CONCERNS**
   - ✅ Generic error handling (`handle_api_error`)
   - ❌ Blink-specific validation (`require_sync_module`)
   - **Should separate generic error handling from domain-specific validation**

### **Well-Organized Models & Types**

✅ **`models/` directory is well organized:**
- **`models/ids.py`** - ID validation classes (CameraId, NetworkId, ClipId) with proper inheritance
- **`models/types.py`** - Centralized type definitions and aliases
- **`models/responses.py`** - API response utilities (single function, focused)
- **`models/cache.py`** - Cache data structures and thread-safe implementations
- **`types/` directory** - Empty (unused, can be removed)

**No changes needed for models directory** - it follows good separation of concerns with focused modules.

### **Poorly Organized Routes**

1. **`routes/admin.py`** - **MIXED RESPONSIBILITIES**
   - ✅ Cache management endpoints (`/api/cache/*`)
   - ❌ Placeholder route (`/placeholder`) - unrelated to admin functions
   - ❌ Inline cache clearing logic - should use service functions
   - **Should focus on admin operations only**

2. **`routes/camera.py`** - **OVERLY LARGE** (22KB, 500+ lines)
   - ✅ Camera details and recording
   - ❌ Thumbnail operations (should be separate)
   - ❌ Streaming operations (should be separate)
   - ❌ Inline business logic mixed with route handling
   - **Should be split by functionality**

3. **`routes/settings.py`** - **MIXED CONCERNS**
   - ✅ User settings (`/api/settings`)
   - ❌ Application config (`/api/config`) - different concern
   - **Should separate user settings from app configuration**

4. **Route registration inconsistency** - Some use `setup_*_routes()`, others use `register_*_routes()`

## Recommended Reorganization

### **1. Consolidate Cache Operations**
**Merge:** `cache_service.py` + `cache_management.py` → `cache_service.py`

```python
# blinkapp/services/cache_service.py
def initialize_cache_paths() -> None
def clear_all_caches() -> dict[str, Any]
def get_cache_directories() -> dict[str, str | None]
def ensure_cache_directories_exist() -> None
def validate_cache_directory(cache_dir: str) -> bool
def ensure_cache_directory(cache_dir: str, validator=None) -> None
def initialize_caches(config: dict[str, Any]) -> None
def ensure_clips_cache_initialized()
def ensure_thumbnail_cache_initialized()
def get_cache_stats() -> dict[str, dict[str, int | float]]
def load_thumbnail_cache() -> None
def load_clips_cache() -> None  # Move from lifecycle_service
```

### **2. Split utils_service.py by Responsibility**

**Create:** `utils/formatters.py`
```python
def format_device_temperature(temperature) -> str
def format_battery_level(voltage) -> str
def format_clips_by_day(clips_by_day: dict[str, dict[str, object]]) -> list[dict[str, object]]  # Move from validators
def format_time_ago(timestamp_str: str | int | None) -> str  # Move from validators
```

**Create:** `services/device_service.py`
```python
def create_device_data(camera: BlinkCamera, cache_key: CameraId, current_ts: int = 0, cached_ts: int = 0) -> dict[str, object]
```

**Create:** `services/debug_service.py`
```python
def dump_blink_system_info() -> None
def handle_dump_system(credentials_checker=None) -> None
def check_credentials_file_exists(credentials_path) -> bool
def dump_cloud_videos(videos: list[dict[str, object]]) -> None  # Move from lifecycle_service
```

**Delete:** `utils_service.py` (functions moved to appropriate modules)

### **3. Split connection_service.py**

**Keep:** `services/connection_service.py` (generic connections)
```python
def initialize_connections() -> None
def ensure_executor_initialized() -> ThreadPoolExecutor
def ensure_http_session_initialized()
```

**Create:** `services/blink_connection.py` (Blink-specific)
```python
class BlinkConnection:
    def __init__(self, timeout: int | None = None) -> None
    def start(self) -> None
    def execute(self, coro: Coroutine[Any, Any, T], timeout: int | None = None) -> T
    def cleanup_active_streams(self) -> None
    def shutdown(self) -> None

def initialize_blink_connection() -> None
def get_blink_connection() -> BlinkConnection | None
def shutdown_blink_connection() -> None
```

### **4. Refactor lifecycle_service.py**

**Keep:** `services/lifecycle_service.py` (core lifecycle only)
```python
def startup() -> None
def cleanup_resources() -> None
async def cleanup_blink_session() -> None
```

**Move to cache_service.py:**
```python
def load_clips_cache() -> None
```

**Move to debug_service.py:**
```python
def dump_cloud_videos(videos: list[dict[str, object]]) -> None
```

### **5. Split Large Services**

**Split clip_service.py:**

**Keep:** `services/clip_service.py` (core operations)
```python
def process_cloud_clips(videos_metadata: list[dict[str, object]]) -> list[dict[str, object]]
def process_local_clips(blink_instance=None, blink_connection_instance=None) -> list[dict[str, object]]
```

**Create:** `services/clip_download.py`
```python
def download_cloud_clip(clip_id: ClipId, blink_instance=None, cache_dir=None) -> tuple[bool, str, Path | None]
def download_local_clip(clip_id: ClipId, sync_name: str, item_id: int, cache_dir=None) -> tuple[bool, str, Path | None]
def download_clip_common(clip_id: ClipId, filepath: Path, media_url: str, session_instance=None) -> tuple[bool, str]
```

**Create:** `services/clip_processing.py`
```python
def process_cloud_clip_background(clip_id: ClipId) -> None
def process_local_clip_background(clip_id: ClipId, sync_name: str, item_id: int) -> None
def download_and_cache_cloud_thumbnail(clip_id: ClipId, thumbnail_url: str, cache_instance=None, session_instance=None) -> Path | None
```

**Split stream_service.py:**

**Keep:** `services/stream_service.py` (stream management)
```python
def initialize_stream_manager(manager_factory=None) -> None
def ensure_stream_manager_initialized(manager_factory=None)
def start_camera_stream(camera_id: CameraId, tcp_url: str) -> tuple[str | None, str | None]
def stop_camera_stream(camera_id: CameraId) -> bool
def is_stream_active(camera_id: CameraId) -> bool
def get_hls_file(camera_id: CameraId, filename: str) -> tuple[bytes | None, str | None]
class StreamManager
```

**Create:** `services/hls_service.py`
```python
def parse_tcp_url(tcp_url: str) -> dict[str, str]
def generate_hls_url(camera_id: str, base_url: str = "http://localhost:8080") -> str
def validate_camera_id(camera_id: str) -> bool
def validate_tcp_url(tcp_url: str) -> bool
@dataclass
class StreamConfig
class HLSStream
def _create_ffmpeg_process(cmd: list[str], process_factory=None) -> subprocess.Popen | None
def _build_ffmpeg_command(tcp_url: str, output_path: Path, config) -> list[str]
```

### **6. Reorganize Routes Directory**

**Split routes/camera.py:**

**Keep:** `routes/camera.py` (core camera operations)
```python
def setup_camera_routes(app: Flask) -> None
    # /api/cameras - get all cameras
    # /api/cameras/<id> - get camera details
    # /api/cameras/<id>/record - trigger recording
```

**Create:** `routes/thumbnails.py`
```python
def setup_thumbnail_routes(app: Flask) -> None
    # /api/cameras/<id>/thumbnail - get/clear camera thumbnails
    # /api/clips/<id>/thumbnail - get/create clip thumbnails
```

**Create:** `routes/streaming.py`
```python
def setup_streaming_routes(app: Flask) -> None
    # /api/cameras/<id>/streams - start/stop streams
    # /api/cameras/<id>/streams/<filename> - serve HLS files
```

**Refactor routes/admin.py:**

**Keep:** `routes/admin.py` (admin operations only)
```python
def setup_admin_routes(app: Flask) -> None
    # /api/cache - clear all caches
    # /api/cache/thumbnails - clear thumbnail cache
    # /api/cache/clips - clear clips cache
    # Remove placeholder route, use service functions for cache clearing
```

**Split routes/settings.py:**

**Keep:** `routes/settings.py` (user settings only)
```python
def setup_settings_routes(app: Flask) -> None
    # /api/settings - user preferences
```

**Create:** `routes/config.py`
```python
def setup_config_routes(app: Flask) -> None
    # /api/config - application configuration
```

**Standardize route registration:**
- Use consistent `setup_*_routes(app: Flask)` pattern for all modules
- Remove duplicate `register_*_routes` functions

### **7. Reorganize Utils Directory**

**Split utils/validators.py by Responsibility:**

**Create:** `utils/validators.py` (pure validation only)
```python
def validate_string_input(value: str, max_length: int, field_name: str) -> str
def validate_camera_id(camera_id: str) -> bool  # Move from stream_service
def validate_tcp_url(tcp_url: str) -> bool  # Move from stream_service
def is_valid_email_format(email: str) -> bool  # Move from auth_service
def validate_credentials(username: str, password: str) -> bool  # Move from auth_service
```

**Create:** `utils/parsers.py`
```python
def extract_thumbnail_timestamp(thumbnail_url: str | None) -> int  # Move from validators
def parse_arguments(args: list[str] | None = None) -> argparse.Namespace  # Move from validators
def parse_clip_id(clip_id_str: str) -> tuple[ClipId | None, ApiResponse | None]  # Move from validators
```

**Move to utils/formatters.py:**
```python
def format_clips_by_day(clips_by_day: dict[str, dict[str, object]]) -> list[dict[str, object]]  # Move from validators
def format_time_ago(timestamp_str: str | int | None) -> str  # Move from validators
```

**Split utils/decorators.py:**

**Keep:** `utils/decorators.py` (core utilities only)
```python
@contextmanager
def error_context(operation: str, reraise_as: type[Exception] | None = None) -> Generator[None, None, None]
def safe_execute(func: Callable[[], T], default: T | None = None, log_error: bool = True) -> T | None
def ensure_blink_available(func: Callable[P, T]) -> Callable[P, T | FlaskResponse]
def check_blink_availability() -> ApiResponse | None
```

**Create:** `utils/route_decorators.py`
```python
def api_route(operation_name: str | None = None) -> DecoratorFunction
def api_route_with_validation(operation_name: str | None = None, validate_json: bool = False, validate_params: dict[str, ValidationFunction] | None = None) -> DecoratorFunction
def simple_success_response(message: str | None = None) -> DecoratorFunction
def cached_response(cache_dict: CacheProtocol, cache_key_func: Callable[..., CacheKey] | None = None) -> DecoratorFunction
def file_response_route(operation_name: str | None = None, validate_params: dict[str, ValidationFunction] | None = None) -> DecoratorFunction
def method_dispatch_route(operation_name: str | None = None) -> DecoratorFunction
def cached_api_route(operation_name: str | None = None, cache_dict: CacheProtocol | None = None, cache_key_func: Callable[..., CacheKey] | None = None) -> DecoratorFunction
def template_route_with_validation(operation_name: str | None = None, validate_form: bool = False, validate_params: dict[str, ValidationFunction] | None = None) -> DecoratorFunction
# All internal helper functions (_get_operation_name, _handle_response_formatting, etc.)
```

**Split utils/error_handlers.py:**

**Keep:** `utils/error_handlers.py` (generic error handling only)
```python
def handle_api_error(error: Exception, operation: str, default_message: str = "Operation failed") -> ApiResponse
```

**Create:** `services/blink_validators.py`
```python
def require_sync_module(network_id: NetworkId) -> tuple["BlinkSyncModule | None", ApiResponse | None]
```

**Keep as-is (well organized):**
- `utils/errors.py` - Exception classes (well organized)
- `utils/logging_config.py` - Logging setup (single responsibility)

## Implementation Steps

1. **Create new modules** with moved functions
2. **Update imports** throughout codebase
3. **Update tests** to reference new module locations
4. **Delete old modules** after migration
5. **Run full test suite** to ensure no regressions
6. **Update documentation** to reflect new structure

## Benefits

- **Clear separation of concerns** - Each module has a single responsibility
- **Reduced module size** - No more 800+ line files or 24KB utils
- **Eliminated duplication** - Single cache service instead of two
- **Better discoverability** - Functions grouped by actual functionality
- **Improved maintainability** - Easier to find and modify related code
- **Enhanced testability** - Smaller, focused modules are easier to test
- **Logical organization** - Utils contain pure utilities, services contain business logic
- **Consistent route patterns** - Standardized registration and focused responsibilities

## File Structure After Reorganization

```
blinkapp/
├── routes/
│   ├── admin.py                 # 🔄 Admin operations only (remove placeholder)
│   ├── auth.py                  # ✅ Well organized (no changes)
│   ├── camera.py                # 🔄 Core camera operations only
│   ├── clips.py                 # ✅ Well organized (no changes)
│   ├── config.py                # 🆕 Application configuration
│   ├── settings.py              # 🔄 User settings only
│   ├── streaming.py             # 🆕 Live streaming operations
│   ├── system.py                # ✅ Well organized (no changes)
│   └── thumbnails.py            # 🆕 Thumbnail operations
├── services/
│   ├── auth_service.py          # ✅ Well organized (no changes)
│   ├── blink_connection.py      # 🆕 Blink-specific connection logic
│   ├── blink_service.py         # ✅ Well organized (no changes)
│   ├── blink_validators.py      # 🆕 Blink-specific validation logic
│   ├── cache_service.py         # 🔄 Consolidated cache operations
│   ├── camera_service.py        # ✅ Well organized (no changes)
│   ├── clip_download.py         # 🆕 Clip download operations
│   ├── clip_processing.py       # 🆕 Background clip processing
│   ├── clip_service.py          # 🔄 Core clip operations only
│   ├── connection_service.py    # 🔄 Generic connections only
│   ├── debug_service.py         # 🆕 Debug and system info
│   ├── device_service.py        # 🆕 Device data operations
│   ├── file_service.py          # ✅ Well organized (no changes)
│   ├── hls_service.py           # 🆕 HLS and FFmpeg operations
│   ├── lifecycle_service.py     # 🔄 Core lifecycle only
│   ├── logging_service.py       # ✅ Well organized (no changes)
│   ├── stream_service.py        # 🔄 Stream management only
│   ├── system_service.py        # ✅ Well organized (no changes)
│   ├── thumbnail_service.py     # ✅ Well organized (no changes)
│   └── time_service.py          # ✅ Well organized (no changes)
├── routes/
│   ├── admin.py                 # 🔄 Admin operations only (remove placeholder)
│   ├── auth.py                  # ✅ Well organized (no changes)
│   ├── camera.py                # 🔄 Core camera operations only
│   ├── clips.py                 # ✅ Well organized (no changes)
│   ├── config.py                # 🆕 Application configuration
│   ├── settings.py              # 🔄 User settings only
│   ├── streaming.py             # 🆕 Live streaming operations
│   ├── system.py                # ✅ Well organized (no changes)
│   └── thumbnails.py            # 🆕 Thumbnail operations
├── models/
│   ├── cache.py                 # ✅ Well organized (thread-safe cache implementations)
│   ├── ids.py                   # ✅ Well organized (ID validation classes)
│   ├── responses.py             # ✅ Well organized (API response utilities)
│   └── types.py                 # ✅ Well organized (centralized type definitions)
└── utils/
    ├── decorators.py            # 🔄 Core utilities only (error handling, blink checks)
    ├── error_handlers.py        # 🔄 Generic error handling only
    ├── errors.py                # ✅ Well organized (no changes)
    ├── formatters.py            # 🆕 Pure formatting functions
    ├── logging_config.py        # ✅ Well organized (no changes)
    ├── parsers.py               # 🆕 Pure parsing functions
    ├── route_decorators.py      # 🆕 Flask route decorators
    └── validators.py            # 🔄 Pure validation functions only
```

**Remove:**
- `types/` directory (empty, unused)

**Legend:**
- ✅ Well organized (no changes needed)
- 🔄 Refactored (functions moved/reorganized)
- 🆕 New module created
- ❌ Deleted (utils_service.py, cache_management.py, types/ directory)

## Routes Directory Analysis Summary

The **routes directory has significant organizational issues**:

1. **`routes/camera.py`** is 22KB with mixed responsibilities (camera details, thumbnails, streaming)
2. **`routes/admin.py`** mixes admin operations with unrelated placeholder routes
3. **`routes/settings.py`** mixes user settings with application configuration
4. **Inconsistent registration patterns** - some use `setup_*`, others use `register_*`
5. **Inline business logic** mixed with route handling instead of using service functions

The reorganization **separates routes by functionality** and **standardizes patterns** for better maintainability.

## Models & Types Directory Analysis Summary

The **models directory is exceptionally well organized** with clear separation of concerns:

1. **`models/ids.py`** - ID validation classes with proper inheritance and validation patterns
2. **`models/types.py`** - Centralized type definitions preventing duplication
3. **`models/responses.py`** - Single focused function for API responses
4. **`models/cache.py`** - Thread-safe cache implementations with specialized subclasses

**No reorganization needed** - this is an example of good modular design.

The **types directory is empty** and should be removed to avoid confusion.

## Utils Directory Analysis Summary

The current utils directory has **significant organizational issues**:

1. **`validators.py`** is a 12KB "junk drawer" mixing URL parsing, CLI parsing, validation, and formatting
2. **`decorators.py`** is 24KB mixing core utilities with Flask-specific route decorators
3. **`error_handlers.py`** mixes generic error handling with Blink-specific validation

The reorganization separates these into **focused, single-responsibility modules** that are easier to maintain and test.
