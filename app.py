#!/usr/bin/env python3
"""Flask web server for Blink camera system."""

import sys
import os
import asyncio
import threading
import queue
import subprocess
import tempfile
import atexit
import signal
from datetime import datetime
from typing import Optional, Union, TYPE_CHECKING, Any, Dict, List, Tuple
from threading import Lock
import re
from functools import wraps

# Add the blinkpy directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'blinkpy'))

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from flask import Response as FlaskResponse

if TYPE_CHECKING:
    from werkzeug.wrappers import Response
else:
    Response = Any

try:
    from blinkpy.blinkpy import Blink  # type: ignore
    from blinkpy.auth import Auth  # type: ignore
except ImportError:
    Blink = None  # type: ignore
    Auth = None  # type: ignore
import logging

# Configuration constants
class Config:
    # Cache settings
    CLIPS_CACHE_SIZE = 50
    THUMBNAIL_CACHE_TIMEOUT = 3600  # 1 hour
    
    # FFmpeg settings
    FFMPEG_TIMEOUT = 30
    FFPROBE_TIMEOUT = 10
    HLS_SEGMENT_TIME = 2
    HLS_LIST_SIZE = 3
    
    # Process settings
    PROCESS_TERMINATE_TIMEOUT = 5
    BLINK_OPERATION_TIMEOUT = 30
    
    # API settings
    MAX_VIDEOS_METADATA = 50
    CLIPS_PER_STORAGE_TYPE = 5
    
    # File settings
    LOG_FILE = 'blink_app.log'
    SECRET_KEY = 'your-secret-key-here'
    
    # Validation settings
    MAX_USERNAME_LENGTH = 100
    MAX_PASSWORD_LENGTH = 100
    MAX_2FA_LENGTH = 10
    VALID_CAMERA_ID_PATTERN = r'^[a-zA-Z0-9_-]+$'
    VALID_NETWORK_ID_PATTERN = r'^[0-9]+$'
    VALID_CLIP_ID_PATTERN = r'^[a-zA-Z0-9_:-]+$'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Config.LOG_FILE)
    ]
)
logger = logging.getLogger(__name__)

# Enable blinkpy debug logging to trace API calls
logging.getLogger('blinkpy').setLevel(logging.DEBUG)
# Suppress asyncio unclosed session warnings
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

def validate_string_input(value: str, max_length: int, field_name: str) -> str:
    """Validate string input for length and basic safety.
    
    Args:
        value: Input string to validate
        max_length: Maximum allowed length
        field_name: Name of field for error messages
        
    Returns:
        Validated and stripped string
        
    Raises:
        ValueError: If validation fails
    """
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} cannot be empty")
    
    if len(value) > max_length:
        raise ValueError(f"{field_name} too long (max {max_length} characters)")
    
    # Basic XSS prevention
    if '<' in value or '>' in value or '&' in value:
        raise ValueError(f"{field_name} contains invalid characters")
    
    return value

def create_api_response(success: bool = True, data: Any = None, error: str = None, status_code: int = 200) -> Tuple[Dict[str, Any], int]:
    """Create standardized API response format.
    
    Args:
        success: Whether the operation was successful
        data: Response data (for successful operations)
        error: Error message (for failed operations)
        status_code: HTTP status code
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    response = {
        'success': success,
        'timestamp': datetime.now().isoformat()
    }
    
    if success and data is not None:
        response['data'] = data
    elif not success and error:
        response['error'] = error
    
    return response, status_code

def find_camera_by_id(camera_id: str) -> Optional[Any]:
    """Find camera by ID across all sync modules.
    
    Args:
        camera_id: Camera ID to search for
        
    Returns:
        Camera object if found, None otherwise
    """
    if not blink or not blink.available:
        return None
    
    for sync_name, sync in blink.sync.items():
        for cam_name, cam in sync.cameras.items():
            if str(cam.camera_id) == str(camera_id):
                return cam
    return None

def handle_api_error(error: Exception, operation: str, status_code: int = 500) -> Tuple[Dict[str, Any], int]:
    """Handle API errors consistently.
    
    Args:
        error: Exception that occurred
        operation: Description of operation that failed
        status_code: HTTP status code to return
        
    Returns:
        Standardized error response tuple
    """
    logger.error(f"Error {operation}: {error}")
    return create_api_response(success=False, error=str(error), status_code=status_code)

def validate_id_format(value: str, pattern: str, field_name: str) -> str:
    """Validate ID format against regex pattern.
    
    Args:
        value: ID string to validate
        pattern: Regex pattern to match
        field_name: Name of field for error messages
        
    Returns:
        Validated ID string
        
    Raises:
        ValueError: If validation fails
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} cannot be empty")
    
    value = value.strip()
    if not re.match(pattern, value):
        raise ValueError(f"Invalid {field_name} format")
    
    return value

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', Config.SECRET_KEY)

# Global Blink instance and thread
blink: Optional['Blink'] = None
blink_thread: Optional[threading.Thread] = None
blink_loop: Optional[asyncio.AbstractEventLoop] = None
# Cache configuration - will be set from command line
CACHE_DIR = 'cache'  # Default, overridden by Flask config
CREDENTIALS_FILE = None  # Set in get_cache_paths()
THUMBNAIL_CACHE_DIR = None  # Set in get_cache_paths()
CLIPS_CACHE_DIR = None  # Set in get_cache_paths()
thumbnail_cache: Dict[str, Dict[str, Union[int, str]]] = {}  # {camera_id: {'timestamp': int, 'filename': str}}
thumbnail_cache_lock: Lock = Lock()  # Thread safety for thumbnail cache

def get_cache_paths() -> None:
    """Initialize cache directory paths from Flask config or defaults.
    
    Sets global path variables for cache directories and credential file.
    Uses Flask app config 'CACHE_DIR' or defaults to 'cache'.
    """
    global CACHE_DIR, CREDENTIALS_FILE, THUMBNAIL_CACHE_DIR, CLIPS_CACHE_DIR
    CACHE_DIR = app.config.get('CACHE_DIR', 'cache')
    CREDENTIALS_FILE = os.path.join(CACHE_DIR, 'blink.json')
    THUMBNAIL_CACHE_DIR = os.path.join(CACHE_DIR, 'thumbnails')
    CLIPS_CACHE_DIR = os.path.join(CACHE_DIR, 'clips')

# Clips cache configuration
CLIPS_CACHE_SIZE = Config.CLIPS_CACHE_SIZE  # Maximum number of clips to cache
clips_cache: Dict[str, Dict[str, Any]] = {}  # {storage_type: {'data': clips_data, 'timestamp': timestamp}}
clips_cache_order: List[str] = []  # FIFO order tracking
clips_cache_lock: Lock = Lock()  # Thread safety for clips cache

# Downloaded clips cache
downloaded_clips_cache: Dict[str, Dict[str, str]] = {}  # {clip_id: {'filepath': str, 'thumbnail': str}}
downloaded_clips_order: List[str] = []  # FIFO order for downloaded clips
downloaded_clips_lock: Lock = Lock()  # Thread safety for downloaded clips cache

