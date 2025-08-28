# Specifications

Write an http server running the flask Python framework (with default port 5001), which allows full access to a Blink camera system, through the blinkpy python package (available on github as https://github.com/fronzbot/blinkpy, which is cloned in the `blinkpy` subdirectory). The blinkpy package is meant to be run in a signe thread, so make sure that every call to the blinkpy If some of the functionality described below is not accessible through the blinkpy package, please use placeholders. When pressed, a placeholder should pop up a text which says that the feature is not yet available, with a "close" button to dismiss the popup.

The script to run the server is `python -m blinkapp`, and `python -m blinkapp -h` should show help and command-line parameters.

The first time the server is accessed, or if saved credentials are not available, it should ask for Blink credentials (username and password), and login using the procedure described in the blinkpy documentation (`blinkpy/README.md`, section "Starting blink without a prompt"). It should then present a page to ask for the 2FA token sent by email or SMS, and after the 2FA key is sent, it should save the credentials to `<cache>/blink.json` using the procedure described in the section "Saving credentials" of `blinkpy/README.md`.

The `<cache>` directory, which is used for caching credentials, camera thumbnails, and downloaded clips, should be a command-line parameter of the main script `app.py`.

If saved credentials are available from `<cache>/blink.json`, they should be loaded using the procedure described in the section "Supplying credentials from file" in `blinkpy/README.md`.


If credentials are wrong, they should be erased and the server should return to the login page.

The top of the home page should have a three buttons to select one of the views: "Home", "Clips" or "Settings":
- "Home" button should have a "home" icon and the word "Home" below.
- "Clips" button should have a "play video" icon and the word "Clips" below.
- "Settings" should have a "gear" icon" and the word "Settings" below.

## blinkpy package usage

The blinkpy package is not meant to be used in a multi-threaded context, so the code will implement a BlinkConnection class which handles executing all blinkpy calls in a single thread.

The source of the blinpy package is given in the directory blinkpy-source, for reference.

## "Home" view

The "Home" view should allow to select the current Blink system on top (if there is more than one), and have a "plus" button on the right to add a new device to the system.

The elements above form the "Home" view header and should not scroll when the devices are scrolled/

Below the header is the list of devices in this system, which is scrollable. A device can be a Blink camera or a Blink sync module.

At the bottom of the page, there is a non-scrollable toggle button that has two possible states: "Disarmed" or "Armed", and it is used to arm or disarm the selected Blink system.

### Blink camera

A blink camera device is displayed as the latest captured thumbnail, with some information overlaid:
- On the top-left of the thumbnail is the name of the camera
- On the bottom-left of the thumbnail is the last time the thumbnail was updated in human-readable format: seconds (e.g. "30s ago"), minutes (e.g. "5m ago"), hours (e.g. "2h ago"), or days (e.g. "105d ago"). The timestamp is extracted from the ts parameter of the thumbnail URL.
For example if the URL is /api/v3/media/accounts/200995/networks/440889/lotus/148021/thumbnail/thumbnail.jpg?ts=1742459551&ext= , the thumbnail was last updated at 1742459551 since epoch. This is converted to the appropriate time unit based on age: seconds for <1 minute, minutes for <1 hour, hours for <1 day, days for ≥1 day.
- On the bottom-right of the thumbnail is a kebab button, which allows accessing the camera pane (described below)
- In the middle of the thumbnail, there is a "play" button (with a "play icon") that switches to the "Live View" for that camera (see details below).

The thumbnails for all cameras should be cached by the server in the `<cache>/thumbnails` subdirectory, together with their timestamp ("ts" parameter in the thumbnail URL). If, when loading the devices, the thumbnail URL is found to be more recent than the cached one (based on the "ts" value), it should be downloaded and updated.

When the app is launched, it scans the thumbnail cache directory for existing thumbnails with their date, loads them from the cache, and updates the thumbnail date. It should fetch a new thumbnail only if the thumbnail date from the device list is more recent than this of the cached thumbnail, in which case it will remove and update the cached thumbnail.

### Live View

Clicking on the the "play" button in the middle of a thumbnail opens the "Live View" page for that camera.
On the top-left of the Live View page, there is a "Back" button (back arrow), that goes back to the "Home" view.
On the top-right of the Live View page, there is a "Mute" button ("speaker" icon) to mute the sound of the live view.
At the bottom of the Live View page, there is a "Save" button (💾 icon) that triggers recording a clip on the camera being viewed by calling the `/api/cameras/{camera_id}/record` API endpoint.

#### Live streaming MPEG-TS livestreaming via local TCP proxy server

Live streaming is based on PR [#1079](https://github.com/fronzbot/blinkpy/pull/1078), which uses a local TCP proxy server to stream the camera as MPEG-TS. The `requirements.txt` file installs this version of blinkpy.

Here is sample code that uses this functionality:
```python
import asyncio
import os.path
from aiohttp import ClientSession
from blinkpy.blinkpy import Blink
from blinkpy.auth import Auth
from blinkpy.helpers.util import json_load

async def start():
    blink = Blink(session=ClientSession())
    if os.path.exists("blink.json"):
        auth = Auth(await json_load("blink.json"))
        blink.auth = auth
    await blink.start()
    await blink.save("blink.json")
    camera = blink.cameras["MyCamera"]
    stream = await camera.init_livestream()
    await stream.start()
    print(stream.url)
    await stream.feed()


asyncio.run(start())
```

ffplay just works with the stable stream like this:
```
ffplay tcp://127.0.0.1:<random-port>
```
The URL given to ffplay is `stream.url` from the code above.

In our implementation, the MPEG-TS should be transcoded to HLS and played by the browser.

### Camera pane

The camera pane is overlaid on the page when the camera kebab button is pressed. It has:
- On top-right a "close" button (with a cross) to close the pane and get back to the Home view.
- On top-left, the name of the camera in boldface
- below, a text saying whether the camera is online or offline.
- below, a "Motion Detection" toggle, with a text saying "On (System Armed)", "On (System Disarmed)", "Off (System Armed)", or "Off (System Disarmed)" depending on the camera's motion detection setting and the system's armed/disarmed status
- below, a "Refresh thumbnail" button with a camera icon, to refresh the camera thumbnail.
- below, a "Device Settings" with a gear icon. We will detail later (TODO) what this button does. it is a placeholder for now.

"Refresh thumbnail" should immediately close the Camera pane, and display the text "Refreshing thumbnail..." on a green background banner inside the camera thumbnail, on the top. The thumbnail and the thumbnail age should be updated both in the cache and in the "Home" view as soon as available,  the previous camera thumbnail should be removed from the cache, and the banner text should say "Thumbnail updated!" for 1s, then disappear.

### Sync module

A sync module is displayed as the word "Sync Module", with a text on the right saying whether it is "Online" or "Offline"

We will detail later (TODO) what clicking on the sync module does.

## "Clips" view

The "Clips" view should show a scrollable list of clips. At the bottom of the list of clips, there is a non-scrollable popup button to select between "Local storage" or "Cloud storage".

If "Cloud storage" is empty, "Local storage" should be automatically selected. A spinning wheel should be displayed while the list of clips is being loaded.

### List of clips

The list of clips should should the clips available, either on the sync module local storage, or on Blink cloud storage, depending on the selection.

If the list is empty, it should show the following text:
  **No Recent Activity**
  This is where you'll see motion events and other recent activity from your devices.

The clips are sorted from most recent to least recent, and are grouped by day.
Each day consists in:
- The date, in boldface, followed by the number of recorded events for that day.
- below, for each clip, there is a box for each clip with, from left to right:
  - The thumbnail of the clip (only available for cloud storage)
  - The name of the camera (boldface), and below it the name of the system.
  - The time of the event (in the time zone of the server), and below it the kind of event (which is usually "Motion")

Clicking on a clip will download a clip to the directory `<cache>/clips` with a filename that contains the clip id, the camera name and the ISO date (in server timezone) of the clip.

While loading the clip, the player window should be shown with a dark gray background and a spinning wheel icon, and the following text in white: "Just a moment..." (boldface), and on the next line "We're retrieving your clip.". If the clip is from local storage, it should also say "Hang tight, USB clips take a little longer to load.".

The full player interface should be shown when the clip is loaded, with a timeline that allows scrubbing the clip, but the video should not play right away: the user has to click on the play button to start it.

On top of the video player it should show the camera name, the date and the time, in a font that has the same size as the font used in the clips list.

The clip player should also have those additional buttons on the top-left:
- A trashcan button to delete the clip. This should show a modal dialog saying "<b>Are you sure?</b><br />This will delete the clip and cannot be undone." with two buttons "Delete Clip" (default action) and "Nevermind".
- A download button to download the clip.

The clips (either cloud-based or local) should be cached by the server in a FIFO cache, and the cache size should have a default size of 100 clips. Identify clearly the clips cache size in the code. For each clip, a thumbnail should be shown if it is available from the clip cache. The thumbnail for downloaded clips is the middle frame from the clip. Clip thumbnails (either cloud-based or local) should be cached in the same directory as the clips. The thumbnail from "cloud" clips can be obtained from the API (they don't have to be extracted from the clip itself), and they have to be cached in the same clips cache (with an empty clip if the clip was not downloaded yet). When a thumbnail is not available for a given "local storage" clip, the thumbnail should show a "play" button. As soon as a clip thumbnail is cached, the "Clips" view should display that thumbnail without having to reload the page.

See blinkpy/blinksync/blinksync.py for the correct way to get the list of local storage clips. Whenever needed, local storage clips can be downloaded using item.prepare_download() followed by item.download_video(), as in blinkpy/blinksync/blinksync.py

On the top of the local storage clips list, there should be a "Update xx Clips" button,  where xx is the number of clip thumbnails missing. Pressing this button will trigger downloading all clips that are not in the server cache, and updating their thumbnails. Those updates should be done in the background (The GUI should remain usable), and thumbnails should be updated as they become available. When all local clip thumbnails are already available, the "Update xx Clips" button should be hidden.

When all local clip thumbnails are already available, the "Update All" button should be hidden. When some local clip thumbnails are not available, the text should not say "Update All" but "Update xx Clips", where xx is the number of clip thumbnails missing.

## "Settings" view

The "Settings" view should have:
- "Temperature Units" with the choces "Celsius" or "Fahrenheit".
- "Auto Delete Cloud Clips After..." with the following choices: 60 days (default), 30 days, 14 days, 7 days, 3 days.
- "Auto Delete Local Clips After..." with the following choices: Never (default), 60 days, 30 days, 14 days, 7 days, 3 days.
- "Clip Thumbnail Size" with the following choices: Small, Medium (default), Large.
- a "Clear Cache" button, which will clear the on-disk and in-memory caches for device thumbnails, clips, and clips thumbnails. The corresponding images in the web pages should be invalidated. Stored credentials should not be cleared.
- a "Log out" button, which shows a confirmation dialog, and if confirmed resets the stored credential and also executes the same actions as "Clear cache". Once the credentials are reset, the server should show the login page.

The settings should be saved in a settings.json file in the cache. settings.json should not be removed when logging out.

## Additional Features

### API Documentation and Development Tools

The server should provide comprehensive API documentation through an OpenAPI 3.0 specification file (`api.json`) that documents all available endpoints, request/response schemas, and authentication requirements. This enables developers to integrate with the Blink camera system programmatically.

The development environment should include modern tooling for code quality:
- Pre-commit hooks for automated code formatting and linting
- Type safety with comprehensive type hints throughout the codebase
- Automated testing with a comprehensive test suite covering core functionality
- Code formatting with ruff and type checking with pyright

### Advanced Caching and Performance

The application should implement intelligent caching strategies beyond basic thumbnail caching:
- FIFO (First In, First Out) cache management with configurable size limits
- Automatic cache cleanup to prevent disk space issues
- Connection pooling for efficient HTTP requests
- Background processing for non-blocking operations like clip downloads and thumbnail generation

### Mobile and Responsive Design

The web interface should be fully responsive and optimized for mobile devices:
- Compact layouts that work well on small screens
- Touch-friendly button sizes and spacing
- Responsive navigation that adapts to screen size
- Mobile-optimized video playback controls

### Security and Input Validation

The application should implement comprehensive security measures:
- Input validation and sanitization to prevent XSS attacks
- Secure credential storage with proper encryption
- Request validation with structured error responses
- Protection against common web vulnerabilities

### Settings and Configuration Management

Beyond the basic settings specified, the application should provide:
- Persistent settings storage using JSON files in the cache directory
- Real-time settings updates without requiring page refresh
- Configurable cache sizes and retention policies
- Advanced stream configuration options (segment time, quality settings)

### Resource Management and Cleanup

The application should properly manage system resources:
- Automatic cleanup of temporary files and processes on shutdown
- Proper termination of background threads and streams
- Memory management for long-running operations
- Graceful handling of system interrupts and errors

### Logging and Monitoring

The application should provide comprehensive logging capabilities:
- Structured logging with configurable levels (DEBUG, INFO, WARNING, ERROR)
- Log rotation to prevent disk space issues
- Performance monitoring and error tracking
- Detailed request/response logging for debugging

### Stream Management for Live Video

The live streaming functionality should include advanced stream management:
- Dedicated HLS stream manager for handling multiple concurrent streams
- Automatic stream cleanup when clients disconnect
- Configurable stream quality and bandwidth settings
- Stream health monitoring and automatic recovery

## TODO

- Fix live view
- add motion_enabled button to each camera in Home view
- Add camera properties
  - temperature (celcius or f)
  - battery voltage
  - wifi_strength (may be None)
  - sync_signal_strength (may be None)
- Continuous live view using a strategy similar to blinkbridge https://github.com/roger-/blinkbridge
- Pan/tilt control, if it becomes available https://github.com/MattTW/BlinkMonitorProtocol/issues/69

# **Differences Between Specifications and Current Implementation**

### **✅ CORRECTLY IMPLEMENTED:**

1. Main Entry Point: python -m blinkapp works with proper CLI arguments including --cache
2. Authentication Flow: Login, 2FA, credential saving/loading from <cache>/blink.json
3. Three-Button Navigation: Home/Clips/Settings with proper icons
4. Home View Structure: System selector, device list, arm/disarm toggle
5. Camera Thumbnails: Cached in <cache>/thumbnails with timestamp tracking
6. Live View: Basic implementation with back/mute buttons
7. Clips View: Cloud/Local storage selection, empty state message
8. Settings View: All specified settings (temperature, retention, thumbnail size, clear cache, logout)
9. API Endpoints: Most RESTful endpoints are implemented

# Code Quality Analysis & Improvement Recommendations

## Overall Code Quality Rating: B+ (Good with room for improvement)

The codebase demonstrates solid engineering practices with comprehensive type hints, good error handling, and clean separation of concerns. However, there are several areas where code quality can be significantly improved through refactoring and consolidation.

### Strengths
- **Type Safety**: Comprehensive type hints throughout codebase
- **Error Handling**: Consistent patterns with proper exception handling
- **Documentation**: Good docstrings and inline comments
- **Architecture**: Clean separation of concerns with dedicated service classes
- **Testing**: 50% code coverage with 388 passing tests

### Areas for Improvement

#### 1. Code Duplication (High Priority)
**Problem**: Excessive repeated patterns across the codebase
- **8+ instances** of "Import locally to avoid circular imports" scattered across route handlers
- **14 instances** of repeated `ensure_blink_connection_initialized()` pattern with identical error handling
- **Repeated service initialization** pattern in multiple route handlers

**Impact**: Code duplication, maintenance burden, unclear dependencies

**Solution**: Create centralized service management
```python
# Create a centralized import manager
class ServiceManager:
    @staticmethod
    def get_services() -> dict[str, Any]:
        return {
            'blink_connection': ensure_blink_connection_initialized(),
            'executor': ensure_executor_initialized(),
            'thumbnail_cache': ensure_thumbnail_cache_initialized(),
            'stream_manager': ensure_stream_manager_initialized()
        }

# Service injection decorator
@inject_services(['blink_connection', 'executor'])
def route_handler(camera_id: CameraId, services: dict[str, Any]) -> JsonDict:
    # Services automatically available
```

#### 2. Large Function Complexity (Medium Priority)
**Problem**: Functions with excessive complexity and length
- `update_camera_thumbnail()`: 167 lines
- Several route handlers: 50+ lines each
- Complex nested logic in clip processing functions

**Impact**: Hard to test, maintain, and understand

**Solution**: Extract business logic into service classes
```python
class ThumbnailUpdateService:
    def update_if_needed(self, camera, cache_key, current_ts, cached_ts) -> None
    def _download_and_cache(self, camera, cache_key, current_ts) -> None
    def _cleanup_old_thumbnail(self, cache_key) -> None
```

#### 3. Inconsistent Error Handling (Medium Priority)
**Problem**: Mixed patterns of ValidationError, CameraError, and direct responses
**Impact**: Inconsistent API responses, harder debugging
**Solution**: Standardize error handling with middleware
```python
@standardize_errors
def route_handler() -> JsonDict:
    # Automatic error conversion to standard API format
```

#### 4. Template JavaScript Duplication (Low Priority)
**Problem**: Inline JavaScript mixed with HTML (60+ lines in base.html), limited reusability
**Impact**: Harder to maintain, test, and extend
**Solution**: Extract to separate JS modules with proper organization

### Refactoring Opportunities

#### Route Handler Consolidation
```python
# Current: Repeated pattern in 6+ route handlers
def route_handler(id: SomeId) -> JsonDict:
    # Import locally to avoid circular imports
    from blinkapp.services.blink_service import ensure_blink_connection_initialized
    blink_connection = ensure_blink_connection_initialized()
    # ... validation logic
    # ... business logic

# Proposed: Base class with common patterns
class BaseRouteHandler:
    def __init__(self):
        self.services = ServiceManager.get_services()

    def handle_with_validation(self, validator_func, business_logic_func):
        # Common validation and error handling
```

#### Cache Management Consolidation
```python
# Current: Scattered cache operations
thumbnail_cache = ensure_thumbnail_cache_initialized()
clips_cache = ensure_clips_cache_initialized()

# Proposed: Unified cache manager
class CacheManager:
    def get_cache(self, cache_type: CacheType) -> Cache
    def clear_all(self) -> dict[str, object]
    def get_stats(self) -> dict[str, Any]
```

### Implementation Priority

#### Phase 1 (High Impact, Low Risk)
1. Create ServiceManager for dependency injection
2. Standardize error handling middleware
3. Extract common route handler patterns

#### Phase 2 (Medium Impact, Medium Risk)
4. Refactor large functions into service classes
5. Consolidate cache management
6. Create base route handler class

#### Phase 3 (Low Impact, Low Risk)
7. Extract JavaScript to separate files
8. Create standardized API client
9. Add comprehensive JSDoc documentation

### Expected Benefits
- **Maintainability**: 40% reduction in code duplication
- **Testability**: Easier unit testing with dependency injection
- **Consistency**: Standardized error handling and API responses
- **Performance**: Better caching strategies and resource management
- **Developer Experience**: Clearer code organization and documentation

Do it **step** by **step**, **one** file at a time. For each file from the list above:
- create the file if it does not exist yet
- move it to the right directory
- move the corresponding code and functions to this file
- fix all imports in the code to refer to the new location
- run `ruff check` and `pyright` and fix any issues with the code
- check that all 388 tests from the full test suite still pass
Do not change the API itself: the parameters passed to each function or class should be the same as the original implementation. This should just be about moving code around, not modifying it.
Do not over-engineer the solution. This is just about reorganizing the existing code, not modifying it.

Check for functions that have the same name in the different python files, and verify if this is duplicate code. Give me the results, where for each duplicate function you say where it is defined, if both implementations are identical, and which implementation should be kept because it implements the full functionality.

If yes, resolve the issue by keeping just one instance of each function.

Check for any duplicate or redundant tests, and factorize them. Organize unit tests to mimic the main code organization.

Check for any inconsistencies or duplicate code in the main app code.

Check if the app API is still consistent with the API described in `api.json`. Update `api.json` if needed, and also fix the javascript code that uses this API.

Remove useless comments from the main code and tests that refer to previous versions of the code, such as "xxx moved to yyy", "xxx was moved to yyy", "xxx is now yyy" or "zzz for backward compatibility". Add comments in the code where the code itself is not self-explanatory. Make sure docstrings are complete and up-to-date.

Make sure each python file/module explicitly defines what it exports, and only exports symbols that it implements.

Now read carefully the contents of the blinkpy package (in the blinkpy directory).  Are there functionalities from blinkpy that we don't use in the flask app? are there things that appear in the blinkpy tests that are currently not handled by the flask app? For example, is there a way to fetch a thumbnail for a cloud clip without downloading the clip? Same question for a local clip.

fix the pyright error. Fix as many pyright warnings, even if it means manually updating the blinkpy stubs (found in the blinkpy-stubs directory) with more detailed type hints. Make sure all functions in the python code and tests have type hints.

Next, we will write a full developer documentation detailing, not necessarily in that order:
- The general organization of the code, describing the function of each file.
- How configuration centralization works, what to modify in the Python and javascript code if an additional config constant is needed
- How error messages are defined and shared between Python and Javascript
- How thread-safe LRU cache safety works.
- Route decorators
- How error handling works in Python
- How error handling works in Javascript
- How API response patterns are used in the Python code, with the list of helper functions and when to use them.
- The various decorators implemented in the Python app and their use. Make sure that each validator also has a full docstring with a usage example in the Python code.
- How the CSS is structured
- How the DOM utilities and selection (Javascript) work: DOM, DOMUtils, DOMBatch...
- Any other helpful information that would help the developer understand the code and extend it.
You can find some existing documentation in IMPLEMENTATIONS.md and in the various .md files your can find in this repository, but it is not well organized.
The developper documentation should be in markdown format, in a fine called DOCUMENTATION.md.
First, you should sketch the plan of the documentation, with sections and subsections, and after I approve you can continue filling in the details.









# MISSING FUNCTIONALITIES

## Unused blinkpy Functionalities

The current Flask application implements all core Blink camera functionality specified in the requirements. However, several advanced features available in the blinkpy library are not yet utilized, presenting opportunities for future enhancement.

### 1. Camera Properties Not Exposed
**Available in blinkpy:**
```python
camera.battery_level        # Battery percentage (0-100%)
camera.battery_voltage      # Raw battery voltage (in 100ths of volts)
camera.temperature         # Temperature reading in Fahrenheit
camera.temperature_c        # Temperature in Celsius
camera.wifi_strength        # WiFi signal strength (signal bars)
camera.sync_signal_strength # Sync module signal strength
camera.motion_detected      # Current motion detection state
camera.battery_state        # Battery status string
```

**Current Flask app:** Only shows online/offline status

**Implementation opportunity:**
```python
# Add to camera info API
@app.route("/api/camera/<camera_id>/info")
def get_camera_info(camera_id):
    camera = find_camera_by_id(camera_id)
    return {
        "battery_level": camera.battery_level,
        "temperature": camera.temperature,
        "wifi_strength": camera.wifi_strength,
        "motion_detected": camera.motion_detected
    }
```

### 2. Recent Clips Management
**Available in blinkpy:**
```python
camera.recent_clips[]           # List of recent motion-triggered clips
camera.save_recent_clips()      # Save all recent clips with timestamp patterns
camera.expire_recent_clips()    # Auto-expire old clips
```

**Current Flask app:** Not implemented - we only show cloud/local storage clips

**Implementation opportunity:**
```python
# Add recent clips endpoint
@app.route("/api/camera/<camera_id>/recent-clips")
def get_recent_clips(camera_id):
    camera = find_camera_by_id(camera_id)
    return {"clips": camera.recent_clips}
```

### 3. Advanced Camera Controls
**Available in blinkpy:**
```python
camera.set_motion_detect()    # Per-camera motion detection toggle
camera.get_sensor_info()      # Camera sensor information
```

**Current Flask app:**
- ✅ `camera.snap_picture()` - Already implemented for thumbnail refresh
- ✅ `camera.record()` - Already implemented in Live View Save button
- ❌ Per-camera motion detection - Not implemented

### 4. Local Storage Advanced Features
**Available in blinkpy:**
```python
item.delete_video()           # Delete videos from sync module
item.download_video_delete()  # Download and delete in one operation
```

**Current Flask app:** Only downloads, no deletion capability

### 5. Video Information API
**Available in blinkpy:**
```python
api.request_video_count()     # Total video count
api.request_videos()          # Paginated video list with metadata
# Unwatched videos list
```

**Current Flask app:** Not implemented

### 6. System Health and Diagnostics
**Available in blinkpy:**
```python
# System health checks
# Client device information
# Region information
# Network diagnostics
```

**Current Flask app:** Not implemented

## Implementation Recommendations

### High Priority (Easy Wins)
1. **Camera Properties Display** - Would provide much richer device information to users, matching what's available in the official Blink app
2. **Recent Clips Feature** - Would show motion-triggered clips immediately without waiting for cloud sync
3. **Manual Recording Trigger** - Allow users to manually start recording from camera pane

### Medium Priority
4. **Video Management API** - Total video count, paginated video lists, video deletion capabilities
5. **Per-Camera Motion Detection** - Individual camera motion detection toggle
6. **Camera Sensor Readings** - Detailed sensor information display

### Low Priority
7. **System Diagnostics** - Health monitoring, network diagnostics, client device management

## Impact Assessment

**Camera Properties:** Would provide much richer device information to users, matching what's available in the official Blink app.

**Recent Clips:** Would show motion-triggered clips immediately without waiting for cloud sync.

**Manual Recording:** Would allow users to trigger recording on-demand, useful for testing or capturing specific events.

These features would enhance the application's functionality while maintaining the current stable foundation.


# **Code Quality Analysis & Improvement Recommendations**

### **Overall Code Quality Rating: B+ (Good with room for improvement)**

The codebase demonstrates solid engineering practices with comprehensive type hints, good error handling, and clean separation of concerns. However, there are several areas where code quality can be significantly improved through refactoring and consolidation.

### **Major Issues Identified**

#### **1. Excessive Local Imports (High Priority)**
**Problem**: 8+ instances of "Import locally to avoid circular imports" scattered across route handlers
**Impact**: Code duplication, maintenance burden, unclear dependencies
**Solution**:
```python
# Create a centralized import manager
class ServiceManager:
    @staticmethod
    def get_services() -> dict[str, Any]:
        return {
            'blink_connection': ensure_blink_connection_initialized(),
            'executor': ensure_executor_initialized(),
            'thumbnail_cache': ensure_thumbnail_cache_initialized(),
            'stream_manager': ensure_stream_manager_initialized()
        }
```

#### **2. Repeated Service Initialization Pattern (High Priority)**
**Problem**: 14 instances of `ensure_blink_connection_initialized()` with identical error handling
**Impact**: Code duplication, inconsistent error handling
**Solution**: Create a service injection decorator
```python
@inject_services(['blink_connection', 'executor'])
def route_handler(camera_id: CameraId, services: dict[str, Any]) -> JsonDict:
    # Services automatically available
```

#### **3. Large Function Complexity (Medium Priority)**
**Problem**: `update_camera_thumbnail()` (167 lines), several route handlers (50+ lines)
**Impact**: Hard to test, maintain, and understand
**Solution**: Extract business logic into service classes
```python
class ThumbnailUpdateService:
    def update_if_needed(self, camera, cache_key, current_ts, cached_ts) -> None
    def _download_and_cache(self, camera, cache_key, current_ts) -> None
    def _cleanup_old_thumbnail(self, cache_key) -> None
```

#### **4. Inconsistent Error Handling (Medium Priority)**
**Problem**: Mixed patterns of ValidationError, CameraError, and direct responses
**Impact**: Inconsistent API responses, harder debugging
**Solution**: Standardize error handling with middleware
```python
@standardize_errors
def route_handler() -> JsonDict:
    # Automatic error conversion to standard API format
```

#### **5. Template JavaScript Duplication (Low Priority)**
**Problem**: Inline JavaScript mixed with HTML, limited reusability
**Impact**: Harder to maintain, test, and extend
**Solution**: Extract to separate JS modules with proper organization

### **Specific Refactoring Opportunities**

#### **Route Handler Consolidation**
```python
# Current: Repeated pattern in 6+ route handlers
def route_handler(id: SomeId) -> JsonDict:
    # Import locally to avoid circular imports
    from blinkapp.services.blink_service import ensure_blink_connection_initialized
    blink_connection = ensure_blink_connection_initialized()
    # ... validation logic
    # ... business logic

# Proposed: Base class with common patterns
class BaseRouteHandler:
    def __init__(self):
        self.services = ServiceManager.get_services()

    def handle_with_validation(self, validator_func, business_logic_func):
        # Common validation and error handling
```

#### **Cache Management Consolidation**
```python
# Current: Scattered cache operations
thumbnail_cache = ensure_thumbnail_cache_initialized()
clips_cache = ensure_clips_cache_initialized()

# Proposed: Unified cache manager
class CacheManager:
    def get_cache(self, cache_type: CacheType) -> Cache
    def clear_all(self) -> dict[str, object]
    def get_stats(self) -> dict[str, Any]
```

### **JavaScript/Template Improvements**

#### **Extract Inline JavaScript**
```javascript
// Current: 60+ lines of inline JavaScript in base.html
// Proposed: Separate modules
// static/js/modal.js
// static/js/live-view.js
// static/js/api-client.js
```

#### **API Client Standardization**
```javascript
// Proposed: Consistent API client
class BlinkApiClient {
    async startLiveView(cameraId) { /* ... */ }
    async refreshThumbnail(cameraId) { /* ... */ }
    async triggerRecording(cameraId) { /* ... */ }
}
```

### **Implementation Priority**

#### **Phase 1 (High Impact, Low Risk)**
1. Create ServiceManager for dependency injection
2. Standardize error handling middleware
3. Extract common route handler patterns

#### **Phase 2 (Medium Impact, Medium Risk)**
4. Refactor large functions into service classes
5. Consolidate cache management
6. Create base route handler class

#### **Phase 3 (Low Impact, Low Risk)**
7. Extract JavaScript to separate files
8. Create standardized API client
9. Add comprehensive JSDoc documentation

### **Expected Benefits**

- **Maintainability**: 40% reduction in code duplication
- **Testability**: Easier unit testing with dependency injection
- **Consistency**: Standardized error handling and API responses
- **Performance**: Better caching strategies and resource management
- **Developer Experience**: Clearer code organization and documentation

### **Risk Assessment**

- **Low Risk**: Service manager, error handling middleware
- **Medium Risk**: Large function refactoring (requires careful testing)
- **High Risk**: None identified - all changes are incremental improvements

The codebase has a solid foundation and these improvements would elevate it from "good" to "excellent" while maintaining backward compatibility and system stability.




Check all the api route names. Do they look consistent, logical, and RESTful? Is there room for improvements?

ok, implement the recommended improvements. Also update api.json, the python code and tests, the javascript and the documentation

did you update api.json? Is it complete? Are there more actions missing or outdated? Also update the documentation.

run ruff check, pyright, and pytest (full test suites), and fix all issues. Do not stop until all issues are fixed.

are there any duplicate tests? if yes, compare individual tests and keep the one with the best coverage (in number of lines). Do not remove whole files, but reason test case by test case.

# Cleanup after reorganization

Execute modifications from the "Cleanup after reorganization" section of `IMPLEMENTATION.md`. Start with High priority items, then Normal priority, and finally Lower priority. Read carefully the instructions at the beginning of the section.

Before starting, and after each modificiation of the code, do the following tests:
- [x] All imports updated (including in tests)
- [x] All mocks and patches updated in tests
- [x] Mocks should be created with "Mock(spec=...)" when possible
- [x] Do your best to not use generic types like Any or object
- [x] Do not use cast
- [x] For the spec parameter of Mock, use just the type name, not the full path, and add proper imports. For example, use Mock(spec=CameraThumbnailCache), not Mock(spec=blinkapp.models.cache.CameraThumbnailCache)
- [x] Symbols explicitly exported using `__all__` in every module
- [X] `ruff check` and `pyright` pass with no errors or warnings on all code (including tests)
- [x] Tests pass (full test suite, not just core tests)
- [x] Strong typing: use type hints everywhere (including tests), reduce usage of `Any` or `object`
- [x] Avoid functions that have multiple behaviors depending on the parameter type. It is allowed to use `<type> | None` but not `<type1> | <type2>` with different processing logics for type1 and type2
- [x] All calls to blinkpy should be launched in the blink thread using blink_connection.execute(blink....)
- [x] No circular imports
- [x] Functions moved to correct modules
- [x] Route registration works
- [x] Application starts successfully

Automatically retry until everything is done. Do not stop midway. Be self-critical, verify and understand what you are doing. Do not be polite with yourself or with me. Humans (including me) make errors, and you make errors too, be careful. Take your time.

Do not forget that there is a lot of Blink API and blinkpy API documentation and sample usages (in tests) in blinkpy-source. Use it as often as possible, re-read the whole code if necessary to refresh your memory.

Do not forget to compact your context before it overflows.

## High priority

- Fix all pyright issues, fix all tests (full test suite), run ruff check and ruff format, then `git commit`

- Update all docstrings, README.md, and add comments to the code where it's not self-explanatory.

## Normal priority

- fix get_session_transaction to return an actual type. I know that "Iterator[SessionMixin]" doesn't work because client.session_transaction() returns a context manager, not an iterator. Find the right return type.

- Where do the thresholds for voltage values in format_battery_level come from? Did you get these from blinkpy-source code or tests? Or did you get these from somewhere else?

- Check in blinkpy-source if temperatures in the Blink API are supposed to be in Celsius or Fahrenheit (also look at the docume,ntation and tests from blinkpy-source). Update the code and tests for the app accordingly.

- Update the api.json file by adding as much metadata as possible, following the OpenAPI 3.1.1 specification. This file must truly reflect how the Flask app API works.

- Update the blink-api.json file by adding as much metadata as possible, following the OpenAPI 3.1.1 specification, by looking at the source code, tests and documentations in blinkpy-source. This file must truly reflect how the API works.

- Add significantly more comments to the tests, explaining what we are testing, why we are testing it, and how the test works.

- Are there any duplicate tests? if yes, compare individual tests and keep the one with the best coverage (in number of lines). Do not remove whole files, but reason test case by test case.

# Lower priority

- Run test coverage and add new tests to expand the coverage. Focus first on modules that have the highest numbered of uncovered statements.
