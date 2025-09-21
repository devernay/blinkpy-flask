/**
 * Clips Management Module
 * Handles clip loading, rendering, playback, and thumbnail management
 */

let thumbnailPollingInterval = null;
let clipsBeingProcessed = new Set();
let downloadQueue = [];
let isDownloading = false;

/**
 * Load clips from server
 */
async function loadClips() {
    const storageType = document.querySelector('.storage-btn.active').textContent.toLowerCase().includes('cloud') ? 'cloud' : 'local';
    const container = document.getElementById('clips-list');

    // Show loading spinner
    container.innerHTML = `
        <div class="loading-state">
            <div class="spinner">⟳</div>
            <p>Loading clips...</p>
        </div>
    `;

    try {
        const response = await fetch(`/api/clips?storage=${storageType}`);
        const data = await response.json();

        if (response.ok && data.success) {
            if (data.data.clips.length === 0) {
                // If cloud storage is empty, try local storage
                if (storageType === 'cloud') {
                    selectStorage('local');
                    return;
                }

                container.innerHTML = `
                    <div class="empty-state">
                        <h3><strong>No Recent Activity</strong></h3>
                        <p>This is where you'll see motion events and other recent activity from your devices.</p>
                    </div>
                `;
            } else {
                renderClips(data.data.clips);
            }
        } else {
            console.error('Failed to load clips:', data.error);
            container.innerHTML = `
                <div class="empty-state">
                    <h3>Error Loading Clips</h3>
                    <p>Unable to load clips: ${data.error}</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading clips:', error);
        container.innerHTML = `
            <div class="empty-state">
                <h3>Error Loading Clips</h3>
                <p>Unable to connect to server.</p>
            </div>
        `;
    }
}

/**
 * Render clips in the UI
 */
function renderClips(clipsData) {
    const container = document.getElementById('clips-list');
    container.innerHTML = '';

    // Add Update button for local storage
    const storageType = document.querySelector('.storage-btn.active').textContent.toLowerCase().includes('local') ? 'local' : 'cloud';
    if (storageType === 'local' && clipsData.length > 0) {
        addUpdateButton(container, clipsData);
    }

    clipsData.forEach(dayGroup => {
        const dayDiv = document.createElement('div');
        dayDiv.className = 'day-group';

        dayDiv.innerHTML = `
            <div class="day-header">
                <strong>${dayGroup.date}</strong> - ${dayGroup.clips.length} event${dayGroup.clips.length !== 1 ? 's' : ''}
            </div>
        `;

        dayGroup.clips.forEach(clip => {
            const clipDiv = document.createElement('div');
            clipDiv.className = 'clip-item';
            clipDiv.onclick = () => playClip(clip);

            // Apply current thumbnail size setting to new elements
            const thumbnailSize = getCurrentThumbnailSize();
            clipDiv.innerHTML = `
                ${clip.thumbnail ? `<img src="${clip.thumbnail}" class="clip-thumbnail size-${thumbnailSize}" alt="${clip.camera_name}" data-clip-id="${clip.id}">` : `<div class="clip-thumbnail clip-placeholder size-${thumbnailSize}" data-clip-id="${clip.id}"><div class="play-icon">▶</div></div>`}
                <div class="clip-info">
                    <div class="clip-camera">${clip.camera_name}</div>
                    <div class="clip-system">${clip.system_name}</div>
                    <div class="clip-time">${clip.time}</div>
                    <div class="clip-event">${clip.event_type}</div>
                </div>
            `;

            dayDiv.appendChild(clipDiv);
        });

        container.appendChild(dayDiv);
    });
}

/**
 * Add update button for local clips
 */
function addUpdateButton(container, clipsData) {
    // Count clips without thumbnails
    let missingCount = 0;
    clipsData.forEach(dayGroup => {
        dayGroup.clips.forEach(clip => {
            if (!clip.thumbnail && clip.id.includes('~')) {
                missingCount++;
            }
        });
    });

    if (missingCount > 0) {
        const downloadAllBtn = document.createElement('div');
        downloadAllBtn.innerHTML = `
            <button class="download-all-btn" onclick="window.Clips.downloadAllLocalClips()" style="
                width: 100%;
                padding: 15px;
                background: #007AFF;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                margin-bottom: 20px;
            ">Update ${missingCount} Clip${missingCount !== 1 ? 's' : ''}</button>
        `;
        container.appendChild(downloadAllBtn);
    }
}

/**
 * Play a clip
 */
async function playClip(clip) {
    const isLocalClip = clip.id.includes('~');
    const config = window.App.getConfig();

    // Show loading modal
    const loadingModal = document.createElement('div');
    loadingModal.className = 'modal';
    loadingModal.style.display = 'block';
    loadingModal.innerHTML = `
        <div class="modal-content" style="max-width: 400px; background: #333; color: white; text-align: center; padding: 40px;">
            <div class="spinner" style="margin-bottom: 20px;">⟳</div>
            <div style="font-weight: bold; margin-bottom: 10px;">Just a moment...</div>
            <div>We're retrieving your clip.</div>
            ${isLocalClip ? '<div style="margin-top: 10px;">Hang tight, USB clips take a little longer to load.</div>' : ''}
        </div>
    `;
    document.body.appendChild(loadingModal);

    try {
        // Download and play clip
        const response = await fetch(`/api/clips/${clip.id}/download`);
        if (response.ok) {
            const blob = await response.blob();
            const videoUrl = URL.createObjectURL(blob);

            // Remove loading modal
            loadingModal.remove();

            // Create video player modal
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.style.display = 'block';
            modal.innerHTML = `
                <div class="modal-content" style="max-width: 800px;">
                    <div class="modal-header">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <button class="clip-action-btn" onclick="window.Clips.downloadClip('${clip.id}')" title="Download clip">
                                📥
                            </button>
                            <button class="clip-action-btn" onclick="window.Clips.showDeleteConfirmation('${clip.id}')" title="Delete clip">
                                🗑️
                            </button>
                        </div>
                        <h2 style="font-size: 16px; font-weight: 600;">${clip.camera_name} - ${formatClipDate(clip)} - ${clip.time}</h2>
                        <button class="close-btn" onclick="window.Clips.closeVideoModal(this)">&times;</button>
                    </div>
                    <video controls preload="metadata" style="width: 100%; border-radius: 8px;">
                        <source src="${videoUrl}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                </div>
            `;
            document.body.appendChild(modal);
            // Start thumbnail polling for this specific clip
            startClipThumbnailPolling(clip.id);
        } else {
            loadingModal.remove();
            const error = await response.json();
            alert(config.error_messages.clip_download_failed + (error.error ? ': ' + error.error : ''));
        }
    } catch (error) {
        loadingModal.remove();
        console.error('Error playing clip:', error);
        alert(config.error_messages.clip_play_failed);
    }
}

/**
 * Close video modal
 */
function closeVideoModal(button) {
    const modal = button.closest('.modal');
    const video = modal.querySelector('video');
    if (video && video.src) {
        URL.revokeObjectURL(video.src);
    }
    modal.remove();
}

/**
 * Download clip
 */
function downloadClip(clipId) {
    const downloadUrl = `/api/clips/${clipId}/download`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = '';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Show delete confirmation modal
 */
function showDeleteConfirmation(clipId) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.display = 'block';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">Delete Clip</h2>
                <button class="close-btn" onclick="this.closest('.modal').remove()">&times;</button>
            </div>
            <div style="margin-bottom: 20px;">
                <b>Are you sure?</b><br />
                This will delete the clip and cannot be undone.
            </div>
            <div style="display: flex; gap: 10px; justify-content: flex-end;">
                <button onclick="this.closest('.modal').remove()" style="padding: 8px 16px; border: 1px solid #ccc; background: white; border-radius: 6px; cursor: pointer;">
                    Nevermind
                </button>
                <button onclick="window.Clips.deleteClip('${clipId}'); this.closest('.modal').remove();" style="padding: 8px 16px; border: none; background: #dc3545; color: white; border-radius: 6px; cursor: pointer;">
                    Delete Clip
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

/**
 * Delete clip
 */
async function deleteClip(clipId) {
    try {
        const response = await fetch(`/api/clips/${clipId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            // Close video modal if open
            const videoModal = document.querySelector('.modal video');
            if (videoModal) {
                videoModal.closest('.modal').remove();
            }

            // Reload clips to reflect deletion
            loadClips();
        } else {
            const error = await response.json();
            alert('Failed to delete clip: ' + (error.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error deleting clip:', error);
        alert('Failed to delete clip. Please try again.');
    }
}

/**
 * Select storage type (cloud/local)
 */
function selectStorage(type) {
    document.querySelectorAll('.storage-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent.toLowerCase().includes(type)) {
            btn.classList.add('active');
        }
    });

    // Reload clips for selected storage type
    loadClips();
}

/**
 * Start thumbnail polling (placeholder for future use)
 */
function startThumbnailPolling() {
    // Don't start general polling - only poll for specific clips after download
    // This prevents unnecessary API calls for clips that haven't been downloaded
}

/**
 * Start polling for a specific clip thumbnail
 */
function startClipThumbnailPolling(clipId) {
    if (clipsBeingProcessed.has(clipId)) return;

    clipsBeingProcessed.add(clipId);
    let attempts = 0;
    const config = window.App.getConfig();
    const maxAttempts = config.clip_thumbnail_poll_max_attempts || 15;

    const pollInterval = setInterval(async () => {
        attempts++;

        try {
            const response = await fetch(`/api/clips/${clipId}/thumbnail?check=true`);
            const data = await response.json();

            if (data.success && data.data.available) {
                // Replace placeholder with thumbnail
                const placeholder = document.querySelector(`[data-clip-id="${clipId}"]`);
                if (placeholder && placeholder.classList.contains('clip-placeholder')) {
                    const img = document.createElement('img');
                    img.src = `/api/clips/${clipId}/thumbnail`;
                    img.className = 'clip-thumbnail';
                    img.alt = 'Clip thumbnail';
                    img.setAttribute('data-clip-id', clipId);

                    placeholder.parentNode.replaceChild(img, placeholder);
                }

                clearInterval(pollInterval);
                clipsBeingProcessed.delete(clipId);
            } else if (attempts >= maxAttempts) {
                clearInterval(pollInterval);
                clipsBeingProcessed.delete(clipId);
            }
        } catch (error) {
            console.error('Error checking thumbnail:', error);
            if (attempts >= maxAttempts) {
                clearInterval(pollInterval);
                clipsBeingProcessed.delete(clipId);
            }
        }
    }, config.clip_thumbnail_check_interval || 2000);
}

/**
 * Stop thumbnail polling
 */
function stopThumbnailPolling() {
    if (thumbnailPollingInterval) {
        clearInterval(thumbnailPollingInterval);
        thumbnailPollingInterval = null;
    }
}

/**
 * Get current thumbnail size setting
 */
function getCurrentThumbnailSize() {
    const select = document.getElementById('clip-thumbnail-size');
    return select ? select.value : 'medium';
}

/**
 * Apply thumbnail size to all clip thumbnails
 */
function applyThumbnailSize(size) {
    document.querySelectorAll('.clip-thumbnail').forEach(thumbnail => {
        // Remove existing size classes
        thumbnail.classList.remove('size-small', 'size-medium', 'size-large');
        // Add new size class
        thumbnail.classList.add(`size-${size}`);
    });
}

/**
 * Format clip date for display
 */
function formatClipDate(clip) {
    // Extract date from clip data - clips are grouped by day
    const dayGroups = document.querySelectorAll('.day-group');
    for (const dayGroup of dayGroups) {
        const clipItems = dayGroup.querySelectorAll('.clip-item');
        for (const clipItem of clipItems) {
            const clipThumbnail = clipItem.querySelector('.clip-thumbnail');
            if (clipThumbnail && clipThumbnail.getAttribute('data-clip-id') === clip.id) {
                const dayHeader = dayGroup.querySelector('.day-header');
                if (dayHeader) {
                    // Extract just the date part (before the dash)
                    const headerText = dayHeader.textContent.trim();
                    const datePart = headerText.split(' - ')[0];
                    return datePart;
                }
            }
        }
    }
    return 'Unknown Date';
}

/**
 * Download all local clips that need thumbnails
 */
async function downloadAllLocalClips() {
    const config = window.App.getConfig();

    // Scan DOM for local clips missing thumbnails (placeholders)
    const clipsToDownload = [];
    document.querySelectorAll('.clip-item').forEach(clipItem => {
        const thumbnail = clipItem.querySelector('.clip-thumbnail');
        const clipId = thumbnail?.getAttribute('data-clip-id');

        if (clipId && clipId.includes('~') && thumbnail?.classList.contains('clip-placeholder')) {
            // Extract clip data from DOM
            const clipInfo = clipItem.querySelector('.clip-info');
            const cameraName = clipInfo?.querySelector('.clip-camera')?.textContent;
            const time = clipInfo?.querySelector('.clip-time')?.textContent;

            clipsToDownload.push({
                id: clipId,
                camera_name: cameraName,
                time: time
            });
        }
    });

    if (clipsToDownload.length === 0) {
        alert(config.error_messages.clips_updated);
        return;
    }

    // Add to download queue
    downloadQueue = [...clipsToDownload];

    // Update button text
    const btn = document.querySelector('.download-all-btn');
    if (btn) {
        btn.textContent = `Updating ${downloadQueue.length} clips...`;
        btn.disabled = true;
    }

    // Start background downloading
    processDownloadQueue();
}

/**
 * Process the download queue
 */
async function processDownloadQueue() {
    if (isDownloading || downloadQueue.length === 0) return;

    isDownloading = true;
    const config = window.App.getConfig();
    let errorCount = 0;
    let successCount = 0;

    // Process clips sequentially to avoid overwhelming server
    while (downloadQueue.length > 0) {
        const clip = downloadQueue.shift();

        try {
            // Trigger server-side processing (download + thumbnail generation)
            const response = await fetch(`/api/clips/${clip.id}/thumbnail`, {
                method: 'POST'
            });

            if (response.ok) {
                // Wait for thumbnail to be generated
                await waitForThumbnail(clip.id);
                successCount++;
            } else {
                const errorData = await response.json().catch(() => ({}));
                console.error(`Failed to process clip ${clip.id}:`, errorData.error || 'Unknown error');
                errorCount++;
            }
        } catch (error) {
            console.error(`Error processing clip ${clip.id}:`, error);
            errorCount++;
        }

        // Update button text
        const btn = document.querySelector('.download-all-btn');
        if (btn) {
            if (downloadQueue.length > 0) {
                btn.textContent = `Updating ${downloadQueue.length} clips...`;
            } else {
                // Show completion status
                if (errorCount > 0) {
                    btn.textContent = `Updated ${successCount}, ${errorCount} failed`;
                    btn.style.background = '#FF6B6B';
                    setTimeout(() => {
                        btn.style.background = '#007AFF';
                        updateButtonState(btn);
                    }, 3000);
                } else {
                    btn.textContent = `Updated ${successCount} clips`;
                    btn.style.background = '#28A745';
                    setTimeout(() => {
                        btn.style.background = '#007AFF';
                        updateButtonState(btn);
                    }, 2000);
                }
                btn.disabled = false;
            }
        }
    }

    isDownloading = false;
}

/**
 * Update button state based on remaining clips
 */
function updateButtonState(btn) {
    // Recalculate missing clips count
    let missingCount = 0;
    document.querySelectorAll('.clip-item').forEach(clipItem => {
        const thumbnail = clipItem.querySelector('.clip-thumbnail');
        const clipId = thumbnail?.getAttribute('data-clip-id');
        if (clipId && clipId.includes('~') && thumbnail?.classList.contains('clip-placeholder')) {
            missingCount++;
        }
    });

    if (missingCount > 0) {
        btn.textContent = `Update ${missingCount} Clip${missingCount !== 1 ? 's' : ''}`;
        btn.style.display = 'block';
    } else {
        btn.style.display = 'none';
    }
}
    }

    isDownloading = false;
}

