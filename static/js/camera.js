/**
 * Camera Management Module
 * Handles camera rendering, thumbnail management, and camera-specific operations
 */

let currentCameraId = null;
let ageUpdateInterval = null;

/**
 * Render all devices (cameras and sync modules)
 */
async function renderDevices(devices) {
    const container = document.getElementById('device-list');
    container.innerHTML = '';

    for (const device of devices) {
        if (device.type === 'camera') {
            const cameraCard = await createCameraCard(device);
            container.appendChild(cameraCard);
        } else if (device.type === 'sync_module') {
            const syncCard = createSyncModuleCard(device);
            container.appendChild(syncCard);
        }
    }
}

/**
 * Create a camera card element
 */
function formatDuration(seconds) {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;

    const days = Math.floor(seconds / 86400);
    return `${days}d`;
}

function calculateThumbnailAge(thumbnailUrl) {
    if (!thumbnailUrl) return '';

    try {
        const url = new URL(thumbnailUrl, window.location.origin);
        const ts = url.searchParams.get('ts');
        if (!ts) return '';

        const thumbnailTime = parseInt(ts) * 1000; // Convert to milliseconds
        const now = Date.now();
        const ageSeconds = Math.floor((now - thumbnailTime) / 1000);

        if (ageSeconds <= 0) return 'now';
        return formatDuration(ageSeconds) + ' ago';
    } catch (error) {
        console.warn('Error calculating thumbnail age:', error);
        return '';
    }
}

async function createCameraCard(camera) {
    const card = document.createElement('div');
    card.className = 'device-card camera-card';

    let thumbnailUrl = camera.thumbnail;
    if (thumbnailUrl) {
        try {
            const response = await fetch(`/api/cameras/${camera.id}/thumbnail?timestamp=true`);
            const data = await response.json();
            if (response.ok && data.success) {
                thumbnailUrl = `${camera.thumbnail}?ts=${data.data.timestamp}`;
            }
        } catch (error) {
            console.error('Error fetching timestamp for camera', camera.id, error);
        }
    }

    const thumbnailAge = calculateThumbnailAge(thumbnailUrl);

    card.innerHTML = `
        ${thumbnailUrl ? `<img src="${thumbnailUrl}" class="camera-thumbnail" alt="${camera.name}">` : ''}
        <div class="camera-overlay">
            <div class="camera-name">${camera.name}</div>
            <button class="play-btn" onclick="window.LiveStream.show('${camera.id}', '${camera.name}')">▶</button>
            <div class="camera-bottom">
                <div class="camera-time">${thumbnailAge}</div>
                <button class="kebab-btn" onclick="window.Camera.showPane('${camera.id}', '${camera.name}')">⋮</button>
            </div>
        </div>
    `;

    return card;
}

/**
 * Create a sync module card element
 */
function createSyncModuleCard(sync) {
    const card = document.createElement('div');
    card.className = 'device-card sync-module-card';

    card.innerHTML = `
        <div class="sync-module-name">Sync Module</div>
        <div class="status-badge ${sync.online ? 'status-online' : 'status-offline'}">
            ${sync.online ? 'Online' : 'Offline'}
        </div>
    `;

    return card;
}

/**
 * Show camera settings pane
 */
function showCameraPane(cameraId, cameraName) {
    currentCameraId = cameraId;
    document.getElementById('camera-modal-title').textContent = cameraName;

    // Update motion detection status
    const camera = window.App.getDevices().find(d => d.id === cameraId && d.type === 'camera');
    const motionStatus = document.getElementById('motion-status');
    const motionSwitch = document.querySelector('#camera-modal .switch');

    if (camera) {
        const currentSystem = window.App.getCurrentSystem();
        const isArmed = currentSystem && currentSystem.armed;
        const motionEnabled = camera.motion_enabled;

        // Update switch state based on motion detection setting
        if (motionEnabled) {
            motionSwitch.classList.add('on');
        } else {
            motionSwitch.classList.remove('on');
        }

        // Update status text: motion state + system state
        const motionState = motionEnabled ? 'On' : 'Off';
        const systemState = isArmed ? '(System Armed)' : '(System Disarmed)';
        motionStatus.textContent = `${motionState} ${systemState}`;
    }

    window.showModal('camera-modal');
}

/**
 * Refresh camera thumbnail
 */
async function refreshThumbnail() {
    if (!currentCameraId) return;

    // Close camera pane immediately
    window.hideModal('camera-modal');

    // Show refreshing banner
    showThumbnailBanner(currentCameraId, 'Refreshing thumbnail...', 'refreshing');

    try {
        const response = await fetch(`/api/cameras/${currentCameraId}/thumbnail`, {
            method: 'DELETE'
        });

        if (response.ok) {
            // Poll for updated thumbnail
            pollForThumbnailUpdate(currentCameraId);
        } else {
            const data = await response.json();
            const config = window.App.getConfig();
            showThumbnailBanner(currentCameraId, 'Error refreshing thumbnail', 'error');
            setTimeout(() => hideThumbnailBanner(currentCameraId), config.thumbnail_error_display_time || 3000);
        }
    } catch (error) {
        console.error('Error refreshing thumbnail:', error);
        const config = window.App.getConfig();
        showThumbnailBanner(currentCameraId, 'Error refreshing thumbnail', 'error');
        setTimeout(() => hideThumbnailBanner(currentCameraId), config.thumbnail_error_display_time || 3000);
    }
}

