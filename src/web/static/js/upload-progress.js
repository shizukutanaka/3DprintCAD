/**
 * Upload progress tracking with speed calculation and ETA
 */

class UploadProgressTracker {
    constructor() {
        this.uploads = new Map();
    }

    /**
     * Start tracking an upload
     */
    startUpload(fileId, fileName, fileSize) {
        this.uploads.set(fileId, {
            fileName,
            fileSize,
            loaded: 0,
            startTime: Date.now(),
            lastUpdateTime: Date.now(),
            lastLoaded: 0,
            speed: 0,
            eta: null,
            status: 'uploading'
        });
    }

    /**
     * Update upload progress
     */
    updateProgress(fileId, loaded) {
        const upload = this.uploads.get(fileId);
        if (!upload) return;

        const now = Date.now();
        const timeDiff = (now - upload.lastUpdateTime) / 1000; // seconds
        const loadedDiff = loaded - upload.lastLoaded;

        // Calculate speed (bytes per second)
        if (timeDiff > 0) {
            upload.speed = loadedDiff / timeDiff;
        }

        upload.loaded = loaded;
        upload.lastUpdateTime = now;
        upload.lastLoaded = loaded;

        // Calculate ETA
        const remaining = upload.fileSize - loaded;
        if (upload.speed > 0) {
            upload.eta = Math.ceil(remaining / upload.speed);
        }

        return this.getUploadInfo(fileId);
    }

    /**
     * Mark upload as complete
     */
    completeUpload(fileId) {
        const upload = this.uploads.get(fileId);
        if (upload) {
            upload.status = 'complete';
            upload.loaded = upload.fileSize;
            upload.eta = 0;
        }
    }

    /**
     * Mark upload as failed
     */
    failUpload(fileId, error) {
        const upload = this.uploads.get(fileId);
        if (upload) {
            upload.status = 'failed';
            upload.error = error;
        }
    }

    /**
     * Get upload information
     */
    getUploadInfo(fileId) {
        const upload = this.uploads.get(fileId);
        if (!upload) return null;

        const percentage = Math.round((upload.loaded / upload.fileSize) * 100);
        const elapsedTime = (Date.now() - upload.startTime) / 1000;

        return {
            fileName: upload.fileName,
            fileSize: upload.fileSize,
            loaded: upload.loaded,
            percentage,
            speed: upload.speed,
            speedFormatted: this.formatSpeed(upload.speed),
            eta: upload.eta,
            etaFormatted: this.formatTime(upload.eta),
            elapsedTime,
            elapsedTimeFormatted: this.formatTime(elapsedTime),
            status: upload.status
        };
    }

    /**
     * Format speed in human-readable format
     */
    formatSpeed(bytesPerSecond) {
        if (!bytesPerSecond || bytesPerSecond === 0) return '0 B/s';

        const units = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
        let size = bytesPerSecond;
        let unitIndex = 0;

        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }

        return `${size.toFixed(1)} ${units[unitIndex]}`;
    }

    /**
     * Format time in human-readable format
     */
    formatTime(seconds) {
        if (!seconds || seconds <= 0) return '0s';

        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);

        if (hours > 0) {
            return `${hours}h ${minutes}m ${secs}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${secs}s`;
        } else {
            return `${secs}s`;
        }
    }

    /**
     * Get all active uploads
     */
    getActiveUploads() {
        const active = [];
        for (const [fileId, upload] of this.uploads.entries()) {
            if (upload.status === 'uploading') {
                active.push({
                    fileId,
                    ...this.getUploadInfo(fileId)
                });
            }
        }
        return active;
    }

    /**
     * Clear completed uploads
     */
    clearCompleted() {
        for (const [fileId, upload] of this.uploads.entries()) {
            if (upload.status === 'complete') {
                this.uploads.delete(fileId);
            }
        }
    }

    /**
     * Create progress UI element
     */
    createProgressElement(fileId, fileName, fileSize) {
        const element = document.createElement('div');
        element.id = `upload-progress-${fileId}`;
        element.className = 'upload-progress-item';
        element.innerHTML = `
            <div class="upload-header">
                <span class="upload-filename">${this.escapeHtml(fileName)}</span>
                <span class="upload-size">${this.formatBytes(fileSize)}</span>
            </div>
            <div class="upload-progress-bar">
                <div class="upload-progress-fill" style="width: 0%"></div>
            </div>
            <div class="upload-stats">
                <span class="upload-percentage">0%</span>
                <span class="upload-speed">0 B/s</span>
                <span class="upload-eta">Calculating...</span>
            </div>
        `;
        return element;
    }

    /**
     * Update progress UI element
     */
    updateProgressElement(fileId, info) {
        const element = document.getElementById(`upload-progress-${fileId}`);
        if (!element) return;

        const fill = element.querySelector('.upload-progress-fill');
        const percentage = element.querySelector('.upload-percentage');
        const speed = element.querySelector('.upload-speed');
        const eta = element.querySelector('.upload-eta');

        if (fill) fill.style.width = `${info.percentage}%`;
        if (percentage) percentage.textContent = `${info.percentage}%`;
        if (speed) speed.textContent = info.speedFormatted;
        if (eta) {
            if (info.eta && info.eta > 0) {
                eta.textContent = `ETA: ${info.etaFormatted}`;
            } else {
                eta.textContent = 'Complete';
            }
        }

        if (info.status === 'complete') {
            element.classList.add('upload-complete');
        } else if (info.status === 'failed') {
            element.classList.add('upload-failed');
        }
    }

    /**
     * Format bytes in human-readable format
     */
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';

        const units = ['B', 'KB', 'MB', 'GB'];
        let size = bytes;
        let unitIndex = 0;

        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }

        return `${size.toFixed(2)} ${units[unitIndex]}`;
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Axios upload adapter with progress tracking
     */
    createAxiosConfig(fileId, fileName, fileSize) {
        this.startUpload(fileId, fileName, fileSize);

        return {
            onUploadProgress: (progressEvent) => {
                const info = this.updateProgress(fileId, progressEvent.loaded);
                if (info) {
                    this.updateProgressElement(fileId, info);
                }
            }
        };
    }
}

// Global instance
window.uploadProgressTracker = new UploadProgressTracker();

// Helper function for easy integration
window.trackUpload = function(fileId, fileName, fileSize, container) {
    const tracker = window.uploadProgressTracker;

    // Create progress element
    const element = tracker.createProgressElement(fileId, fileName, fileSize);
    if (container) {
        container.appendChild(element);
    }

    // Return axios config
    return tracker.createAxiosConfig(fileId, fileName, fileSize);
};