/**
 * Wait for thumbnail to be generated
 */
async function waitForThumbnail(clipId) {
    const config = window.App.getConfig();

    return new Promise((resolve) => {
        const checkThumbnail = async () => {
            try {
                const response = await fetch(`/api/clips/${clipId}/thumbnail?check=true`);
                const data = await response.json();

                if (data.success && data.data.available) {
                    // Replace placeholder with thumbnail
                    const placeholder = document.querySelector(`[data-clip-id="${clipId}"]`);
                    if (placeholder && placeholder.classList.contains('clip-placeholder')) {
                        const img = document.createElement('img');
                        img.src = `/api/clips/${clipId}/thumbnail`;
                        const thumbnailSize = getCurrentThumbnailSize();
                        img.className = `clip-thumbnail size-${thumbnailSize}`;
                        img.alt = 'Clip thumbnail';
                        img.setAttribute('data-clip-id', clipId);

                        placeholder.parentNode.replaceChild(img, placeholder);
                    }
                    resolve();
                } else {
                    // Retry after a delay
                    setTimeout(checkThumbnail, config.clip_thumbnail_check_interval);
                }
            } catch (error) {
                console.error('Error checking thumbnail:', error);
                resolve(); // Continue even if error
            }
        };

        checkThumbnail();
    });
}

// Export functions for global access
window.selectStorage = selectStorage;

// Export module
window.Clips = {
    load: loadClips,
    renderClips,
    playClip,
    closeVideoModal,
    downloadClip,
    showDeleteConfirmation,
    deleteClip,
    selectStorage,
    startThumbnailPolling,
    stopThumbnailPolling,
    startClipThumbnailPolling,
    getCurrentThumbnailSize,
    applyThumbnailSize,
    formatClipDate,
    downloadAllLocalClips,
    processDownloadQueue,
    updateButtonState,
    waitForThumbnail
};
