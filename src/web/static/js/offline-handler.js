/**
 * Offline detection and automatic retry with exponential backoff
 */

class OfflineHandler {
    constructor() {
        this.isOnline = navigator.onLine;
        this.retryQueue = [];
        this.maxRetries = 3;
        this.baseDelay = 1000; // 1 second
        this.maxDelay = 30000; // 30 seconds

        this.setupEventListeners();
        this.startMonitoring();
    }

    setupEventListeners() {
        window.addEventListener('online', () => {
            this.handleOnline();
        });

        window.addEventListener('offline', () => {
            this.handleOffline();
        });
    }

    handleOnline() {
        this.isOnline = true;
        this.showNotification('Connection restored', 'success');
        this.processRetryQueue();
    }

    handleOffline() {
        this.isOnline = false;
        this.showNotification('Connection lost. Changes will be saved and retried when online.', 'warning');
    }

    /**
     * Start monitoring connection with periodic checks
     */
    startMonitoring() {
        setInterval(() => {
            this.checkConnection();
        }, 10000); // Check every 10 seconds
    }

    /**
     * Check connection by pinging server
     */
    async checkConnection() {
        try {
            const response = await fetch('/api/health', {
                method: 'GET',
                cache: 'no-cache',
                signal: AbortSignal.timeout(5000)
            });

            const wasOffline = !this.isOnline;
            this.isOnline = response.ok;

            if (wasOffline && this.isOnline) {
                this.handleOnline();
            } else if (!wasOffline && !this.isOnline) {
                this.handleOffline();
            }
        } catch (error) {
            if (this.isOnline) {
                this.isOnline = false;
                this.handleOffline();
            }
        }
    }

    /**
     * Add request to retry queue
     */
    addToRetryQueue(request) {
        const queueItem = {
            id: Date.now() + Math.random(),
            request,
            retries: 0,
            nextRetryTime: Date.now()
        };

        this.retryQueue.push(queueItem);
        this.saveQueueToStorage();

        return queueItem.id;
    }

    /**
     * Process retry queue
     */
    async processRetryQueue() {
        if (!this.isOnline || this.retryQueue.length === 0) return;

        const now = Date.now();
        const itemsToRetry = this.retryQueue.filter(item => item.nextRetryTime <= now);

        for (const item of itemsToRetry) {
            try {
                await this.retryRequest(item);
                this.removeFromQueue(item.id);
            } catch (error) {
                item.retries++;

                if (item.retries >= this.maxRetries) {
                    this.showNotification(
                        `Failed to sync: ${item.request.description || 'Request'}`,
                        'error'
                    );
                    this.removeFromQueue(item.id);
                } else {
                    // Exponential backoff
                    const delay = Math.min(
                        this.baseDelay * Math.pow(2, item.retries),
                        this.maxDelay
                    );
                    item.nextRetryTime = Date.now() + delay;
                }
            }
        }

        this.saveQueueToStorage();
    }

    /**
     * Retry a request
     */
    async retryRequest(item) {
        const { request } = item;

        const response = await fetch(request.url, {
            method: request.method || 'GET',
            headers: request.headers || {},
            body: request.body
        });

        if (!response.ok) {
            throw new Error(`Request failed: ${response.status}`);
        }

        if (request.onSuccess) {
            const data = await response.json();
            request.onSuccess(data);
        }

        return response;
    }

    /**
     * Remove item from queue
     */
    removeFromQueue(id) {
        this.retryQueue = this.retryQueue.filter(item => item.id !== id);
        this.saveQueueToStorage();
    }

    /**
     * Save queue to localStorage
     */
    saveQueueToStorage() {
        try {
            const serializable = this.retryQueue.map(item => ({
                id: item.id,
                request: {
                    url: item.request.url,
                    method: item.request.method,
                    headers: item.request.headers,
                    body: item.request.body,
                    description: item.request.description
                },
                retries: item.retries,
                nextRetryTime: item.nextRetryTime
            }));

            localStorage.setItem('offline_retry_queue', JSON.stringify(serializable));
        } catch (error) {
            console.error('Failed to save retry queue:', error);
        }
    }

    /**
     * Load queue from localStorage
     */
    loadQueueFromStorage() {
        try {
            const stored = localStorage.getItem('offline_retry_queue');
            if (stored) {
                this.retryQueue = JSON.parse(stored);
            }
        } catch (error) {
            console.error('Failed to load retry queue:', error);
        }
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        if (window.enhancedUI) {
            window.enhancedUI.showNotification(message, type, 5000);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }

    /**
     * Wrap axios request with offline handling
     */
    wrapAxiosRequest(axiosConfig) {
        const originalConfig = { ...axiosConfig };

        return async (...args) => {
            if (!this.isOnline) {
                // Queue for retry
                const queueId = this.addToRetryQueue({
                    url: args[0],
                    method: originalConfig.method || 'GET',
                    headers: originalConfig.headers,
                    body: originalConfig.data,
                    description: `Request to ${args[0]}`
                });

                this.showNotification('Request queued for retry when online', 'warning');

                // Return a rejected promise
                return Promise.reject(new Error('Offline - queued for retry'));
            }

            // Online - proceed with request
            try {
                return await axios(originalConfig);
            } catch (error) {
                // Check if it's a network error
                if (!error.response && error.message.includes('Network Error')) {
                    this.handleOffline();
                    const queueId = this.addToRetryQueue({
                        url: args[0],
                        method: originalConfig.method || 'GET',
                        headers: originalConfig.headers,
                        body: originalConfig.data,
                        description: `Request to ${args[0]}`
                    });

                    this.showNotification('Network error - request queued for retry', 'warning');
                }
                throw error;
            }
        };
    }

    /**
     * Get queue status
     */
    getQueueStatus() {
        return {
            isOnline: this.isOnline,
            queueLength: this.retryQueue.length,
            pendingRequests: this.retryQueue.map(item => ({
                id: item.id,
                description: item.request.description,
                retries: item.retries,
                nextRetry: new Date(item.nextRetryTime).toLocaleString()
            }))
        };
    }

    /**
     * Clear retry queue
     */
    clearQueue() {
        this.retryQueue = [];
        localStorage.removeItem('offline_retry_queue');
    }
}

// Global instance
window.offlineHandler = new OfflineHandler();

// Load queued requests from storage
window.offlineHandler.loadQueueFromStorage();

// Auto-process queue when online
if (navigator.onLine) {
    setTimeout(() => {
        window.offlineHandler.processRetryQueue();
    }, 1000);
}

// Helper function for easy integration
window.makeOfflineRequest = async function(url, options = {}) {
    const handler = window.offlineHandler;

    if (!handler.isOnline) {
        handler.addToRetryQueue({
            url,
            method: options.method || 'GET',
            headers: options.headers,
            body: options.body,
            description: options.description || `Request to ${url}`,
            onSuccess: options.onSuccess
        });

        handler.showNotification('Request queued for retry when online', 'warning');
        throw new Error('Offline - queued for retry');
    }

    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            throw new Error(`Request failed: ${response.status}`);
        }
        return response;
    } catch (error) {
        if (error.message.includes('Failed to fetch')) {
            handler.handleOffline();
            handler.addToRetryQueue({
                url,
                method: options.method || 'GET',
                headers: options.headers,
                body: options.body,
                description: options.description || `Request to ${url}`,
                onSuccess: options.onSuccess
            });
            handler.showNotification('Network error - request queued for retry', 'warning');
        }
        throw error;
    }
};
