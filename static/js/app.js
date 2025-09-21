/**
 * Main Application Module
 * Handles app initialization, configuration, and global state management
 */

// Global application state
let currentView = 'home';
let currentSystem = null;
let systems = [];
let devices = [];

// Configuration loaded from server
let appConfig = {
    hls_stream_check_interval: 1000,
    hls_stream_check_delay: 2000,
    hls_stream_max_attempts: 10,
    thumbnail_update_poll_interval: 2000,
    thumbnail_success_display_time: 1000,
    thumbnail_processing_display_time: 3000,
    clip_thumbnail_check_interval: 2000,
    clip_thumbnail_poll_max_attempts: 15,
    thumbnail_error_display_time: 3000,
    milliseconds_to_seconds: 1000,
    error_messages: {
        live_stream_failed: "Unable to start live video. Please check your camera connection and try again.",
        live_stream_connection_failed: "Unable to start live video. Please check your internet connection and try again.",
        live_view_failed: "Unable to start live view. Please check that your camera is online and try again.",
        connection_error: "Unable to connect. Please check your internet connection and try again.",
        arm_state_failed: "Unable to change system status. Please check your connection and try again.",
        clip_download_failed: "Unable to download video. Please try again later.",
        clip_play_failed: "Unable to play video. Please check your connection and try again.",
        cache_clear_success: "Cache cleared successfully! Your storage space has been freed up.",
        cache_clear_failed: "Unable to clear cache. Please check your connection and try again.",
        logout_failed: "Unable to log out. Please try again.",
        clips_updated: "All your local video clips are already up to date!",
        feature_coming_soon: "This feature is coming soon! We're working hard to bring it to you."
    }
};

/**
 * Initialize the application
 */
document.addEventListener('DOMContentLoaded', function() {
    loadConfig();
    loadSystems();
    loadSettings();
    setupEventListeners();

    // Initialize view from URL hash
    showViewFromHash();
});

/**
 * Setup event listeners including hash change
 */
/**
 * Setup global event listeners
 */
function setupEventListeners() {
    // Listen for hash changes (browser back/forward)
    window.addEventListener('hashchange', showViewFromHash);

    // Cleanup livestream when page is unloaded
    window.addEventListener('beforeunload', function() {
        if (window.LiveStream && window.LiveStream.getCurrentStream()) {
            // Use sendBeacon for reliable cleanup during page unload
            const currentStream = window.LiveStream.getCurrentStream();
            navigator.sendBeacon(`/api/cameras/${currentStream.cameraId}/liveview`);

/**
 * Load configuration from server
 */
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const data = await response.json();
        if (response.ok && data.success) {
            appConfig = { ...appConfig, ...data.data };
        }
    } catch (error) {
        console.warn('Could not load configuration, using defaults:', error);
    }
}
        }
    });

    // Also cleanup on visibility change (when tab becomes hidden)
    document.addEventListener('visibilitychange', function() {
        if (document.hidden && window.LiveStream && window.LiveStream.getCurrentStream()) {
            window.LiveStream.stop();
        }
    });
}

/**
 * Show a specific view and handle navigation
 */
// Hash to view mapping for URL persistence
const HASH_TO_VIEW = {
    '': 'home',
    '#clips': 'clips',
    '#settings': 'settings'
};

const VIEW_TO_HASH = {
    'home': '',
    'clips': '#clips',
    'settings': '#settings'
};

function showView(viewName) {
    // Stop livestream if leaving live view
    if (window.LiveStream && window.LiveStream.getCurrentStream() && viewName !== 'live') {
        window.LiveStream.stop();
    }

    // Hide all views
    document.querySelectorAll('.view').forEach(view => {
        view.style.display = 'none';
    });

    // Show selected view
    document.getElementById(viewName + '-view').style.display = 'block';

    // Update nav buttons
    updateNavButtons(viewName);

    // Show/hide header elements
    updateHeaderVisibility(viewName);

    currentView = viewName;

    // Update URL hash (but prevent infinite loop)
    if (!window.hashChangeInProgress) {
        setViewHash(viewName);
    }

    // Load view-specific data
    if (viewName === 'clips') {
        window.Clips.load();
        window.Clips.startThumbnailPolling();
    } else {
        window.Clips.stopThumbnailPolling();
    }

    // Start age updates for home view
    if (viewName === 'home') {
        window.Camera.startAgeUpdates();
    } else {
        window.Camera.stopAgeUpdates();
    }
}

/**
 * Set URL hash for current view
 */
function setViewHash(viewName) {
    const hash = VIEW_TO_HASH[viewName];
    if (hash !== undefined) {
        window.location.hash = hash;
    }
}

