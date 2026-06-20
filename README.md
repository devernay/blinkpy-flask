# Blink Camera Flask Web Interface

A professional-grade Flask web application providing comprehensive access to Blink camera systems with advanced features including live streaming, clip management, and secure API access.

## Features

### Core Functionality
- **Multi-system support** - Manage multiple Blink systems
- **Real-time camera thumbnails** with intelligent caching and age tracking
- **Live streaming** - TCP to HLS transcoding with FFmpeg using Blink's init_livestream() (see note on live streaming below)
- **Clip management** - Download and view cloud/local storage clips with thumbnail generation
- **2FA authentication** - Full two-factor authentication support with unified login flow
- **RESTful API** - JSON endpoints for programmatic access
- **Thread-safe operations** - Concurrent request handling with background processing
- **Intelligent caching** - reduces repeated Blink API calls with configurable retention
- **Settings management** - Persistent user preferences (temperature units, clip retention, thumbnail sizes)

### Web Interface
- **Responsive design** - Mobile-optimized compact layout
- **Theme** - Light, Dark, or System (follows OS), selectable in Settings
- **System management** - Arm/disarm, device status with real-time updates
- **Camera controls** - Thumbnail refresh with polling, motion detection toggle
- **Clip browser** - Organized by date with auto-updating thumbnails and batch processing
- **Live view** - Real-time camera streaming with HLS support
- **Live-view recording** - Optionally keep a live-view session; saved recordings appear in the clip browser as "Live View" clips
- **Configurable thumbnails** - Small/Medium/Large sizing options

### Security & Performance
- **Input validation** - XSS prevention and data sanitization
- **Resource management** - Automatic cleanup and process handling
- **Error handling** - Comprehensive logging and graceful recovery
- **Cache optimization** - FIFO management with configurable limits and automatic cleanup

## Requirements

- Python 3.12+
- FFmpeg (for live streaming)
- Flask and dependencies (see requirements.txt)

## Installation

1. **Install system dependencies:**
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download FFmpeg from https://ffmpeg.org/
```

2. **Install Python dependencies:**
```bash
# Installs the app and its runtime + dev dependencies (declared in pyproject.toml)
pip install -e ".[dev]"

# Or, equivalently, via requirements.txt (which points at pyproject)
pip install -r requirements.txt

# Runtime only (no test/lint tooling)
pip install -e .
```

blinkpy is pinned to the released **0.25.6** on PyPI — no manual checkout or
submodule is required.

3. **Install type stubs (optional, for better type checking):**
```bash
pip install -e types-blinkpy/
```

4. **Run the application:**
```bash
# Run as Python module (recommended)
python -m blinkapp

# Or with custom options
python -m blinkapp --host 127.0.0.1 --port 8080 --debug
```

**Command line options:**
```bash
python -m blinkapp --help
python -m blinkapp --host 127.0.0.1 --port 8080 --debug
python -m blinkapp --cache /custom/cache/path
python -m blinkapp --log-level DEBUG
python -m blinkapp --dump-system  # Show system info and exit
```

5. **Access the interface:**
   - Web UI: `http://localhost:5001` (default port is 5001, not 5000)
   - API: `http://localhost:5001/api/`

## Authentication

### First Time Setup
1. Navigate to `http://localhost:5001`
2. Enter your Blink credentials (email/password)
3. Complete 2FA verification if required
4. Credentials are securely cached for future sessions

### API Access
All API endpoints return standardized JSON responses:
```json
{
  "success": true,
  "data": {...},
  "timestamp": "2025-01-27T..."
}
```

## API Endpoints

### System Management
- `GET /api/systems` - List available Blink systems
- `GET /api/systems/<network_id>` - Get system details
- `GET /api/systems/<network_id>/devices` - Get devices for system
- `PUT /api/systems/<network_id>` - Update system (arm/disarm)
- `DELETE /api/systems/cache` - Clear systems cache

### Camera Operations
- `GET /api/cameras` - List all cameras
- `GET /api/cameras/<camera_id>` - Get camera details
- `GET /api/cameras/<camera_id>/thumbnail` - Get camera thumbnail
- `GET /api/cameras/<camera_id>/thumbnail?timestamp=true` - Get thumbnail timestamp
- `DELETE /api/cameras/<camera_id>/thumbnail` - Clear thumbnail cache and refresh
- `POST /api/cameras/<camera_id>/streams` - Start live stream
- `DELETE /api/cameras/<camera_id>/streams` - Stop live stream
- `GET /api/cameras/<camera_id>/streams/<filename>` - Get HLS stream segments
- `PUT /api/cameras/<camera_id>/streams/save` - Toggle whether the current live view is kept on stop (`{"saved": true|false}`)
- `POST /api/cameras/<camera_id>/record` - Start recording