# Live stream processes
live_streams: Dict[str, Dict[str, Any]] = {}  # {camera_id: {'process': subprocess, 'hls_dir': path}}
live_streams_lock: Lock = Lock()  # Thread safety for live streams

def run_blink_thread() -> None:
    """Run Blink operations in dedicated thread with persistent event loop.
    
    Creates and runs a new asyncio event loop in the current thread.
    This loop handles all Blink API operations asynchronously while
    keeping the main Flask thread responsive.
    """
    global blink_loop
    blink_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(blink_loop)
    blink_loop.run_forever()

def run_in_blink_thread(coro) -> Any:
    """Execute coroutine in the Blink thread and return result.
    
    Args:
        coro: Coroutine to execute in the Blink event loop
        
    Returns:
        Result of the coroutine execution, or None if loop unavailable
        
    Raises:
        TimeoutError: If operation exceeds configured timeout
        Exception: Any exception raised by the coroutine
    """
    global blink_loop
    if not blink_loop:
        return None
    future = asyncio.run_coroutine_threadsafe(coro, blink_loop)
    return future.result(timeout=Config.BLINK_OPERATION_TIMEOUT)



async def initialize_blink(username: str, password: str) -> Union[bool, str]:
    """Initialize Blink system following blinkpy README.
    
    Args:
        username: Blink account username/email
        password: Blink account password
        
    Returns:
        True if successful, '2fa_required' if 2FA needed, False if failed
    """
    global blink
    try:
        blink = Blink()
        auth = Auth({"username": username, "password": password}, no_prompt=True)
        blink.auth = auth
        await blink.start()
        
        # Check if 2FA is required
        if blink.key_required:
            logger.info("2FA key required - check your email or SMS")
            return '2fa_required'
        
        logger.info("Blink system initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing Blink: {e}")
        return False

async def verify_2fa_and_save(username: str, password: str, two_fa_key: str) -> bool:
    """Verify 2FA code and save credentials in same thread as Blink creation.
    
    Args:
        username: Blink account username (unused but kept for consistency)
        password: Blink account password (unused but kept for consistency)
        two_fa_key: 2FA verification code from email/SMS
        
    Returns:
        True if verification successful, False otherwise
    """
    global blink
    try:
        logger.debug(f"Starting 2FA verification with key: {two_fa_key[:2]}***")
        
        # Send 2FA key using same session/thread
        logger.debug("Sending 2FA key...")
        await blink.auth.send_auth_key(blink, two_fa_key)
        
        logger.debug("Setting up post verification...")
        await blink.setup_post_verify()
        
        logger.debug("Saving credentials...")
        await blink.save(CREDENTIALS_FILE)
        
        logger.info("2FA verification and save completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error verifying 2FA: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False

def format_time_ago(timestamp_str: Optional[str]) -> str:
    """Format timestamp as 'Xd ago' format.
    
    Args:
        timestamp_str: ISO format timestamp string or None
        
    Returns:
        Formatted time string like '5d ago', '2h ago', '30m ago', or 'Unknown'
    """
    try:
        if not timestamp_str:
            return "Unknown"
        # Parse the timestamp
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now(timestamp.tzinfo)
        diff = now - timestamp
        days = diff.days
        if days == 0:
            hours = diff.seconds // 3600
            if hours == 0:
                minutes = diff.seconds // 60
                return f"{minutes}m ago"
            return f"{hours}h ago"
        return f"{days}d ago"
    except:
        return "Unknown"

@app.route('/')
def index() -> Response:
    """Main page - redirect to login if not authenticated.
    
    Returns:
        Redirect to login page or rendered index template
    """
    if 'authenticated' not in session:
        # Check if Blink is available from saved credentials
        if blink and blink.available:
            session['authenticated'] = True
        else:
            return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login() -> Response:
    """Handle login page GET/POST requests.
    
    Returns:
        Login form template or redirect based on authentication result
    """
    if request.method == 'POST':
        try:
            username = validate_string_input(
                request.form.get('username', ''), 
                Config.MAX_USERNAME_LENGTH, 
                'Username'
            )
            password = validate_string_input(
                request.form.get('password', ''), 
                Config.MAX_PASSWORD_LENGTH, 
                'Password'
            )
        except ValueError as e:
            return render_template('login.html', error=str(e))
        
        # Initialize Blink thread if needed
        global blink_thread
        if not blink_thread or not blink_thread.is_alive():
            blink_thread = threading.Thread(target=run_blink_thread, daemon=True)
            blink_thread.start()
            import time
            time.sleep(0.1)  # Give thread time to start
        
        try:
            success = run_in_blink_thread(initialize_blink(username, password))
            
            if success == '2fa_required':
                session['temp_username'] = username
                session['temp_password'] = password
                return redirect(url_for('two_factor'))
            elif success:
                run_in_blink_thread(blink.save(CREDENTIALS_FILE))
                session['authenticated'] = True
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error='Invalid credentials')
        except Exception as e:
            logger.error(f"Login error: {e}")
            return render_template('login.html', error='Login failed. Please try again.')
    
    return render_template('login.html')

