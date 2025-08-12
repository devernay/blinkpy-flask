Write an http server running the flask Python framework, which allows full access to a Blink camera system, through the blinkpy python package (available on github as https://github.com/fronzbot/blinkpy, which is cloned in the `blinkpy` subdirectory). The blinkpy package is meant to be run in a signe thread, so make sure that every call to the blinkpy If some of the functionality described below is not accessible through the blinkpy package, please use placeholders. When pressed, a placeholder should pop up a text which says that the feature is not yet available, with a "close" button to dismiss the popup.

The script to run the server is `app.py`, and `app.py -h` should show help and command-line parameters.

The first time the server is accessed, or if saved credentials are not available, it should ask for Blink credentials (username and password), and login using the procedure described in the blinkpy documentation (`blinkpy/README.md`, section "Starting blink without a prompt"). It should then present a page to ask for the 2FA token sent by email or SMS, and after the 2FA key is sent, it should save the credentials to `<cache>/blink.json` using the procedure described in the section "Saving credentials" of `blinkpy/README.md`.

The `<cache>` directory, which is used for caching credentials, camera thumbnails, and downloaded clips, should be a command-line parameter of the main script `app.py`.

If saved credentials are available from `<cache>/blink.json`, they should be loaded using the procedure described in the section "Supplying credentials from file" in `blinkpy/README.md`.


If credentials are wrong, they should be erased and the server should return to the login page.

The top of the home page should have a three buttons to select one of the views: "Home", "Clips" or "Settings":
- "Home" button should have a "home" icon and the word "Home" below.
- "Clips" button should have a "play video" icon and the word "Clips" below.
- "Settings" should have a "gear" icon" and the word "Settings" below.

# "Home" view

The "Home" view should allow to select the current Blink system on top (if there is more than one), and have a "plus" button on the right to add a new device to the system.

The elements above form the "Home" view header and should not scroll when the devices are scrolled/

Below the header is the list of devices in this system, which is scrollable. A device can be a Blink camera or a Blink sync module.

At the bottom of the page, there is a non-scrollable toggle button that has two possible states: "Disarmed" or "Armed", and it is used to arm or disarm the selected Blink system.

## Blink camera

A blink camera device is displayed as the latest captured thumbnail, with some information overlaid:
- On the top-left of the thumbnail is the name of the camera
- On the bottom-left of the thumbnail is the last time the thumbnail was updated , in days, e.g. "105d ago" if it was last updated 105 days ago. the date when each thumbnail was last updated can be extracted from the ts parameter of the thumbnail URL.
For example if the URL is /api/v3/media/accounts/200995/networks/440889/lotus/148021/thumbnail/thumbnail.jpg?ts=1742459551&ext= , the thumbnail was last updated at 1742459551 since epoch. This has then to be converted into days before the current server timezone and displayed.
- On the bottom-right of the thumbnail is a kebab button, which allows accessing the camera pane (described below)
- In the middle of the thumbnail, there is a "play" button (with a "play icon") that switches to the "Live View" for that camera (see details below).

The thumbnails for all cameras should be cached by the server in the `<cache>/thumbnails` subdirectory, together with their timestamp ("ts" parameter in the thumbnail URL). If, when loading the devices, the thumbnail URL is found to be more recent than the cached one (based on the "ts" value), it should be downloaded and updated.

When the app is launched, it scans the thumbnail cache directory for existing thumbnails with their date, loads them from the cache, and updates the thumbnail date. It should fetch a new thumbnail only if the thumbnail date from the device list is more recent than this of the cached thumbnail, in which case it will remove and update the cached thumbnail.

## Live View

Clicking on the the "play" button in the middle of a thumbnail opens the "Live View" page for that camera.
On the top-left of the Live View page, there is a "Back" button (back arrow), that goes back to the "Home" view.
On the top-right of the Live View page, there is a "Mute" button ("speaker" icon) to mute the sound of the live view.

### Live streaming MPEG-TS livestreaming via local TCP proxy server

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

## Camera pane

The camera pane is overlaid on the page when the camera kebab button is pressed. It has:
- On top-right a "close" button (with a cross) to close the pane and get back to the Home view.
- On top-left, the name of the camera in boldface
- below, a text saying whether the camera is online or offline.
- below, a "Motion Detection" toggle, with a text saying it is "On (System Armed)" or "Off (System Disarmed)"
- below, a "Refresh thumbnail" button with a camera icon, to refresh the camera thumbnail.
- below, a "Device Settings" with a gear icon. We will detail later (TODO) what this button does. it is a placeholder for now.

"Refresh thumbnail" should immediately close the Camera pane, and display the text "Refreshing thumbnail..." on a green background banner inside the camera thumbnail, on the top. The thumbnail and the thumbnail age should be updated both in the cache and in the "Home" view as soon as available,  the previous camera thumbnail should be removed from the cache, and the banner text should say "Thumbnail updated!" for 1s, then disappear.

## Sync module

A sync module is displayed as the word "Sync Module", with a text on the right saying whether it is "Online" or "Offline"

We will detail later (TODO) what clicking on the sync module does.

# "Clips" view

The "Clips" view should show a scrollable list of clips. At the bottom of the list of clips, there is a non-scrollable popup button to select between "Local storage" or "Cloud storage".

If "Cloud storage" is empty, "Local storage" should be automatically selected. A spinning wheel should be displayed while the list of clips is being loaded.

## List of clips

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

The clips (either cloud based or local) should be cached by the server in a FIFO cache, and the cache size should have a default size of 100 clips. Identify clearly the clips cache size in the code. For each clip, a thumbnail should be shown if it is available from the clip cache. The thumbnail for downloaded clips is the middle frame from the clip. Clip thumbnails should be cached in the same directory as the clips. When a thumbnail is not available for a given clip, the thumbnail should show a "play" button. As soon as a clip thumbnail is cached, the "Clips" view should display that thumbnail without having to reload the page.

See blinkpy/blinksync/blinksync.py for the correct way to get the list of local storage clips. Whenever needed, local storage clips can be downloaded using item.prepare_download() followed by item.download_video(), as in blinkpy/blinksync/blinksync.py

On the top of the local storage clips list, there should be a "Update xx Clips" button,  where xx is the number of clip thumbnails missing. Pressing this button will trigger downloading all clips that are not in the server cache, and updating their thumbnails. Those updates should be done in the background (The GUI should remain usable), and thumbnails should be updated as they become available. When all local clip thumbnails are already available, the "Update xx Clips" button should be hidden.

When all local clip thumbnails are already available, the "Update All" button should be hidden. When some local clip thumbnails are not available, the text should not say "Update All" but "Update xx Clips", where xx is the number of clip thumbnails missing.

# "Settings" view

The "Settings" view should have:
- "Temperature Units" with the choces "Celsius" or "Fahrenheit".
- "Auto Delete Cloud Clips After..." with the following choices: 60 days (default), 30 days, 14 days, 7 days, 3 days.
- "Auto Delete Local Clips After..." with the following choices: Never (default), 60 days, 30 days, 14 days, 7 days, 3 days.
- "Clip Thumbnail Size" with the following choices: Small, Medium (default), Large.
- a "Clear Cache" button, which will clear the on-disk and in-memory caches for device thumbnails, clips, and clips thumbnails. The corresponding images in the web pages should be invalidated. Stored credentials should not be cleared.
- a "Log out" button, which shows a confirmation dialog, and if confirmed resets the stored credential and also executes the same actions as "Clear cache". Once the credentials are reset, the server should show the login page.

The settings should be saved in a settings.json file in the cache. settings.json should not be removed when logging out.

# TODO

- Fix live view
- add motion_enabled button to each camera in Home view
- Add camera properties
  - temperature (celcius or f)
  - battery voltage
  - wifi_strength (may be None)
  - sync_signal_strength (may be None)
- Continuous live view using a strategy similar to blinkbridge https://github.com/roger-/blinkbridge
- Pan/tilt control, if it becomes available https://github.com/MattTW/BlinkMonitorProtocol/issues/69

# Code quality improvements

Re-read IMPLEMENTATION.md, and make sure that *everything* is implemented as described. If there are differences, list those and wait for my instructions, don't do the changes immediately.

Read the whole code again, including the Python code, the Javascript code and the HTML templates. How would you rate the code quality? Is there room for improvement?  Is there code that can be de-duplicated or factorized? Add a section to IMPLEMENTATION.md with the proposed code quality improvements.

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

#### JavaScript Code (1,496 total lines across 4 files)
**Issues:**
- **Global state management**: Multiple global variables scattered across files
- **Repeated AJAX patterns**: Similar fetch() calls with error handling
- **DOM manipulation duplication**: Repeated element selection and manipulation
- **Event handler patterns**: Similar event binding across modules

**Recommended Improvements:**
```javascript
// Create centralized modules:
static/js/
├── core/
│   ├── api.js           # Centralized API calls
│   ├── state.js         # Global state management
│   ├── dom.js           # DOM utilities
│   └── events.js        # Event management
├── modules/
│   ├── camera.js        # Camera operations
│   ├── clips.js         # Clip management
│   ├── livestream.js    # Live streaming
│   └── settings.js      # Settings management
└── app.js               # Main application entry
```

### 2. Specific Code Quality Issues

#### C. JavaScript API Centralization
**Current Problem:** Repeated fetch patterns across files

**Proposed Solution:**
```javascript
// api.js - Centralized API client
class ApiClient {
    static async request(endpoint, options = {}) {
        const response = await fetch(endpoint, {
            headers: { 'Content-Type': 'application/json' },
            ...options
        });

        if (!response.ok) {
            throw new ApiError(`Request failed: ${response.status}`);
        }

        return response.json();
    }

    static async get(endpoint) {
        return this.request(endpoint);
    }

    static async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
}

// Usage in modules:
const clips = await ApiClient.get('/api/clips?storage=cloud');
```

### 3. Performance Optimizations

#### A. Database/Cache Layer
- **Implement cache warming**: Pre-load frequently accessed thumbnails
- **Add cache metrics**: Monitor hit rates and optimize sizes
- **Implement cache invalidation**: Smart cache updates based on device changes

#### B. Frontend Optimizations
- **Lazy loading**: Load clips and thumbnails on demand
- **Image optimization**: Implement responsive images with multiple sizes
- **Bundle optimization**: Minify and combine JavaScript files

### 5. Testing Improvements

#### Current Status:
- 50% code coverage (732/1459 lines)
- 248 passing tests out of 369 total

#### Recommendations:
- **Increase coverage to 80%**: Focus on critical paths
- **Add integration tests**: End-to-end API testing
- **Mock external dependencies**: Better isolation of Blink API calls
- **Performance tests**: Load testing for concurrent users

### 6. Documentation and Maintainability

#### Code Organization:
- **Split large files**: Break app.py into logical modules
- **Consistent naming**: Standardize function and variable naming
- **Remove dead code**: Clean up unused imports and functions

#### Documentation:
- **API documentation**: Generate OpenAPI/Swagger docs
- **Architecture diagrams**: Visual representation of system components
- **Deployment guides**: Production deployment instructions

### 7. Security Enhancements

#### Current Issues:
- **Session management**: Could be more robust
- **Input validation**: Some edge cases not covered
- **Error information leakage**: Stack traces in production

#### Recommendations:
- **Implement rate limiting**: Prevent API abuse
- **Add CSRF protection**: For state-changing operations
- **Audit logging**: Track security-relevant events
- **Secrets management**: Better handling of sensitive data

### Implementation Priority

1. **High Priority**: Split app.py into modules, standardize route handlers
2. **Medium Priority**: Consolidate cache classes, centralize JavaScript API calls
3. **Low Priority**: Performance optimizations, additional testing

This refactoring would improve maintainability, reduce bugs, and make the codebase more scalable while preserving all existing functionality.

---




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