/**
 * Start periodic age updates for thumbnails
 */
function startAgeUpdates() {
    if (ageUpdateInterval) return;

    ageUpdateInterval = setInterval(() => {
        updateAllThumbnailAges();
    }, 60000); // Update every minute
}

/**
 * Stop age updates
 */
function stopAgeUpdates() {
    if (ageUpdateInterval) {
        clearInterval(ageUpdateInterval);
        ageUpdateInterval = null;
    }
}

/**
 * Update all thumbnail age displays
 */
function updateAllThumbnailAges() {
    document.querySelectorAll('.camera-time').forEach(timeElement => {
        const cameraCard = timeElement.closest('.camera-card');
        if (cameraCard) {
            const img = cameraCard.querySelector('.camera-thumbnail');
            if (img && img.src) {
                const timestamp = extractTimestamp(img.src);
                if (timestamp > 0) {
                    const age = formatTimestampAge(timestamp);
                    timeElement.textContent = age;
                }
            }
        }
    });
}

/**
 * Extract timestamp from URL
 */
function extractTimestamp(url) {
    if (!url) return 0;
    const match = url.match(/[?&]ts=([0-9]+)/);
    return match ? parseInt(match[1]) : 0;
}

/**
 * Format timestamp age (e.g., "5m ago", "2h ago")
 */
function formatTimestampAge(timestamp) {
    const config = window.App.getConfig();
    const now = Date.now() / config.milliseconds_to_seconds;
    const diff = now - timestamp;
    const minutes = Math.floor(diff / 60);
    const hours = Math.floor(diff / 3600);
    const days = Math.floor(diff / 86400);

    if (days > 0) {
        return `${days}d ago`;
    } else if (hours > 0) {
        return `${hours}h ago`;
    } else if (minutes > 0) {
        return `${minutes}m ago`;
    } else {
        return 'Just now';
    }
}

/**
 * Show thumbnail status banner
 */
function showThumbnailBanner(cameraId, message, type) {
    const cameraCard = document.querySelector(`[onclick*="${cameraId}"]`)?.closest('.camera-card');
    if (!cameraCard) return;

    // Remove existing banner
    const existingBanner = cameraCard.querySelector('.thumbnail-banner');
    if (existingBanner) existingBanner.remove();

    // Create banner
    const banner = document.createElement('div');
    banner.className = `thumbnail-banner ${type}`;
    banner.textContent = message;

    cameraCard.appendChild(banner);
}

/**
 * Hide thumbnail status banner
 */
function hideThumbnailBanner(cameraId) {
    const cameraCard = document.querySelector(`[onclick*="${cameraId}"]`)?.closest('.camera-card');
    if (!cameraCard) return;

    const banner = cameraCard.querySelector('.thumbnail-banner');
    if (banner) banner.remove();
}

/**
 * Poll for thumbnail update after refresh
 */
function pollForThumbnailUpdate(cameraId) {
    let pollCount = 0;
    const maxPolls = 15;
    const config = window.App.getConfig();

    // Get initial timestamp from thumbnail URL
    const img = document.querySelector(`[onclick*="${cameraId}"]`)?.closest('.camera-card')?.querySelector('.camera-thumbnail');
    const lastTimestamp = extractTimestamp(img?.src || '');

    const pollInterval = setInterval(async () => {
        pollCount++;

        try {
            const response = await fetch(`/api/cameras/${cameraId}/thumbnail?timestamp=true`);
            const data = await response.json();

            if (response.ok && data.success) {
                const currentTimestamp = data.data.timestamp;
                console.log(`Camera ${cameraId} polling - Current: ${lastTimestamp}, Received: ${currentTimestamp}`);

                if (currentTimestamp > lastTimestamp) {
                    // Thumbnail updated!
                    const cameraCard = document.querySelector(`[onclick*="${cameraId}"]`)?.closest('.camera-card');
                    if (cameraCard) {
                        const img = cameraCard.querySelector('.camera-thumbnail');
                        if (img) {
                            const baseUrl = img.src.split('?')[0];
                            img.src = `${baseUrl}?ts=${currentTimestamp}`;
                        }

                        // Update timestamp display
                        const timeElement = cameraCard.querySelector('.camera-time');
                        if (timeElement) {
                            timeElement.textContent = 'Just now';
                        }
                    }

                    showThumbnailBanner(cameraId, 'Thumbnail updated!', 'success');
                    setTimeout(() => hideThumbnailBanner(cameraId), config.thumbnail_success_display_time);

                    clearInterval(pollInterval);
                    return;
                }
            }
        } catch (error) {
            console.error('Error polling for thumbnail update:', error);
        }

        if (pollCount >= maxPolls) {
            clearInterval(pollInterval);
            showThumbnailBanner(cameraId, 'Thumbnail refresh timeout', 'error');
            setTimeout(() => hideThumbnailBanner(cameraId), config.thumbnail_processing_display_time);
        }
    }, config.thumbnail_update_poll_interval);
}

// Export functions for global access
window.refreshThumbnail = refreshThumbnail;

// Export module
window.Camera = {
    renderDevices,
    createCameraCard,
    createSyncModuleCard,
    showPane: showCameraPane,
    refreshThumbnail,
    startAgeUpdates,
    stopAgeUpdates,
    updateAllThumbnailAges,
    extractTimestamp,
    formatTimestampAge,
    showThumbnailBanner,
    hideThumbnailBanner,
    pollForThumbnailUpdate
};