/**
 * Show view based on current URL hash
 */
function showViewFromHash() {
    const hash = window.location.hash;
    const viewName = HASH_TO_VIEW[hash] || 'home';

    // Prevent hash change loop
    window.hashChangeInProgress = true;
    showView(viewName);
    window.hashChangeInProgress = false;
}

/**
 * Update navigation button states
 */
function updateNavButtons(viewName) {
    document.querySelectorAll('.nav-button').forEach(btn => {
        btn.classList.remove('active');
    });

    // Only update nav button if called from nav button click
    if (event && event.target) {
        const navButton = event.target.closest('.nav-button');
        if (navButton) {
            navButton.classList.add('active');
        }
    } else {
        // Find and activate the correct nav button based on viewName
        const navButtons = document.querySelectorAll('.nav-button');
        navButtons.forEach(btn => {
            const text = btn.querySelector('.nav-text').textContent.toLowerCase();
            if ((viewName === 'home' && text === 'home') ||
                (viewName === 'clips' && text === 'clips') ||
                (viewName === 'settings' && text === 'settings')) {
                btn.classList.add('active');
            }
        });
    }
}

/**
 * Update header element visibility based on current view
 */
function updateHeaderVisibility(viewName) {
    if (viewName === 'home') {
        document.getElementById('home-header').style.display = 'flex';
        document.getElementById('bottom-controls').style.display = 'flex';
        document.getElementById('clips-storage-selector').style.display = 'none';
    } else if (viewName === 'clips') {
        document.getElementById('home-header').style.display = 'none';
        document.getElementById('bottom-controls').style.display = 'none';
        document.getElementById('clips-storage-selector').style.display = 'flex';
    } else {
        document.getElementById('home-header').style.display = 'none';
        document.getElementById('bottom-controls').style.display = 'none';
        document.getElementById('clips-storage-selector').style.display = 'none';
    }
}

/**
 * Load available Blink systems
 */
async function loadSystems() {
    try {
        const response = await fetch('/api/systems');
        const data = await response.json();

        if (response.ok && data.success) {
            systems = data.data.systems;
            const select = document.getElementById('system-select');
            select.innerHTML = '';

            systems.forEach(system => {
                const option = document.createElement('option');
                option.value = system.network_id;
                option.textContent = system.name;
                select.appendChild(option);
            });

            if (systems.length > 0) {
                currentSystem = systems[0];
                select.value = currentSystem.network_id;
                loadDevices();
                updateArmButton();
            }
        } else if (response.status === 401) {
            // Authentication required - redirect to login
            window.location.href = '/login';
        } else {
            console.error('Failed to load systems:', data.error);
            document.getElementById('device-list').innerHTML = `
                <div style="text-align: center; padding: 40px; color: #d32f2f;">
                    ${data.error}
                    <br><br>
                    <button onclick="logout()" style="background: #d32f2f; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">
                        Log out
                    </button>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading systems:', error);
        document.getElementById('device-list').innerHTML = `
            <div style="text-align: center; padding: 40px; color: #d32f2f;">
                Connection error. Please try again.
                <br><br>
                <button onclick="logout()" style="background: #d32f2f; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer;">
                    Log out
                </button>
            </div>
        `;
    }
}

/**
 * Load devices for the selected system
 */
async function loadDevices() {
    const select = document.getElementById('system-select');
    const networkId = select.value;

    if (!networkId) return;

    // Find the selected system
    currentSystem = systems.find(s => s.network_id == networkId);
    updateArmButton();

    try {
        const response = await fetch(`/api/systems/${networkId}/devices`);
        const data = await response.json();

        if (response.ok && data.success) {
            devices = data.data.devices;
            window.Camera.renderDevices(devices);
        } else {
            console.error('Failed to load devices:', data.error);
        }
    } catch (error) {
        console.error('Error loading devices:', error);
    }
}

/**
 * Update arm/disarm button states
 */
function updateArmButton() {
    const disarmedBtn = document.getElementById('disarmed-btn');
    const armedBtn = document.getElementById('armed-btn');

    if (currentSystem && currentSystem.armed) {
        disarmedBtn.classList.remove('active');
        armedBtn.classList.add('active');
    } else {
        disarmedBtn.classList.add('active');
        armedBtn.classList.remove('active');
    }
}

/**
 * Set system arm state
 */
async function setArmState(armed) {
    if (!currentSystem || currentSystem.armed === armed) return;

    try {
        const response = await fetch(`/api/systems/${currentSystem.network_id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ armed: armed })
        });

        if (response.ok) {
            currentSystem.armed = armed;
            updateArmButton();
        } else {
            const data = await response.json();
            alert(appConfig.error_messages.arm_state_failed + (data.error ? ': ' + data.error : ''));
        }
    } catch (error) {
        console.error('Error toggling arm state:', error);
        alert(appConfig.error_messages.arm_state_failed);
    }
}