**Live-view recording:** A live view is recorded server-side for the whole
session. The Save toggle (which starts pressed when "Save all Live Views" is
enabled) decides whether the recording is kept when the session ends. Kept
recordings are remuxed to MP4, stored in a `recordings/` directory (separate
from the cache), and appear in the clip list as **Live View** clips
(downloadable/deletable via the clip endpoints).

**Live Streaming Implementation:**
Live streaming performs MPEG-TS to HLS transcoding via FFmpeg. The camera's
`init_livestream()` method (blinkpy) creates a local TCP proxy server that
streams MPEG-TS data, which is then transcoded to HLS segments for web browser
compatibility.

This capability originated in blinkpy PR
[#1078](https://github.com/fronzbot/blinkpy/pull/1078), which was **merged and
released in blinkpy 0.25.0**. This project pins the released **0.25.6**, which
also includes the liveview endpoint fix
([#1227](https://github.com/fronzbot/blinkpy/pull/1227)) and the livestream
auth-header fix ([#1167](https://github.com/fronzbot/blinkpy/pull/1167)). No
manual PR checkout is required.

### Clip Management
- `GET /api/clips?storage=cloud|local` - List clips by storage type
- `GET /api/clips/<clip_id>/download` - Download clip file
- `POST /api/clips/<clip_id>/thumbnail` - Generate clip thumbnail
- `GET /api/clips/<clip_id>/thumbnail` - Get clip thumbnail
- `GET /api/clips/<clip_id>/thumbnail?check=true` - Check thumbnail availability
- `DELETE /api/clips/<clip_id>` - Delete clip

### Settings & Utility
- `GET /api/config` - Get application configuration
- `GET /api/settings` - Get user settings
- `PUT /api/settings` - Save user settings
- `DELETE /api/cache` - Clear all caches
- `DELETE /api/cache/thumbnails` - Clear thumbnail cache only
- `DELETE /api/cache/clips` - Clear clips cache only
- `GET /api/log` - Retrieve recent application log entries
- `GET /logs` - Log viewer page
- `POST /logout` - Logout and clear credentials

## Configuration

### Environment Variables
```bash
# Flask session signing key. If unset, an ephemeral random key is generated
# (sessions reset on each restart); set it to keep sessions stable.
SECRET_KEY=your-secret-key-here
CACHE_DIR=cache  # Default cache directory
# Authentication guard (default: on). Set to false for local/dev only.
REQUIRE_AUTH=true
```

### Authentication guard
All routes require an authenticated session except the login/2FA pages, the
favicon, and static assets. Unauthenticated API calls return HTTP 401 with
`{"success": false, "error": "Authentication required"}`; unauthenticated page
requests redirect to `/login`. The guard is controlled by the `REQUIRE_AUTH`
config flag (default on); it should only be disabled in trusted dev/test
environments.

### User Settings (Persistent)
- **Theme**: System (follows OS) / Light / Dark
- **Temperature Units**: Celsius/Fahrenheit
- **Cloud Clip Retention**: 3-60 days auto-deletion
- **Local Clip Retention**: Never or 3-60 days auto-deletion
- **Clip Thumbnail Size**: Small/Medium/Large display options
- **Save all Live Views**: When on, new live views start with Save enabled

### Cache Settings
- **Clips cache**: 100 items (configurable)
- **Thumbnail cache**: Persistent with timestamp tracking
- **Settings cache**: Persistent across sessions

## File Structure

```
blinkpy-flask/
├── blinkapp/           # Main Flask application package
│   ├── __main__.py    # CLI entry point
│   ├── __init__.py    # Flask app instance and route registration
│   ├── config.py      # Configuration management
│   ├── services/      # Business logic services (Phase 2 reorganized)
│   │   ├── auth_service.py        # Authentication and 2FA handling
│   │   ├── blink_connection.py    # Async Blink connection management
│   │   ├── cache_service.py       # Cache initialization and management
│   │   ├── clip_service.py        # Cloud and local clip operations
│   │   ├── device_service.py      # Device data formatting utilities
│   │   ├── debug_service.py       # System debugging and diagnostics
│   │   ├── stream_service.py      # Live streaming coordination
│   │   ├── hls_service.py         # HLS transcoding with FFmpeg
│   │   └── ...                    # Additional specialized services
│   ├── routes/        # Flask route handlers (thin wrappers over connexion_handlers)
│   │   ├── auth.py    # Authentication routes
│   │   ├── camera.py  # Camera + thumbnail + streaming routes
│   │   ├── clips.py   # Clip listing/download routes
│   │   ├── system.py  # System (arm/disarm) routes
│   │   ├── settings.py, admin.py, logs.py, thumbnails.py, streaming.py
│   │   └── ...        # (no single api.py; endpoints are split by domain)
│   ├── connexion_handlers/  # Business-logic handlers the routes delegate to
│   ├── utils/         # Utility functions and helpers
│   │   ├── decorators.py          # Function decorators
│   │   ├── validators.py          # Input validation
│   │   ├── formatters.py          # Data formatting utilities
│   │   └── ...                    # Additional utilities
│   └── models/        # Data models and type definitions
├── pyproject.toml      # Project metadata, dependencies, and tool config
├── requirements.txt    # Thin wrapper: installs the project via pyproject
├── templates/          # HTML templates
│   ├── base.html      # Base template with responsive CSS
│   ├── index.html     # Main SPA with clips, settings, live view
│   └── auth.html      # Unified login/2FA authentication
├── cache/             # Application cache (auto-created)
│   ├── blink.json     # Cached Blink auth tokens (plaintext JSON via blinkpy)
│   ├── settings.json  # User preferences (persistent)
│   ├── blink_app.log  # Application logs (rotated)
│   ├── thumbnails/    # Camera thumbnail cache with timestamps
│   └── clips/         # Downloaded clips cache with thumbnails
├── recordings/        # Saved live-view recordings (MP4 + JSON sidecar + thumbnail), separate from cache
└── README.md          # This file
```

## Production Deployment

### WSGI Server
```bash
# Install production server
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 "blinkapp:app"
```

### Security Considerations
- Set strong `SECRET_KEY` environment variable
- Use HTTPS in production
- Configure firewall rules
- Regular security updates
- Monitor log files

### Performance Tuning
- Adjust cache sizes in `Config` class
- Configure FFmpeg parameters for TCP to HLS transcoding
- Monitor disk usage for clip cache
- Set appropriate timeout values

## Type Stubs

This project includes comprehensive type stubs for the blinkpy library in the `types-blinkpy/` directory. These provide full type safety and IDE support.

### Installing Type Stubs

```bash
# Install locally for this project
pip install -e types-blinkpy/

# Or build and install as a package
cd types-blinkpy/
pip install .
```

### Using in Other Projects

The `types-blinkpy` package can be installed alongside any blinkpy installation:

```bash
pip install blinkpy types-blinkpy
```

This provides type checking for blinkpy in any Python project without conflicts.

## Troubleshooting

### Common Issues
- **FFmpeg not found**: Install FFmpeg and ensure it's in PATH
- **2FA timeout**: Check email/SMS and enter code quickly
- **Cache full**: Use the `DELETE /api/cache` endpoint or clear cache in Settings
- **Stream fails**: Check camera connectivity and TCP stream availability
- **Local clips not loading**: Ensure USB storage is connected and accessible
- **Thumbnails not updating**: Use "Update All" button for local clips

### Logging
- Application logs: `cache/blink_app.log` (rotated)
- Debug mode: `python -m blinkapp --debug`
- Log levels: `python -m blinkapp --log-level DEBUG`
- System dump: `python -m blinkapp --dump-system` (requires login)

## Technical Architecture

### Thread Safety
- Dedicated asyncio thread for Blink operations
- Thread-safe caching with proper locking
- Resource cleanup on shutdown

### Performance Features
- **Intelligent caching**: fewer repeated API calls via timestamp tracking
- **Background processing**: Sequential clip processing with thumbnail generation
- **FIFO management**: Automatic cache cleanup with configurable retention
- **Stream cleanup**: Live streams stop their FFmpeg process and remove HLS segments on stop, client disconnect, idle timeout, and shutdown, so transcoding processes and temp files are not leaked
- **Mobile optimization**: Compact UI with reduced spacing and font sizes

### Error Handling
- Comprehensive input validation
- Graceful degradation on failures
- Detailed error logging

## Development

### Code Architecture

The project has undergone a comprehensive **Phase 2 reorganization** to improve maintainability and separation of concerns:

#### Services Directory Reorganization
- **Cache services consolidated**: Merged `cache_management.py` functionality into `cache_service.py`
- **Utils service split**: Divided `utils_service.py` into specialized modules:
  - `device_service.py`: Device data formatting and utilities
  - `debug_service.py`: System debugging and diagnostics
- **Connection service extracted**: Moved `BlinkConnection` class to dedicated `blink_connection.py` module
- **Authentication clarity**: Renamed functions for clear distinction:
  - `is_session_authenticated()`: Web session authentication
  - `is_blink_authenticated()`: Blink API authentication

#### Benefits of Reorganization
- **Better separation of concerns**: Each service has a focused responsibility
- **Improved testability**: Smaller, more focused modules are easier to test
- **Enhanced maintainability**: Clear module boundaries reduce coupling
- **Type safety improvements**: Better type checking with focused imports

### Code Quality
- **Type hints**: Complete type safety with protocols
- **Documentation**: Comprehensive docstrings and comments
- **Error handling**: Consistent patterns with context managers
- **Security**: Input validation and XSS prevention
- **Architecture**: Clean separation of concerns with dedicated classes

## Testing

### Test Suite Overview
The project includes a comprehensive test suite with **~72% code coverage** and **796 passing tests** across multiple test files.

### Complete Test Isolation
Tests run in **complete isolation** with automatic file system protection:
- **Zero source directory pollution**: Tests cannot create files in the project directory
- **Automatic redirection**: All file operations redirected to temporary directories
- **Cross-platform**: Works on Windows, macOS, and Linux
- **pytest-native**: Uses `tmp_path` fixture with `autouse=True` for seamless isolation

### Quick Start
```bash
# Run all tests (automatically isolated)
pytest

# Run with coverage
pytest --cov=blinkapp --cov-report=html

# Run specific test suites by marker
pytest -m core                             # Core application tests

# Run specific test files
pytest tests/test_app.py                    # Core application + API endpoints
pytest tests/test_services.py               # Service-layer logic
pytest tests/test_auth_guard.py             # /api authentication guard
pytest tests/test_liveview_recording.py     # Live-view recording

# Run with verbose output
pytest -v
```

### Regression Testing

The project uses a baseline-driven regression testing system to detect test failures and ensure code quality.

#### Checking for Regressions
```bash
# Check current test results against baseline
cd tests
python check_test_baseline.py
```

This will:
- ✅ **Pass**: No regressions detected
- ⚠️ **Warn**: New tests added (update baseline needed)
- ❌ **Fail**: Regressions detected (tests that were passing now fail)

#### Updating Test Baseline
When you add new tests or expect test changes:

```bash
# Update baseline with current passing tests
cd tests
python update_test_baseline.py
```

**Note**: The baseline contains only passing test names, sorted alphabetically.

#### Regression Check Output
```bash
🔍 Checking test results against baseline...

📊 Current: <N> passing tests
📊 Baseline: <N> tests

✅ NO CHANGES: All tests match baseline
```

#### Integration with CI/CD
Add to your CI pipeline:
```bash
cd tests && python check_test_baseline.py
```

The script exits with:
- `0`: No regressions (safe to deploy)
- `1`: Regressions detected (block deployment)

### Using pytest directly
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_app.py

# Run with coverage
pytest --cov=blinkapp --cov-report=term-missing

# Generate HTML coverage report
pytest --cov=blinkapp --cov-report=html --cov-report=term
```

### Test Options
```bash
# Basic usage
pytest                                     # All tests
pytest --cov=blinkapp --cov-report=html   # With HTML coverage
pytest -v                                 # Verbose output
pytest -q                                 # Quiet output

# Specific test files
pytest tests/test_app.py                   # Core application + API endpoints
pytest tests/test_services.py              # Service-layer logic
pytest tests/test_auth_guard.py            # /api authentication guard
pytest tests/test_liveview_recording.py    # Live-view recording

# Additional options
pytest --disable-warnings                 # Suppress warnings
```

### Test Coverage Status
- **Coverage**: ~72% of statements
- **Passing Tests**: 796 (all passing)

### Test Architecture
- **Complete Isolation**: `conftest.py` with `autouse=True` fixture provides automatic file system isolation
- **Core Tests** (`test_app.py`): Main application functionality, API endpoints, authentication
- **Service Tests** (`test_services.py`): Service-layer logic (auth, streaming, clips, cache)
- **Auth Guard** (`test_auth_guard.py`): `/api/*` authentication guard behavior
- **Live-View Recording** (`test_liveview_recording.py`): recording lifecycle and clip-list integration

For detailed testing documentation, see [`tests/README.md`](tests/README.md).

### Development Tools
```bash
# Install development dependencies
pip install coverage pytest pytest-cov ruff pre-commit

# Code quality checks
ruff check .          # Lint code
ruff format .         # Format code
ruff check --fix .    # Auto-fix issues

# Pre-commit hooks
pre-commit install    # Install git hooks
pre-commit run --all-files  # Run on all files

# Run in debug mode
python -m blinkapp --debug

# Test API endpoints
curl http://localhost:5001/api/systems
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