@app.route('/2fa', methods=['GET', 'POST'])
def two_factor() -> Response:
    """Handle 2FA verification page GET/POST requests.
    
    Returns:
        2FA form template or redirect based on verification result
    """
    if 'temp_username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            key = validate_string_input(
                request.form.get('key', ''), 
                Config.MAX_2FA_LENGTH, 
                '2FA code'
            )
            username = session['temp_username']
            password = session['temp_password']
        except ValueError as e:
            return render_template('2fa.html', error=str(e), email=session.get('temp_username', ''))
        
        try:
            logger.debug("Running 2FA verification in Blink thread")
            success = run_in_blink_thread(verify_2fa_and_save(username, password, key))
            
            if success:
                logger.debug("2FA successful, clearing session and redirecting")
                session.pop('temp_username', None)
                session.pop('temp_password', None)
                session['authenticated'] = True
                return redirect(url_for('index'))
            else:
                logger.debug("2FA failed, showing error")
                return render_template('2fa.html', error='Invalid 2FA code')
        except Exception as e:
            logger.error(f"2FA route error: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return render_template('2fa.html', error='2FA verification failed')
    
    return render_template('2fa.html', email=session.get('temp_username', ''))

@app.route('/api/clear-cache', methods=['POST'])
def clear_cache():
    """Clear all caches except credentials."""
    try:
        # Clear thumbnail cache
        global thumbnail_cache
        if os.path.exists(THUMBNAIL_CACHE_DIR):
            import shutil
            shutil.rmtree(THUMBNAIL_CACHE_DIR)
            os.makedirs(THUMBNAIL_CACHE_DIR, exist_ok=True)
        with thumbnail_cache_lock:
            thumbnail_cache.clear()
        
        # Clear downloaded clips cache
        global downloaded_clips_cache, downloaded_clips_order
        if os.path.exists(CLIPS_CACHE_DIR):
            import shutil
            shutil.rmtree(CLIPS_CACHE_DIR)
            os.makedirs(CLIPS_CACHE_DIR, exist_ok=True)
        with downloaded_clips_lock:
            downloaded_clips_cache.clear()
            downloaded_clips_order.clear()
        
        # Clear clips metadata cache
        global clips_cache, clips_cache_order
        with clips_cache_lock:
            clips_cache.clear()
            clips_cache_order.clear()
        
        logger.info("All caches cleared successfully")
        response, status_code = create_api_response(success=True, data={'message': 'Cache cleared successfully'})
        return jsonify(response), status_code
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        response, status_code = create_api_response(success=False, error=str(e), status_code=500)
        return jsonify(response), status_code

@app.route('/logout', methods=['POST'])
def logout() -> Response:
    """Logout user and clear all credentials and caches.
    
    Returns:
        JSON response indicating success
    """
    global blink
    
    # Clear caches first
    try:
        clear_cache()
    except Exception as e:
        logger.warning(f"Error clearing cache during logout: {e}")
    
    # Clear session and credentials
    session.clear()
    blink = None
    if os.path.exists(CREDENTIALS_FILE):
        os.remove(CREDENTIALS_FILE)
    
    response, status_code = create_api_response(success=True, data={'message': 'Logged out successfully'})
    return jsonify(response), status_code

@app.route('/api/systems')
def get_systems() -> Response:
    """Get list of available Blink systems.
    
    Returns:
        JSON response with list of systems or error message
    """
    if not blink:
        logger.debug("Blink object is None")
        response, status_code = create_api_response(success=False, error='Blink not available - please login', status_code=401)
        return jsonify(response), status_code
    
    if not blink.available:
        logger.debug(f"Blink not available - auth: {blink.auth}, networks: {len(blink.networks) if hasattr(blink, 'networks') else 'N/A'}")
        response, status_code = create_api_response(success=False, error='Blink not available - please login', status_code=401)
        return jsonify(response), status_code
    
    try:
        logger.debug(f"Getting systems - sync count: {len(blink.sync)}")
        systems = []
        for name, sync in blink.sync.items():
            logger.debug(f"Processing sync: {name}, network_id: {sync.network_id}")
            systems.append({
                'name': name,
                'network_id': sync.network_id,
                'armed': sync.arm,
                'online': sync.online
            })
        
        response, status_code = create_api_response(success=True, data=systems)
        return jsonify(response), status_code
    except Exception as e:
        logger.error(f"Error getting systems: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        response, status_code = create_api_response(success=False, error=f'Error: {str(e)}', status_code=500)
        return jsonify(response), status_code

@app.route('/api/devices/<network_id>')
def get_devices(network_id: str) -> Response:
    try:
        network_id = validate_id_format(network_id, Config.VALID_NETWORK_ID_PATTERN, 'Network ID')
    except ValueError as e:
        response, status_code = create_api_response(success=False, error=str(e), status_code=400)
        return jsonify(response), status_code
    """Get devices for a specific Blink system.
    
    Args:
        network_id: Network ID of the Blink system
        
    Returns:
        JSON response with list of devices or error message
    """
    if not blink or not blink.available:
        response, status_code = create_api_response(success=False, error='Blink not available - please login', status_code=401)
        return jsonify(response), status_code
    
    devices = []
    
    # Find the sync module for this network
    sync_module = None
    for name, sync in blink.sync.items():
        if str(sync.network_id) == str(network_id):
            sync_module = sync
            break
    
    if not sync_module:
        response, status_code = create_api_response(success=False, error='System not found', status_code=404)
        return jsonify(response), status_code
    
    # Add sync module
    devices.append({
        'type': 'sync_module',
        'name': 'Sync Module',
        'online': sync_module.online,
        'id': sync_module.sync_id
    })
    
    # Add cameras - refresh thumbnails in Blink thread
    for camera_name, camera in sync_module.cameras.items():
        logger.debug(f"Processing camera: {camera.name}, current thumbnail: {camera.thumbnail}")
        
        # Extract timestamp from thumbnail URL
        current_ts = 0
        if camera.thumbnail:
            try:
                import re
                match = re.search(r'ts=([0-9]+)', camera.thumbnail)
                if match:
                    current_ts = int(match.group(1))
            except Exception as e:
                logger.debug(f"Could not parse thumbnail timestamp for {camera.name}: {e}")
        
        # Check if we need to update cached thumbnail
        cache_key = camera.camera_id
        
        # Format last updated time from cached or current timestamp
        with thumbnail_cache_lock:
            display_ts = thumbnail_cache.get(cache_key, {}).get('timestamp', current_ts)
        last_updated = "Never"
        if display_ts > 0:
            try:
                thumbnail_time = datetime.fromtimestamp(display_ts)
                now = datetime.now()
                diff = now - thumbnail_time
                days = diff.days
                if days == 0:
                    hours = diff.seconds // 3600
                    if hours == 0:
                        minutes = diff.seconds // 60
                        last_updated = f"{minutes}m ago"
                    else:
                        last_updated = f"{hours}h ago"
                else:
                    last_updated = f"{days}d ago"
            except Exception as e:
                logger.debug(f"Could not format timestamp for {camera.name}: {e}")
                last_updated = format_time_ago(camera.last_record) if camera.last_record else "Never"
        with thumbnail_cache_lock:
            cached_ts = thumbnail_cache.get(cache_key, {}).get('timestamp', 0)
        
        if current_ts > cached_ts:
            logger.debug(f"Updating thumbnail cache for {camera.name} (ts: {current_ts} > {cached_ts})")
            try:
                # Remove old cached file if exists
                with thumbnail_cache_lock:
                    if cache_key in thumbnail_cache:
                        old_filename = thumbnail_cache[cache_key].get('filename')
                        if old_filename:
                            old_filepath = os.path.join(THUMBNAIL_CACHE_DIR, old_filename)
                            if os.path.exists(old_filepath):
                                os.remove(old_filepath)
                                logger.debug(f"Removed old thumbnail file: {old_filename}")
                
                thumbnail_response = run_in_blink_thread(camera.get_thumbnail())
                if thumbnail_response and thumbnail_response.status == 200:
                    image_data = run_in_blink_thread(thumbnail_response.read())
                    
                    # Save to file with new timestamp
                    filename = f"{cache_key}_{current_ts}.jpg"
                    filepath = os.path.join(THUMBNAIL_CACHE_DIR, filename)
                    try:
                        with open(filepath, 'wb') as f:
                            f.write(image_data)
                    except IOError as e:
                        logger.error(f"Error writing thumbnail file {filepath}: {e}")
                        raise
                    
                    # Update cache info
                    with thumbnail_cache_lock:
                        thumbnail_cache[cache_key] = {
                            'timestamp': current_ts,
                            'filename': filename
                        }
                    logger.debug(f"Cached thumbnail for {camera.name} with timestamp {current_ts}")
            except Exception as e:
                logger.warning(f"Could not cache thumbnail for {camera.name}: {e}")
        else:
            logger.debug(f"Using cached thumbnail for {camera.name} (ts: {current_ts} <= {cached_ts})")
        
        device_data = {
            'type': 'camera',
            'name': camera.name,
            'id': camera.camera_id,
            'thumbnail': f'/api/media/thumbnail/{camera.camera_id}',  # Use proxy URL
            'last_updated': last_updated,
            'motion_enabled': camera.motion_enabled,
            'battery': camera.battery,
            'temperature': camera.temperature,
            'wifi_strength': camera.wifi_strength
        }
        logger.debug(f"Camera device data for {camera.name}: {device_data}")
        devices.append(device_data)
    
    response, status_code = create_api_response(success=True, data=devices)
    return jsonify(response), status_code

@app.route('/api/system/<network_id>/arm', methods=['POST'])
def arm_system(network_id: str) -> Response:
    try:
        network_id = validate_id_format(network_id, Config.VALID_NETWORK_ID_PATTERN, 'Network ID')
    except ValueError as e:
        response, status_code = create_api_response(success=False, error=str(e), status_code=400)
        return jsonify(response), status_code
    """Arm or disarm a Blink system.
    
    Args:
        network_id: Network ID of the system to arm/disarm
        
    Returns:
        JSON response with success status or error message
    """
    if not blink or not blink.available:
        response, status_code = create_api_response(success=False, error='Blink not available', status_code=500)
        return jsonify(response), status_code
    
    try:
        data = request.get_json()
        if not isinstance(data, dict):
            response, status_code = create_api_response(success=False, error='Invalid JSON data', status_code=400)
            return jsonify(response), status_code
        
        armed = data.get('armed')
        if not isinstance(armed, bool):
            response, status_code = create_api_response(success=False, error='Armed status must be boolean', status_code=400)
            return jsonify(response), status_code
    except Exception as e:
        response, status_code = create_api_response(success=False, error='Invalid request data', status_code=400)
        return jsonify(response), status_code
    
    # Find the sync module
    sync_module = None
    for name, sync in blink.sync.items():
        if str(sync.network_id) == str(network_id):
            sync_module = sync
            break
    
    if not sync_module:
        response, status_code = create_api_response(success=False, error='System not found', status_code=404)
        return jsonify(response), status_code
    
    try:
        run_in_blink_thread(sync_module.async_arm(armed))
        response, status_code = create_api_response(success=True, data={'armed': armed})
        return jsonify(response), status_code
    except Exception as e:
        response, status_code = handle_api_error(e, 'arming/disarming system')
        return jsonify(response), status_code

@app.route('/api/camera/<camera_id>/refresh', methods=['POST'])
def refresh_camera(camera_id: str):
    try:
        camera_id = validate_id_format(camera_id, Config.VALID_CAMERA_ID_PATTERN, 'Camera ID')
    except ValueError as e:
        response, status_code = create_api_response(success=False, error=str(e), status_code=400)
        return jsonify(response), status_code
    
    """Refresh camera thumbnail."""
    if not blink or not blink.available:
        response, status_code = create_api_response(success=False, error='Blink not available', status_code=500)
        return jsonify(response), status_code
    
    camera = find_camera_by_id(camera_id)
    if not camera:
        response, status_code = create_api_response(success=False, error='Camera not found', status_code=404)
        return jsonify(response), status_code
    
    try:
        # Remove camera thumbnail from cache
        cache_key = camera.camera_id
        with thumbnail_cache_lock:
            if cache_key in thumbnail_cache:
                cached_info = thumbnail_cache[cache_key]
                # Remove cached file
                if 'filename' in cached_info:
                    cached_file = os.path.join(THUMBNAIL_CACHE_DIR, cached_info['filename'])
                    if os.path.exists(cached_file):
                        os.remove(cached_file)
                # Remove from cache
                del thumbnail_cache[cache_key]
        
        run_in_blink_thread(camera.snap_picture())
        response, status_code = create_api_response(success=True, data={'message': 'Thumbnail refresh initiated'})
        return jsonify(response), status_code
    except Exception as e:
        response, status_code = handle_api_error(e, 'refreshing camera')
        return jsonify(response), status_code

@app.route('/api/clips')
def get_clips():
    """Get clips from cloud or local storage."""
    if not blink or not blink.available:
        response, status_code = create_api_response(success=False, error='Blink not available', status_code=500)
        return jsonify(response), status_code
    
    storage_type = request.args.get('storage', 'cloud')
    if storage_type not in ['cloud', 'local']:
        response, status_code = create_api_response(success=False, error='Invalid storage type. Must be "cloud" or "local"', status_code=400)
        return jsonify(response), status_code
    
    # Check cache first for performance
    cache_key = storage_type
    current_time = datetime.now().timestamp()
    with clips_cache_lock:
        if cache_key in clips_cache:
            cached_data = clips_cache[cache_key]
            if current_time - cached_data['timestamp'] < 300:  # 5 minutes cache
                response, status_code = create_api_response(success=True, data=cached_data['data'])
                return jsonify(response), status_code
    
    clips = []
    
    try:
        if storage_type == 'cloud':
            # Get cloud clips in Blink thread
            videos_metadata = run_in_blink_thread(blink.get_videos_metadata(stop=Config.CLIPS_PER_STORAGE_TYPE))
            
            # Group clips by day
            clips_by_day = {}
            for video in videos_metadata:
                try:
                    created_at = datetime.fromisoformat(video['created_at'].replace('Z', '+00:00'))
                    day_key = created_at.strftime('%Y-%m-%d')
                    
                    if day_key not in clips_by_day:
                        clips_by_day[day_key] = {
                            'date': created_at.strftime('%B %d, %Y'),
                            'clips': []
                        }
                    
                    clip_id = str(video.get('id'))
                    thumbnail_url = video.get('thumbnail')
                    
                    # Check if we have a cached thumbnail for cloud clips
                    if clip_id in downloaded_clips_cache:
                        cached_thumbnail = downloaded_clips_cache[clip_id]['thumbnail']
                        if cached_thumbnail and os.path.exists(cached_thumbnail):
                            thumbnail_url = f'/api/clip/{clip_id}/thumbnail'
                    
                    clips_by_day[day_key]['clips'].append({
                        'id': clip_id,
                        'camera_name': video.get('device_name', 'Unknown'),
                        'system_name': 'Blink System',  # Could be enhanced to get actual system name
                        'time': created_at.astimezone().strftime('%I:%M %p'),
                        'event_type': 'Motion',
                        'thumbnail': thumbnail_url,
                        'media_url': video.get('media')
                    })
                except Exception as e:
                    logger.error(f"Error processing video metadata: {e}")
                    continue
            
            # Convert to list format expected by frontend
            clips = []
            for day_key in sorted(clips_by_day.keys(), reverse=True):
                day_data = clips_by_day[day_key]
                day_data['clips'].sort(key=lambda x: x['time'], reverse=True)
                day_data['count'] = len(day_data['clips'])
                clips.append(day_data)
                
        else:
            # Get local storage clips from sync modules
            clips_by_day = {}
            
            for sync_name, sync_module in blink.sync.items():
                try:
                    # Refresh sync module to update local storage manifest
                    run_in_blink_thread(sync_module.refresh())
                    
                    # Get clips from local storage manifest if ready
                    if sync_module.local_storage and sync_module.local_storage_manifest_ready:
                        manifest = sync_module._local_storage['manifest']
                        for item in manifest:
                            try:
                                created_at = item.created_at
                                day_key = created_at.strftime('%Y-%m-%d')
                                
                                if day_key not in clips_by_day:
                                    clips_by_day[day_key] = {
                                        'date': created_at.strftime('%B %d, %Y'),
                                        'clips': []
                                    }
                                
                                clip_id = f"{sync_name}:{item.id}"
                                
                                # Generate thumbnail if not exists
                                thumbnail_url = None
                                if clip_id in downloaded_clips_cache:
                                    thumbnail_url = f'/api/clip/{clip_id}/thumbnail'
                                else:
                                    # Check if we need to download clip to generate thumbnail
                                    iso_date = created_at.strftime('%Y-%m-%dT%H-%M-%S')
                                    filename = f"{item.name}_{iso_date}.mp4"
                                    filepath = os.path.join(CLIPS_CACHE_DIR, filename)
                                    
                                    if os.path.exists(filepath):
                                        # Generate thumbnail from existing file
                                        thumbnail_path = generate_clip_thumbnail(filepath, filename, middle_frame=True)
                                        if thumbnail_path:
                                            cache_downloaded_clip(clip_id, filepath, thumbnail_path)
                                            thumbnail_url = f'/api/clip/{clip_id}/thumbnail'
                                    else:
                                        # Start background thumbnail generation
                                        generate_thumbnail_async(clip_id, item, sync_module)
                                
                                clips_by_day[day_key]['clips'].append({
                                    'id': clip_id,
                                    'camera_name': item.name,
                                    'system_name': sync_name,
                                    'time': created_at.astimezone().strftime('%I:%M %p'),
                                    'event_type': 'Motion',
                                    'thumbnail': thumbnail_url,
                                    'media_url': item.url(sync_module._local_storage['last_manifest_id'])
                                })
                            except Exception as e:
                                logger.error(f"Error processing local clip metadata: {e}")
                                continue
                except Exception as e:
                    logger.warning(f"Could not get local storage manifest for {sync_name}: {e}")
                    continue
            
            # Convert to list format expected by frontend
            clips = []
            for day_key in sorted(clips_by_day.keys(), reverse=True):
                day_data = clips_by_day[day_key]
                day_data['clips'].sort(key=lambda x: x['time'], reverse=True)
                day_data['count'] = len(day_data['clips'])
                clips.append(day_data)
            
    except Exception as e:
        logger.error(f"Error retrieving clips: {e}")
        response, status_code = create_api_response(success=False, error=str(e), status_code=500)
        return jsonify(response), status_code
    
    # Cache the results with thread safety
    cache_key = storage_type
    current_time = datetime.now().timestamp()
    with clips_cache_lock:
        clips_cache[cache_key] = {
            'data': clips,
            'timestamp': current_time
        }
        
        # Maintain FIFO cache size
        if cache_key not in clips_cache_order:
            clips_cache_order.append(cache_key)
        
        while len(clips_cache_order) > CLIPS_CACHE_SIZE:
            oldest_key = clips_cache_order.pop(0)
            clips_cache.pop(oldest_key, None)
    
    response, status_code = create_api_response(success=True, data=clips)
    return jsonify(response), status_code

@app.route('/api/refresh', methods=['POST'])
def refresh_system():
    """Manually refresh the Blink system."""
    if not blink or not blink.available:
        response, status_code = create_api_response(success=False, error='Blink not available', status_code=500)
        return jsonify(response), status_code
    
    try:
        success = run_in_blink_thread(blink.refresh(force=True))
        
        if success:
            response, status_code = create_api_response(success=True, data={'message': 'System refreshed successfully'})
            return jsonify(response), status_code
        else:
            response, status_code = create_api_response(success=False, error='Failed to refresh system', status_code=500)
            return jsonify(response), status_code
    except Exception as e:
        logger.error(f"Error refreshing system: {e}")
        response, status_code = create_api_response(success=False, error=str(e), status_code=500)
        return jsonify(response), status_code

@app.route('/api/clip/<clip_id>/download')
def download_clip(clip_id: str):
    try:
        clip_id = validate_id_format(clip_id, Config.VALID_CLIP_ID_PATTERN, 'Clip ID')
    except ValueError as e:
        response, status_code = create_api_response(success=False, error=str(e), status_code=400)
        return jsonify(response), status_code
    """Download a specific clip."""
    if not blink or not blink.available:
        response, status_code = create_api_response(success=False, error='Blink not available', status_code=500)
        return jsonify(response), status_code
    
    try:
        # Check if it's a local storage clip (format: sync_name:item_id)
        if ':' in clip_id:
            sync_name, item_id = clip_id.split(':', 1)
            return download_local_clip(sync_name, int(item_id))
        else:
            return download_cloud_clip(clip_id)
    except Exception as e:
        logger.error(f"Error downloading clip: {e}")
        response, status_code = create_api_response(success=False, error=str(e), status_code=500)
        return jsonify(response), status_code

def download_cloud_clip(clip_id):
    """Download cloud storage clip."""
    # Check if already cached
    with downloaded_clips_lock:
        if clip_id in downloaded_clips_cache:
            cached_clip = downloaded_clips_cache[clip_id]
            if os.path.exists(cached_clip['filepath']):
                return send_file(cached_clip['filepath'], as_attachment=True)
    
    # Get clip metadata from cache or API
    videos_metadata = run_in_blink_thread(blink.get_videos_metadata(stop=Config.MAX_VIDEOS_METADATA))
    
    clip_info = None
    for video in videos_metadata:
        if str(video.get('id')) == str(clip_id):
            clip_info = video
            break
    
    if not clip_info:
        response, status_code = create_api_response(success=False, error='Clip not found', status_code=404)
        return jsonify(response), status_code
    
    # Generate filename with camera name and ISO date
    created_at = datetime.fromisoformat(clip_info['created_at'].replace('Z', '+00:00'))
    camera_name = clip_info.get('device_name', 'unknown')
    iso_date = created_at.strftime('%Y-%m-%dT%H-%M-%S')
    filename = f"{camera_name}_{iso_date}.mp4"
    filepath = os.path.join(CLIPS_CACHE_DIR, filename)
    
    # Download clip if not already cached
    if not os.path.exists(filepath):
        media_url = clip_info.get('media')
        if media_url:
            import requests
            response = requests.get(media_url)
            if response.status_code == 200:
                try:
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                except IOError as e:
                    logger.error(f"Error writing clip file {filepath}: {e}")
                    response, status_code = create_api_response(success=False, error='Failed to save clip', status_code=500)
                    return jsonify(response), status_code
                
                # Generate thumbnail from cloud clip
                thumbnail_path = generate_clip_thumbnail(filepath, filename)
                
                # Cache the clip
                cache_downloaded_clip(clip_id, filepath, thumbnail_path)
            else:
                response, status_code = create_api_response(success=False, error='Failed to download clip', status_code=500)
                return jsonify(response), status_code
    
    return send_file(filepath, as_attachment=True, download_name=filename)

def download_local_clip(sync_name, item_id):
    """Download local storage clip using blinkpy methods."""
    clip_id = f"{sync_name}:{item_id}"
    
    # Check if already cached
    with downloaded_clips_lock:
        if clip_id in downloaded_clips_cache:
            cached_clip = downloaded_clips_cache[clip_id]
            if os.path.exists(cached_clip['filepath']):
                return send_file(cached_clip['filepath'], as_attachment=True)
    
    # Find sync module
    sync_module = None
    for name, sync in blink.sync.items():
        if name == sync_name:
            sync_module = sync
            break
    
    if not sync_module:
        response, status_code = create_api_response(success=False, error='Sync module not found', status_code=404)
        return jsonify(response), status_code
    
    # Find the clip item in manifest
    if not sync_module.local_storage or not sync_module.local_storage_manifest_ready:
        response, status_code = create_api_response(success=False, error='Local storage not available', status_code=404)
        return jsonify(response), status_code
    
    manifest = sync_module._local_storage['manifest']
    item = None
    for clip_item in manifest:
        if clip_item.id == item_id:
            item = clip_item
            break
    
    if not item:
        response, status_code = create_api_response(success=False, error='Local clip not found', status_code=404)
        return jsonify(response), status_code
    
    # Generate filename
    iso_date = item.created_at.strftime('%Y-%m-%dT%H-%M-%S')
    filename = f"{item.name}_{iso_date}.mp4"
    filepath = os.path.join(CLIPS_CACHE_DIR, filename)
    
    # Download using blinkpy methods if not cached
    if not os.path.exists(filepath):
        try:
            # Use blinkpy methods as specified
            run_in_blink_thread(item.prepare_download(blink))
            success = run_in_blink_thread(item.download_video(blink, filepath))
            if not success:
                response, status_code = create_api_response(success=False, error='Failed to download local clip', status_code=500)
                return jsonify(response), status_code
            
            # Generate thumbnail from middle frame
            thumbnail_path = generate_clip_thumbnail(filepath, filename, middle_frame=True)
            
            # Cache the clip
            cache_downloaded_clip(clip_id, filepath, thumbnail_path)
        except Exception as e:
            logger.error(f"Error downloading local clip: {e}")
            response, status_code = create_api_response(success=False, error=f'Download failed: {str(e)}', status_code=500)
            return jsonify(response), status_code
    
    return send_file(filepath, as_attachment=True, download_name=filename)

def start_hls_stream(camera_id: str, rtsp_url: str) -> Tuple[Optional[str], Optional[str]]:
    """Start HLS transcoding for RTSP stream.
    
    Args:
        camera_id: Unique identifier for the camera
        rtsp_url: RTSP stream URL from camera
        
    Returns:
        Tuple of (hls_playlist_url, error_message)
        Success: (playlist_url, None)
        Failure: (None, error_message)
        
    Creates temporary directory for HLS segments and starts FFmpeg
    transcoding process with configured HLS parameters.
    """
    logger.info(f"Starting HLS stream for camera {camera_id} with RTSP URL: {rtsp_url}")
    
    # Stop existing stream if running
    stop_hls_stream(camera_id)
    
    # Create temporary directory for HLS files
    hls_dir = tempfile.mkdtemp(prefix=f'hls_{camera_id}_')
    playlist_path = os.path.join(hls_dir, 'playlist.m3u8')
    
    # FFmpeg command for RTSP to HLS transcoding
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', rtsp_url,
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-preset', 'ultrafast',
        '-tune', 'zerolatency',
        '-f', 'hls',
        '-hls_time', str(Config.HLS_SEGMENT_TIME),
        '-hls_list_size', str(Config.HLS_LIST_SIZE),
        '-hls_flags', 'delete_segments',
        playlist_path
    ]
    
    try:
        # Start FFmpeg process
        logger.debug(f"Starting FFmpeg with command: {' '.join(ffmpeg_cmd)}")
        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait briefly to check if process starts successfully
        import time
        time.sleep(1)
        
        if process.poll() is not None:
            # Process has already terminated
            stdout, stderr = process.communicate()
            error_msg = stderr.decode('utf-8') if stderr else 'Unknown FFmpeg error'
            logger.error(f"FFmpeg failed to start: {error_msg}")
            return None, error_msg
        
        # Store process info
        with live_streams_lock:
            live_streams[camera_id] = {
                'process': process,
                'hls_dir': hls_dir,
                'playlist_path': playlist_path
            }
        
        logger.info(f"HLS stream started successfully for camera {camera_id}")
        return f'/api/hls/{camera_id}/playlist.m3u8', None
    except Exception as e:
        error_msg = f"Error starting HLS stream: {e}"
        logger.error(error_msg)
        return None, error_msg

def stop_hls_stream(camera_id: str) -> None:
    """Stop HLS transcoding for camera and clean up resources.
    
    Args:
        camera_id: Unique identifier for the camera
        
    Terminates FFmpeg process gracefully with fallback to force kill.
    Removes temporary HLS directory and cleans up stream cache.
    """
    with live_streams_lock:
        if camera_id in live_streams:
            stream_info = live_streams[camera_id]
            
            # Terminate FFmpeg process gracefully
            if stream_info['process']:
                try:
                    # Try graceful termination first
                    stream_info['process'].terminate()
                    stream_info['process'].wait(timeout=Config.PROCESS_TERMINATE_TIMEOUT)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful termination fails
                    logger.warning(f"Force killing FFmpeg process for camera {camera_id}")
                    stream_info['process'].kill()
                    stream_info['process'].wait()
                except Exception as e:
                    logger.error(f"Error stopping FFmpeg process: {e}")
            
            # Clean up temporary directory
            import shutil
            try:
                if os.path.exists(stream_info['hls_dir']):
                    shutil.rmtree(stream_info['hls_dir'])
            except Exception as e:
                logger.error(f"Error cleaning up HLS directory: {e}")
            
            del live_streams[camera_id]

@app.route('/api/camera/<camera_id>/liveview')
def get_camera_liveview(camera_id: str):
    try:
        camera_id = validate_id_format(camera_id, Config.VALID_CAMERA_ID_PATTERN, 'Camera ID')
    except ValueError as e:
        response, status_code = create_api_response(success=False, error=str(e), status_code=400)
        return jsonify(response), status_code
    
    """Get live view stream for camera."""
    if not blink or not blink.available:
        response, status_code = create_api_response(success=False, error='Blink not available', status_code=500)
        return jsonify(response), status_code
    
    camera = find_camera_by_id(camera_id)
    if not camera:
        response, status_code = create_api_response(success=False, error='Camera not found', status_code=404)
        return jsonify(response), status_code
    
    try:
        # Get RTSP stream URL
        rtsp_url = run_in_blink_thread(camera.get_liveview())
        
        if rtsp_url:
            # Start HLS transcoding
            hls_url, error_msg = start_hls_stream(camera_id, rtsp_url)
            if hls_url:
                response, status_code = create_api_response(success=True, data={
                    'rtsp_url': rtsp_url,
                    'hls_url': hls_url
                })
                return jsonify(response), status_code
            else:
                response, status_code = create_api_response(success=False, error=f'Failed to start HLS transcoding: {error_msg}', status_code=500)
                return jsonify(response), status_code
        else:
            response, status_code = create_api_response(success=False, error='Failed to get live view URL', status_code=500)
            return jsonify(response), status_code
    except Exception as e:
        response, status_code = handle_api_error(e, f'getting live view for camera {camera_id}')
        return jsonify(response), status_code

@app.route('/api/hls/<camera_id>/<path:filename>')
def serve_hls_file(camera_id: str, filename: str):
    """Serve HLS playlist and segment files."""
    with live_streams_lock:
        if camera_id not in live_streams:
            response, status_code = create_api_response(success=False, error='Stream not found', status_code=404)
            return jsonify(response), status_code
        
        hls_dir = live_streams[camera_id]['hls_dir']
    
    file_path = os.path.join(hls_dir, filename)
    
    if not os.path.exists(file_path):
        response, status_code = create_api_response(success=False, error='File not found', status_code=404)
        return jsonify(response), status_code
    
    if filename.endswith('.m3u8'):
        return send_file(file_path, mimetype='application/vnd.apple.mpegurl')
    elif filename.endswith('.ts'):
        return send_file(file_path, mimetype='video/mp2t')
    else:
        response, status_code = create_api_response(success=False, error='Invalid file type', status_code=400)
        return jsonify(response), status_code

@app.route('/api/clip/<clip_id>/thumbnail')
def get_clip_thumbnail(clip_id: str):
    try:
        clip_id = validate_id_format(clip_id, Config.VALID_CLIP_ID_PATTERN, 'Clip ID')
    except ValueError as e:
        response, status_code = create_api_response(success=False, error=str(e), status_code=400)
        return jsonify(response), status_code
    """Serve clip thumbnail."""
    with downloaded_clips_lock:
        if clip_id in downloaded_clips_cache:
            thumbnail_path = downloaded_clips_cache[clip_id]['thumbnail']
            if thumbnail_path and os.path.exists(thumbnail_path):
                return send_file(thumbnail_path, mimetype='image/jpeg')
    
    response, status_code = create_api_response(success=False, error='Thumbnail not found', status_code=404)
    return jsonify(response), status_code

@app.route('/api/media/thumbnail/<camera_id>')
def get_camera_thumbnail(camera_id: str):
    try:
        camera_id = validate_id_format(camera_id, Config.VALID_CAMERA_ID_PATTERN, 'Camera ID')
    except ValueError as e:
        response, status_code = create_api_response(success=False, error=str(e), status_code=400)
        return jsonify(response), status_code
    
    """Proxy camera thumbnail with authentication."""
    if not blink or not blink.available:
        response, status_code = create_api_response(success=False, error='Blink not available', status_code=500)
        return jsonify(response), status_code
    
    camera = find_camera_by_id(camera_id)
    if not camera or not camera.thumbnail:
        response, status_code = create_api_response(success=False, error='Camera or thumbnail not found', status_code=404)
        return jsonify(response), status_code
    
    try:
        # Check cache first
        with thumbnail_cache_lock:
            if camera_id in thumbnail_cache:
                logger.debug(f"Serving cached thumbnail for camera {camera_id}")
                filename = thumbnail_cache[camera_id]['filename']
                filepath = os.path.join(THUMBNAIL_CACHE_DIR, filename)
                if os.path.exists(filepath):
                    response = send_file(filepath, mimetype='image/jpeg')
                    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                    return response
        
        # If not cached, fetch from Blink
        response = run_in_blink_thread(camera.get_thumbnail())
        if response and response.status == 200:
            image_data = run_in_blink_thread(response.read())
            return FlaskResponse(image_data, mimetype='image/jpeg')
        else:
            response, status_code = create_api_response(success=False, error='Failed to fetch thumbnail', status_code=500)
            return jsonify(response), status_code
    except Exception as e:
        response, status_code = handle_api_error(e, f'fetching thumbnail for camera {camera_id}')
        return jsonify(response), status_code

@app.route('/placeholder')
def placeholder():
    """Show placeholder message."""
    response, status_code = create_api_response(success=False, error='This feature is not yet available', status_code=501)
    return jsonify(response), status_code

async def load_saved_blink():
    """Load Blink system from saved credentials file."""
    global blink
    if os.path.exists(CREDENTIALS_FILE):
        try:
            from blinkpy.helpers.util import json_load
            auth_data = await json_load(CREDENTIALS_FILE)
            auth = Auth(auth_data)
            blink = Blink(session=None)
            blink.auth = auth
            success = await blink.start()
            if success:
                logger.info("Blink system loaded from saved credentials")
                return True
            else:
                logger.warning("Failed to load Blink system from saved credentials - removing invalid file")
                os.remove(CREDENTIALS_FILE)
                return False
        except Exception as e:
            logger.warning(f"Could not load Blink system from saved credentials: {e} - removing invalid file")
            if os.path.exists(CREDENTIALS_FILE):
                os.remove(CREDENTIALS_FILE)
            return False
    return False

def startup() -> None:
    """Initialize application on startup.
    
    Creates cache directories, scans existing thumbnails, starts Blink thread,
    and attempts to load saved credentials. If no valid credentials found,
    user will need to login through web interface.
    
    Handles initialization errors gracefully and logs appropriate messages.
    """
    try:
        # Initialize cache paths
        get_cache_paths()
        
        # Create cache directories if they don't exist
        os.makedirs(CACHE_DIR, exist_ok=True)
        os.makedirs(THUMBNAIL_CACHE_DIR, exist_ok=True)
        os.makedirs(CLIPS_CACHE_DIR, exist_ok=True)
        
        # Scan and load existing thumbnails from cache
        scan_thumbnail_cache()
        
        # Initialize Blink thread for startup
        global blink_thread
        if not blink_thread or not blink_thread.is_alive():
            blink_thread = threading.Thread(target=run_blink_thread, daemon=True)
            blink_thread.start()
            import time
            time.sleep(0.1)  # Give thread time to start
        
        try:
            success = run_in_blink_thread(load_saved_blink())
            if not success:
                logger.info("No valid saved credentials found - user will need to login")
        except Exception as e:
            logger.error(f"Error loading saved Blink credentials: {e}")
            # Clear invalid credentials file
            if os.path.exists(CREDENTIALS_FILE):
                os.remove(CREDENTIALS_FILE)
                logger.info("Removed invalid credentials file")
    except Exception as e:
        logger.warning(f"Could not initialize Blink system on startup: {e}")

def generate_clip_thumbnail(video_path: str, filename: str, middle_frame: bool = False) -> Optional[str]:
    """Generate thumbnail image from video clip.
    
    Args:
        video_path: Path to the video file
        filename: Original filename for thumbnail naming
        middle_frame: If True, extract middle frame; if False, extract first frame
        
    Returns:
        Path to generated thumbnail file, or None if generation failed
        
    Uses FFmpeg to extract frame from video. For middle frame extraction,
    first determines video duration with ffprobe.
    """
    thumbnail_filename = filename.replace('.mp4', '.jpg')
    thumbnail_path = os.path.join(CLIPS_CACHE_DIR, thumbnail_filename)
    
    if os.path.exists(thumbnail_path):
        return thumbnail_path
    
    try:
        import subprocess
        # Use ffmpeg to extract frame (middle frame for local clips, first frame for cloud)
        if middle_frame:
            # Get video duration and extract middle frame
            duration_cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', video_path]
            duration_result = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=Config.FFPROBE_TIMEOUT)
            duration = float(duration_result.stdout.strip()) / 2  # Middle timestamp
            cmd = ['ffmpeg', '-i', video_path, '-ss', str(duration), '-vframes', '1', '-f', 'image2', thumbnail_path]
        else:
            # Extract first frame
            cmd = ['ffmpeg', '-i', video_path, '-ss', '00:00:01', '-vframes', '1', '-f', 'image2', thumbnail_path]
        
        result = subprocess.run(cmd, capture_output=True, check=True, timeout=Config.FFMPEG_TIMEOUT)
        return thumbnail_path
    except subprocess.TimeoutExpired:
        logger.error(f"Thumbnail generation timed out for {video_path}")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error generating thumbnail: {e.stderr.decode() if e.stderr else str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error generating thumbnail: {e}")
        return None

def cache_downloaded_clip(clip_id: str, filepath: str, thumbnail_path: Optional[str]) -> None:
    """Cache downloaded clip with FIFO management.
    
    Args:
        clip_id: Unique identifier for the clip
        filepath: Path to the downloaded video file
        thumbnail_path: Path to the thumbnail file, or None if unavailable
        
    Maintains FIFO cache with size limit. Automatically removes oldest
    clips and their associated files when cache exceeds configured limit.
    Thread-safe operation using downloaded_clips_lock.
    """
    with downloaded_clips_lock:
        # Add to cache
        downloaded_clips_cache[clip_id] = {
            'filepath': filepath,
            'thumbnail': thumbnail_path
        }
        
        # Maintain FIFO order
        if clip_id not in downloaded_clips_order:
            downloaded_clips_order.append(clip_id)
        
        # Maintain cache size limit (50 clips)
        while len(downloaded_clips_order) > CLIPS_CACHE_SIZE:
            oldest_clip_id = downloaded_clips_order.pop(0)
            if oldest_clip_id in downloaded_clips_cache:
                # Clean up files
                old_clip = downloaded_clips_cache[oldest_clip_id]
                try:
                    if os.path.exists(old_clip['filepath']):
                        os.remove(old_clip['filepath'])
                    if old_clip['thumbnail'] and os.path.exists(old_clip['thumbnail']):
                        os.remove(old_clip['thumbnail'])
                except Exception as e:
                    logger.warning(f"Error cleaning up old clip files: {e}")
                
                del downloaded_clips_cache[oldest_clip_id]

def scan_thumbnail_cache() -> None:
    """Scan thumbnail cache directory and load existing thumbnails into memory.
    
    Parses cached thumbnail filenames in format 'camera_id_timestamp.jpg'
    and populates the thumbnail_cache dictionary with metadata.
    Handles camera IDs containing underscores and logs parsing errors.
    Thread-safe operation using thumbnail_cache_lock.
    """
    if not os.path.exists(THUMBNAIL_CACHE_DIR):
        return
    
    try:
        with thumbnail_cache_lock:
            for filename in os.listdir(THUMBNAIL_CACHE_DIR):
                if filename.endswith('.jpg'):
                    # Parse filename format: camera_id_timestamp.jpg
                    parts = filename.replace('.jpg', '').split('_')
                    if len(parts) >= 2:
                        try:
                            camera_id = '_'.join(parts[:-1])  # Handle camera IDs with underscores
                            timestamp = int(parts[-1])
                            
                            filepath = os.path.join(THUMBNAIL_CACHE_DIR, filename)
                            if os.path.exists(filepath):
                                thumbnail_cache[camera_id] = {
                                    'timestamp': timestamp,
                                    'filename': filename
                                }
                                logger.debug(f"Loaded cached thumbnail for camera {camera_id} with timestamp {timestamp}")
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Could not parse thumbnail filename {filename}: {e}")
    except Exception as e:
        logger.error(f"Error scanning thumbnail cache: {e}")

def generate_thumbnail_async(clip_id, item, sync_module):
    """Generate thumbnail for local clip in background."""
    def background_task():
        try:
            # Download clip to generate thumbnail
            iso_date = item.created_at.strftime('%Y-%m-%dT%H-%M-%S')
            filename = f"{item.name}_{iso_date}.mp4"
            filepath = os.path.join(CLIPS_CACHE_DIR, filename)
            
            # Use blinkpy methods to download
            run_in_blink_thread(item.prepare_download(blink))
            success = run_in_blink_thread(item.download_video(blink, filepath))
            
            if success and os.path.exists(filepath):
                # Generate thumbnail
                thumbnail_path = generate_clip_thumbnail(filepath, filename, middle_frame=True)
                if thumbnail_path:
                    cache_downloaded_clip(clip_id, filepath, thumbnail_path)
                    logger.info(f"Generated thumbnail for clip {clip_id}")
        except Exception as e:
            logger.error(f"Error generating thumbnail for {clip_id}: {e}")
    
    # Start background thread
    import threading
    thread = threading.Thread(target=background_task, daemon=True)
    thread.start()

@app.route('/api/clip/<clip_id>/thumbnail/check')
def check_clip_thumbnail(clip_id: str):
    """Check if thumbnail is available for clip."""
    with downloaded_clips_lock:
        if clip_id in downloaded_clips_cache:
            thumbnail_path = downloaded_clips_cache[clip_id]['thumbnail']
            if thumbnail_path and os.path.exists(thumbnail_path):
                response, status_code = create_api_response(success=True, data={'available': True, 'url': f'/api/clip/{clip_id}/thumbnail'})
                return jsonify(response), status_code
    
    response, status_code = create_api_response(success=True, data={'available': False})
    return jsonify(response), status_code

def cleanup_resources() -> None:
    """Clean up all resources on application shutdown.
    
    Stops all active HLS streams and their FFmpeg processes.
    Terminates the Blink event loop gracefully.
    Called automatically on exit via atexit handler and signal handlers.
    """
    logger.info("Cleaning up resources...")
    
    # Stop all live streams
    with live_streams_lock:
        camera_ids = list(live_streams.keys())
    
    for camera_id in camera_ids:
        try:
            stop_hls_stream(camera_id)
        except Exception as e:
            logger.error(f"Error stopping stream for camera {camera_id}: {e}")
    
    # Close Blink session before stopping loop
    global blink, blink_loop
    if blink:
        try:
            # Try to close session gracefully
            if hasattr(blink, 'close') and callable(blink.close):
                if blink_loop and blink_loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(blink.close(), blink_loop)
                    future.result(timeout=2)
        except Exception as e:
            logger.debug(f"Session cleanup: {e}")  # Reduce log noise
    
    # Stop Blink event loop
    if blink_loop and blink_loop.is_running():
        try:
            blink_loop.call_soon_threadsafe(blink_loop.stop)
        except Exception as e:
            logger.error(f"Error stopping Blink loop: {e}")
    
    logger.info("Resource cleanup completed")

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    cleanup_resources()
    sys.exit(0)

# Register cleanup handlers
atexit.register(cleanup_resources)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Initialize on startup
startup()

if __name__ == '__main__':
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        cleanup_resources()