/**
 * Toggle system arm state
 */
async function toggleArm() {
    if (!currentSystem) return;

    const newArmedState = !currentSystem.armed;

    try {
        const response = await fetch(`/api/systems/${currentSystem.network_id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ armed: newArmedState })
        });

        if (response.ok) {
            currentSystem.armed = newArmedState;
            updateArmButton();
        } else {
            const data = await response.json();
            alert(appConfig.error_messages.arm_state_failed + (data.error ? ': ' + data.error : ''));
        }
    } catch (error) {
        console.error('Error toggling arm state:', error);
        alert(appConfig.error_messages.arm_state_failed);
    }
}

/**
 * Load user settings
 */
async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                const settings = data.data;
                document.getElementById('temperature-units').value = settings.temperatureUnits || 'C';
                document.getElementById('cloud-clip-retention').value = settings.cloudClipRetention || '30';
                document.getElementById('local-clip-retention').value = settings.localClipRetention || 'never';
                document.getElementById('clip-thumbnail-size').value = settings.clipThumbnailSize || 'medium';
                window.Clips.applyThumbnailSize(settings.clipThumbnailSize || 'medium');
            }
        }
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

/**
 * Save a user setting
 */
async function saveSetting(key, value) {
    try {
        const response = await fetch('/api/settings', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ [key]: value })
        });

        if (response.ok) {
            console.log(`Setting ${key} saved:`, value);

            // Apply thumbnail size immediately
            if (key === 'clipThumbnailSize') {
                window.Clips.applyThumbnailSize(value);
            }
        } else {
            console.error(`Failed to save setting ${key}`);
        }
    } catch (error) {
        console.error(`Error saving setting ${key}:`, error);
    }
}

/**
 * Clear application cache
 */
async function clearCache() {
    try {
        const response = await fetch('/api/cache', {
            method: 'DELETE'
        });

        if (response.ok) {
            // Invalidate images and videos by adding timestamp to force reload
            const timestamp = Date.now();
            document.querySelectorAll('img[src*="/api/cameras/"], img[src*="/api/clips/"], video[src*="/api/clips/"]').forEach(media => {
                const url = new URL(media.src, window.location.origin);
                url.searchParams.set('_t', timestamp);
                media.src = url.toString();
            });

            // Reload current view to refresh data
            if (currentView === 'home') {
                loadDevices();
            } else if (currentView === 'clips') {
                window.Clips.load();
            }

            alert(appConfig.error_messages.cache_clear_success);
        } else {
            const data = await response.json();
            alert(appConfig.error_messages.cache_clear_failed + (data.error ? ': ' + data.error : ''));
        }
    } catch (error) {
        console.error('Error clearing cache:', error);
        alert(appConfig.error_messages.cache_clear_failed);
    }
}

/**
 * Confirm logout action
 */
function confirmLogout() {
    showModal('logout-modal');
}

/**
 * Perform logout
 */
async function performLogout() {
    try {
        const response = await fetch('/logout', {
            method: 'POST'
        });

        if (response.ok) {
            window.location.href = '/login';
        } else {
            alert(appConfig.error_messages.logout_failed);
        }
    } catch (error) {
        console.error('Error logging out:', error);
        alert(appConfig.error_messages.logout_failed);
    }
}

/**
 * Utility functions
 */
function showModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
}

function hideModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function showAddDevicePlaceholder() {
    showPlaceholder();
}

function showPlaceholder() {
    alert(appConfig.error_messages.feature_coming_soon);
}

function toggleSwitch(switchElement) {
    switchElement.classList.toggle('on');
}

// Export global functions for backward compatibility
window.showView = showView;
window.loadDevices = loadDevices;
window.setArmState = setArmState;
window.toggleArm = toggleArm;
window.saveSetting = saveSetting;
window.clearCache = clearCache;
window.confirmLogout = confirmLogout;
window.performLogout = performLogout;
window.showModal = showModal;
window.hideModal = hideModal;
window.showAddDevicePlaceholder = showAddDevicePlaceholder;
window.showPlaceholder = showPlaceholder;
window.toggleSwitch = toggleSwitch;

// Export for other modules
window.App = {
    currentView,
    currentSystem,
    systems,
    devices,
    appConfig,
    getCurrentView: () => currentView,
    getCurrentSystem: () => currentSystem,
    getSystems: () => systems,
    getDevices: () => devices,
    getConfig: () => appConfig
};
