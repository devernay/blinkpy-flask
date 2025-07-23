/**
 * Live Stream Management Module
 * Handles live video streaming functionality
 */

let currentLiveStream = null;

/**
 * Show live view for a camera
 */
async function showLiveView(cameraId, cameraName) {
    const config = window.App.getConfig();

    try {
        console.log('Starting live view for camera:', cameraId);
        const response = await fetch(`/api/camera/${cameraId}/liveview`);
        const data = await response.json();

        console.log('Live view response:', data);

        if (response.ok && data.success) {
            // Store current stream info for cleanup
            currentLiveStream = {
                cameraId: cameraId,
                streamId: data.data.stream_id,
                tcpUrl: data.data.tcp_url,
                hlsUrl: data.data.hls_url
            };

            // Show live view
            document.getElementById('live-view-title').textContent = `${cameraName} Live View`;
            const video = document.getElementById('live-video');

            console.log('HLS URL:', data.data.hls_url);
            console.log('TCP URL:', data.data.tcp_url);

            window.showView('live');

            // Wait for HLS stream to be ready and check if playlist exists
            let attempts = 0;
            const maxAttempts = config.hls_stream_max_attempts;
            const checkStream = async () => {
                attempts++;
                try {
                    const streamResponse = await fetch(data.data.hls_url);
                    if (streamResponse.ok) {
                        console.log('HLS playlist ready, loading video');
                        video.src = data.data.hls_url;
                        video.load();
                    } else if (attempts < maxAttempts) {
                        console.log(`HLS playlist not ready (attempt ${attempts}/${maxAttempts}), retrying...`);
                        setTimeout(checkStream, config.hls_stream_check_interval);
                    } else {
                        console.error('HLS playlist failed to become ready after', maxAttempts, 'attempts');
                        alert(config.error_messages.live_stream_failed);
                        // Clean up on failure
                        currentLiveStream = null;
                    }
                } catch (error) {
                    if (attempts < maxAttempts) {
                        console.log(`Error checking HLS playlist (attempt ${attempts}/${maxAttempts}):`, error);
                        setTimeout(checkStream, config.hls_stream_check_interval);
                    } else {
                        console.error('Failed to load HLS stream after', maxAttempts, 'attempts:', error);
                        alert(config.error_messages.live_stream_connection_failed);
                        // Clean up on failure
                        currentLiveStream = null;
                    }
                }
            };

            // Start checking after configured delay
            setTimeout(checkStream, config.hls_stream_check_delay);
        } else {
            console.error('Live view API error:', data);
            alert(config.error_messages.live_view_failed);
        }
    } catch (error) {
        console.error('Error starting live view:', error);
        alert(config.error_messages.connection_error);
    }
}

/**
 * Stop the current live stream
 */
async function stopLiveStream() {
    if (!currentLiveStream) return;

    try {
        console.log('Stopping livestream for camera:', currentLiveStream.cameraId);

        // Stop the video element
        const video = document.getElementById('live-video');
        if (video) {
            video.pause();
            video.src = '';
            video.load();
        }

        // Call the backend to stop the stream
        const response = await fetch(`/api/camera/${currentLiveStream.cameraId}/liveview/stop`, {
            method: 'POST'
        });

        if (response.ok) {
            console.log('Livestream stopped successfully');
        } else {
            console.warn('Failed to stop livestream on server');
        }
    } catch (error) {
        console.error('Error stopping livestream:', error);
    } finally {
        currentLiveStream = null;
    }
}

/**
 * Toggle mute state of live video
 */
function toggleMute() {
    const video = document.getElementById('live-video');
    const muteBtn = document.querySelector('.mute-btn');

    if (video.muted) {
        video.muted = false;
        muteBtn.textContent = '🔊';
    } else {
        video.muted = true;
        muteBtn.textContent = '🔇';
    }
}

/**
 * Get current live stream info
 */
function getCurrentStream() {
    return currentLiveStream;
}

/**
 * Check if a stream is currently active
 */
function isStreamActive() {
    return currentLiveStream !== null;
}

/**
 * Get stream status information
 */
function getStreamStatus() {
    if (!currentLiveStream) {
        return {
            active: false,
            cameraId: null,
            streamId: null
        };
    }

    return {
        active: true,
        cameraId: currentLiveStream.cameraId,
        streamId: currentLiveStream.streamId,
        tcpUrl: currentLiveStream.tcpUrl,
        hlsUrl: currentLiveStream.hlsUrl
    };
}

// Export functions for global access
window.showLiveView = showLiveView;
window.toggleMute = toggleMute;

// Export module
window.LiveStream = {
    show: showLiveView,
    stop: stopLiveStream,
    toggleMute,
    getCurrentStream,
    isStreamActive,
    getStreamStatus
};
