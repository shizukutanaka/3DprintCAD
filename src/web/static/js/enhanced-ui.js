/**
 * Enhanced UI components for 3D Print CAD Assistant
 * Provides modern, accessible, and responsive user interface elements
 */

class EnhancedUI {
    constructor() {
        this.init();
        this.setupEventListeners();
        this.setupAccessibility();
        this.setupInternationalization();
    }

    init() {
        this.createProgressSystem();
        this.createNotificationSystem();
        this.createTooltipSystem();
        this.createModalSystem();
        this.setupDragDrop();
        this.setupKeyboardNavigation();
        this.setupThemeToggle();
    }

    // Progress System
    createProgressSystem() {
        const progressContainer = document.createElement('div');
        progressContainer.id = 'progress-container';
        progressContainer.className = 'progress-container hidden';
        progressContainer.innerHTML = `
            <div class="progress-backdrop">
                <div class="progress-modal">
                    <div class="progress-header">
                        <h3 data-i18n="processing">Processing...</h3>
                        <button class="progress-cancel" aria-label="Cancel operation" data-i18n-aria-label="cancel">
                            <span aria-hidden="true">&times;</span>
                        </button>
                    </div>
                    <div class="progress-content">
                        <div class="progress-bar-container">
                            <div class="progress-bar" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                                <div class="progress-fill"></div>
                            </div>
                            <span class="progress-text">0%</span>
                        </div>
                        <div class="progress-details">
                            <div class="progress-status" data-i18n="initializing">Initializing...</div>
                            <div class="progress-eta">ETA: --</div>
                        </div>
                        <div class="progress-log">
                            <div class="log-header">
                                <span data-i18n="details">Details</span>
                                <button class="log-toggle" aria-expanded="false">
                                    <span class="chevron">▼</span>
                                </button>
                            </div>
                            <div class="log-content hidden">
                                <ul class="log-list"></ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(progressContainer);
    }

    showProgress(options = {}) {
        const container = document.getElementById('progress-container');
        const progressBar = container.querySelector('.progress-bar');
        const progressFill = container.querySelector('.progress-fill');
        const progressText = container.querySelector('.progress-text');
        const statusText = container.querySelector('.progress-status');

        container.classList.remove('hidden');

        if (options.title) {
            container.querySelector('h3').textContent = options.title;
        }

        container.querySelector('.progress-cancel').onclick = () => {
            if (options.onCancel) options.onCancel();
            this.hideProgress();
        };

        return {
            update: (progress, status, eta) => {
                const percentage = Math.round(progress);
                progressBar.setAttribute('aria-valuenow', percentage);
                progressFill.style.width = `${percentage}%`;
                progressText.textContent = `${percentage}%`;

                if (status) statusText.textContent = status;
                if (eta) container.querySelector('.progress-eta').textContent = `ETA: ${eta}`;
            },
            log: (message, type = 'info') => {
                const logList = container.querySelector('.log-list');
                const logItem = document.createElement('li');
                logItem.className = `log-item log-${type}`;
                logItem.innerHTML = `
                    <span class="log-time">${new Date().toLocaleTimeString()}</span>
                    <span class="log-message">${message}</span>
                `;
                logList.appendChild(logItem);
                logList.scrollTop = logList.scrollHeight;
            }
        };
    }

    hideProgress() {
        const container = document.getElementById('progress-container');
        container.classList.add('hidden');
    }

    // Notification System
    createNotificationSystem() {
        const notificationContainer = document.createElement('div');
        notificationContainer.id = 'notification-container';
        notificationContainer.className = 'notification-container';
        notificationContainer.setAttribute('aria-live', 'polite');
        document.body.appendChild(notificationContainer);
    }

    showNotification(message, type = 'info', duration = 5000) {
        const container = document.getElementById('notification-container');
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.setAttribute('role', 'alert');

        const icons = {
            success: '✓',
            error: '✗',
            warning: '⚠',
            info: 'ℹ'
        };

        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-icon" aria-hidden="true">${icons[type] || icons.info}</span>
                <span class="notification-message">${message}</span>
                <button class="notification-close" aria-label="Close notification">
                    <span aria-hidden="true">&times;</span>
                </button>
            </div>
        `;

        const closeBtn = notification.querySelector('.notification-close');
        closeBtn.onclick = () => this.removeNotification(notification);

        container.appendChild(notification);

        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => this.removeNotification(notification), duration);
        }

        // Animate in
        requestAnimationFrame(() => {
            notification.classList.add('notification-show');
        });

        return notification;
    }

    removeNotification(notification) {
        notification.classList.add('notification-hide');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }

    // Tooltip System
    createTooltipSystem() {
        const tooltip = document.createElement('div');
        tooltip.id = 'tooltip';
        tooltip.className = 'tooltip hidden';
        tooltip.setAttribute('role', 'tooltip');
        document.body.appendChild(tooltip);

        // Add tooltip triggers
        document.addEventListener('mouseenter', this.handleTooltipShow.bind(this), true);
        document.addEventListener('mouseleave', this.handleTooltipHide.bind(this), true);
        document.addEventListener('focus', this.handleTooltipShow.bind(this), true);
        document.addEventListener('blur', this.handleTooltipHide.bind(this), true);
    }

    handleTooltipShow(event) {
        const element = event.target;
        const tooltipText = element.getAttribute('data-tooltip') || element.getAttribute('title');

        if (!tooltipText) return;

        // Remove title to prevent browser tooltip
        if (element.getAttribute('title')) {
            element.setAttribute('data-original-title', element.getAttribute('title'));
            element.removeAttribute('title');
        }

        const tooltip = document.getElementById('tooltip');
        tooltip.textContent = tooltipText;
        tooltip.classList.remove('hidden');

        this.positionTooltip(tooltip, element);
    }

    handleTooltipHide(event) {
        const element = event.target;
        const tooltip = document.getElementById('tooltip');

        tooltip.classList.add('hidden');

        // Restore original title
        if (element.getAttribute('data-original-title')) {
            element.setAttribute('title', element.getAttribute('data-original-title'));
            element.removeAttribute('data-original-title');
        }
    }

    positionTooltip(tooltip, element) {
        const rect = element.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();

        let top = rect.top - tooltipRect.height - 8;
        let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);

        // Adjust if tooltip goes off screen
        if (top < 0) {
            top = rect.bottom + 8;
        }
        if (left < 0) {
            left = 8;
        }
        if (left + tooltipRect.width > window.innerWidth) {
            left = window.innerWidth - tooltipRect.width - 8;
        }

        tooltip.style.top = `${top + window.scrollY}px`;
        tooltip.style.left = `${left}px`;
    }

    // Modal System
    createModalSystem() {
        // Modal container will be created dynamically
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                this.closeModal();
            }
        });
    }

    showModal(content, options = {}) {
        const modal = document.createElement('div');
        modal.className = 'modal-backdrop';
        modal.setAttribute('aria-modal', 'true');
        modal.setAttribute('role', 'dialog');

        if (options.ariaLabel) {
            modal.setAttribute('aria-label', options.ariaLabel);
        }

        modal.innerHTML = `
            <div class="modal-container">
                <div class="modal-header">
                    <h2 class="modal-title">${options.title || 'Modal'}</h2>
                    <button class="modal-close" aria-label="Close modal">
                        <span aria-hidden="true">&times;</span>
                    </button>
                </div>
                <div class="modal-content">
                    ${content}
                </div>
                ${options.footer ? `<div class="modal-footer">${options.footer}</div>` : ''}
            </div>
        `;

        // Focus trap
        const focusableElements = modal.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const firstFocusable = focusableElements[0];
        const lastFocusable = focusableElements[focusableElements.length - 1];

        modal.addEventListener('keydown', (event) => {
            if (event.key === 'Tab') {
                if (event.shiftKey) {
                    if (document.activeElement === firstFocusable) {
                        event.preventDefault();
                        lastFocusable.focus();
                    }
                } else {
                    if (document.activeElement === lastFocusable) {
                        event.preventDefault();
                        firstFocusable.focus();
                    }
                }
            }
        });

        modal.querySelector('.modal-close').onclick = () => this.closeModal();
        modal.onclick = (event) => {
            if (event.target === modal) this.closeModal();
        };

        document.body.appendChild(modal);
        document.body.classList.add('modal-open');

        // Focus first element
        if (firstFocusable) {
            firstFocusable.focus();
        }

        return modal;
    }

    closeModal() {
        const modal = document.querySelector('.modal-backdrop');
        if (modal) {
            modal.remove();
            document.body.classList.remove('modal-open');
        }
    }

    // Drag and Drop
    setupDragDrop() {
        const dropZones = document.querySelectorAll('[data-drop-zone]');

        dropZones.forEach(zone => {
            zone.addEventListener('dragover', this.handleDragOver.bind(this));
            zone.addEventListener('dragleave', this.handleDragLeave.bind(this));
            zone.addEventListener('drop', this.handleDrop.bind(this));
        });
    }

    handleDragOver(event) {
        event.preventDefault();
        event.currentTarget.classList.add('drag-over');
    }

    handleDragLeave(event) {
        if (!event.currentTarget.contains(event.relatedTarget)) {
            event.currentTarget.classList.remove('drag-over');
        }
    }

    handleDrop(event) {
        event.preventDefault();
        event.currentTarget.classList.remove('drag-over');

        const files = Array.from(event.dataTransfer.files);
        const dropZone = event.currentTarget;

        // Dispatch custom event
        dropZone.dispatchEvent(new CustomEvent('filesDropped', {
            detail: { files }
        }));
    }

    // Keyboard Navigation
    setupKeyboardNavigation() {
        // Arrow key navigation for button groups
        document.addEventListener('keydown', (event) => {
            if (event.target.matches('[role="radiogroup"] button, .button-group button')) {
                this.handleButtonGroupNavigation(event);
            }
        });
    }

    handleButtonGroupNavigation(event) {
        const { key } = event;
        if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(key)) return;

        event.preventDefault();

        const currentButton = event.target;
        const buttonGroup = currentButton.closest('[role="radiogroup"], .button-group');
        const buttons = Array.from(buttonGroup.querySelectorAll('button:not([disabled])'));
        const currentIndex = buttons.indexOf(currentButton);

        let nextIndex;
        if (key === 'ArrowLeft' || key === 'ArrowUp') {
            nextIndex = currentIndex === 0 ? buttons.length - 1 : currentIndex - 1;
        } else {
            nextIndex = currentIndex === buttons.length - 1 ? 0 : currentIndex + 1;
        }

        buttons[nextIndex].focus();
    }

    // Accessibility
    setupAccessibility() {
        // Announce page changes to screen readers
        this.announcePageChange();

        // Skip links
        this.createSkipLinks();

        // Focus management
        this.setupFocusManagement();

        // High contrast detection
        this.detectHighContrast();
    }

    announcePageChange() {
        const announcer = document.createElement('div');
        announcer.setAttribute('aria-live', 'assertive');
        announcer.setAttribute('aria-atomic', 'true');
        announcer.className = 'sr-only';
        announcer.id = 'page-announcer';
        document.body.appendChild(announcer);
    }

    announce(message) {
        const announcer = document.getElementById('page-announcer');
        if (announcer) {
            announcer.textContent = message;
            setTimeout(() => {
                announcer.textContent = '';
            }, 1000);
        }
    }

    createSkipLinks() {
        const skipLinks = document.createElement('div');
        skipLinks.className = 'skip-links';
        skipLinks.innerHTML = `
            <a href="#main-content" class="skip-link" data-i18n="skip-to-main">Skip to main content</a>
            <a href="#navigation" class="skip-link" data-i18n="skip-to-nav">Skip to navigation</a>
        `;
        document.body.insertBefore(skipLinks, document.body.firstChild);
    }

    setupFocusManagement() {
        // Focus visible on keyboard navigation only
        document.addEventListener('mousedown', () => {
            document.body.classList.add('using-mouse');
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Tab') {
                document.body.classList.remove('using-mouse');
            }
        });
    }

    detectHighContrast() {
        // Detect Windows high contrast mode
        const testElement = document.createElement('div');
        testElement.style.color = 'rgb(31, 32, 33)';
        testElement.style.backgroundColor = 'rgb(31, 32, 33)';
        document.body.appendChild(testElement);

        const styles = window.getComputedStyle(testElement);
        if (styles.color !== styles.backgroundColor) {
            document.body.classList.add('high-contrast');
        }

        document.body.removeChild(testElement);
    }

    // Internationalization
    setupInternationalization() {
        this.currentLanguage = document.documentElement.lang || 'en';
        this.translations = {};
        this.loadTranslations();
    }

    async loadTranslations() {
        try {
            const response = await fetch(`/api/translations/${this.currentLanguage}`);
            if (response.ok) {
                this.translations = await response.json();
                this.applyTranslations();
            }
        } catch (error) {
            console.warn('Failed to load translations:', error);
        }
    }

    applyTranslations() {
        const elements = document.querySelectorAll('[data-i18n]');
        elements.forEach(element => {
            const key = element.getAttribute('data-i18n');
            const translation = this.translations[key];
            if (translation) {
                element.textContent = translation;
            }
        });

        // Apply aria-label translations
        const ariaElements = document.querySelectorAll('[data-i18n-aria-label]');
        ariaElements.forEach(element => {
            const key = element.getAttribute('data-i18n-aria-label');
            const translation = this.translations[key];
            if (translation) {
                element.setAttribute('aria-label', translation);
            }
        });
    }

    setLanguage(language) {
        this.currentLanguage = language;
        document.documentElement.lang = language;
        this.loadTranslations();
    }

    // Utility Methods
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatDuration(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);

        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }

    // Theme Toggle System
    setupThemeToggle() {
        const themeToggle = document.getElementById('themeToggle');
        if (!themeToggle) return;

        // Load saved theme preference
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            document.body.classList.add('dark-mode');
            this.updateThemeIcon(true);
        }

        // Theme toggle event listener
        themeToggle.addEventListener('click', () => {
            const isDark = document.body.classList.toggle('dark-mode');
            this.updateThemeIcon(isDark);

            // Save preference
            localStorage.setItem('theme', isDark ? 'dark' : 'light');

            // Dispatch custom event for other components
            window.dispatchEvent(new CustomEvent('themeChanged', {
                detail: { isDark }
            }));
        });
    }

    updateThemeIcon(isDark) {
        const themeToggle = document.getElementById('themeToggle');
        if (!themeToggle) return;

        const icon = themeToggle.querySelector('i');
        if (icon) {
            icon.className = isDark ? 'bi bi-sun' : 'bi bi-moon-stars';
        }

        // Update aria-label
        themeToggle.setAttribute('aria-label',
            isDark ? 'Switch to light mode' : 'Switch to dark mode');
    }
}

// Initialize enhanced UI when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.enhancedUI = new EnhancedUI();
    });
} else {
    window.enhancedUI = new EnhancedUI();
}