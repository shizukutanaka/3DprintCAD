/**
 * Client-side validation and sanitization for production security
 * Validates input before sending to server to reduce load and improve UX
 */

class ClientValidator {
    constructor() {
        this.allowedFileTypes = new Set(['.stl', '.obj', '.ply', '.3mf', '.amf']);
        this.maxFileSizeMB = 100;
        this.patterns = {
            sql: /(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)|(--|;|\/\*|\*\/)|(\bOR\b.*=.*)|(\bUNION\b.*\bSELECT\b)/i,
            xss: /<script[^>]*>.*?<\/script>|javascript:|on\w+\s*=|<iframe[^>]*>|<object[^>]*>|<embed[^>]*>/i,
            cmdInjection: /[;&|`$()]|\$\{.*\}|`.*`|\$\(.*\)/i
        };
    }

    /**
     * Validate file before upload
     */
    validateFile(file) {
        const errors = [];

        // Check file exists
        if (!file) {
            errors.push('No file selected');
            return { valid: false, errors };
        }

        // Check filename
        if (!file.name || file.name.trim() === '') {
            errors.push('Invalid filename');
            return { valid: false, errors };
        }

        // Check for path traversal
        if (file.name.includes('..') || file.name.includes('/') || file.name.includes('\\')) {
            errors.push('Invalid filename: path traversal detected');
            return { valid: false, errors };
        }

        // Check file extension
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        if (!this.allowedFileTypes.has(extension)) {
            errors.push(`Invalid file type. Allowed: ${Array.from(this.allowedFileTypes).join(', ')}`);
        }

        // Check file size
        const fileSizeMB = file.size / (1024 * 1024);
        if (fileSizeMB > this.maxFileSizeMB) {
            errors.push(`File size ${fileSizeMB.toFixed(2)}MB exceeds limit of ${this.maxFileSizeMB}MB`);
        }

        // Check for null bytes in filename
        if (file.name.includes('\x00')) {
            errors.push('Invalid filename: null bytes detected');
        }

        return {
            valid: errors.length === 0,
            errors,
            file: {
                name: file.name,
                size: file.size,
                type: file.type,
                extension
            }
        };
    }

    /**
     * Validate multiple files
     */
    validateFiles(files, maxFiles = 20) {
        const results = {
            valid: true,
            files: [],
            errors: []
        };

        if (!files || files.length === 0) {
            results.valid = false;
            results.errors.push('No files selected');
            return results;
        }

        if (files.length > maxFiles) {
            results.valid = false;
            results.errors.push(`Too many files. Maximum: ${maxFiles}`);
            return results;
        }

        for (const file of files) {
            const fileResult = this.validateFile(file);
            if (!fileResult.valid) {
                results.valid = false;
                results.errors.push(`${file.name}: ${fileResult.errors.join(', ')}`);
            }
            results.files.push(fileResult);
        }

        return results;
    }

    /**
     * Sanitize string input
     */
    sanitizeString(value, allowHtml = false) {
        if (!value) return value;

        // Remove null bytes
        value = value.replace(/\x00/g, '');

        // Remove control characters except newline and tab
        value = value.replace(/[\x00-\x1F\x7F-\x9F]/g, (char) => {
            return ['\n', '\t'].includes(char) ? char : '';
        });

        if (!allowHtml) {
            // Escape HTML special characters
            const htmlEscapes = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#x27;',
                '/': '&#x2F;'
            };
            value = value.replace(/[&<>"'\/]/g, char => htmlEscapes[char]);
        }

        return value.trim();
    }

    /**
     * Check for security threats in string
     */
    checkSecurityThreats(value, fieldName = 'field') {
        const threats = [];

        if (!value) {
            return { safe: true, threats };
        }

        // SQL Injection check
        if (this.patterns.sql.test(value)) {
            threats.push(`${fieldName} contains potential SQL injection pattern`);
        }

        // XSS check
        if (this.patterns.xss.test(value)) {
            threats.push(`${fieldName} contains potential XSS pattern`);
        }

        // Command Injection check
        if (this.patterns.cmdInjection.test(value)) {
            threats.push(`${fieldName} contains potential command injection pattern`);
        }

        return {
            safe: threats.length === 0,
            threats
        };
    }

    /**
     * Validate numeric input with range
     */
    validateNumber(value, options = {}) {
        const {
            fieldName = 'field',
            required = false,
            min = null,
            max = null,
            integer = false
        } = options;

        const errors = [];

        if (required && (value === null || value === undefined || value === '')) {
            errors.push(`${fieldName} is required`);
            return { valid: false, errors, value: null };
        }

        if (value === null || value === undefined || value === '') {
            return { valid: true, errors: [], value: null };
        }

        const numValue = Number(value);

        if (isNaN(numValue)) {
            errors.push(`${fieldName} must be a number`);
            return { valid: false, errors, value: null };
        }

        if (integer && !Number.isInteger(numValue)) {
            errors.push(`${fieldName} must be an integer`);
        }

        if (min !== null && numValue < min) {
            errors.push(`${fieldName} must be >= ${min}`);
        }

        if (max !== null && numValue > max) {
            errors.push(`${fieldName} must be <= ${max}`);
        }

        return {
            valid: errors.length === 0,
            errors,
            value: numValue
        };
    }

    /**
     * Validate mesh settings
     */
    validateMeshSettings(data) {
        const errors = [];
        const sanitized = {};

        // Validate min_wall_thickness
        const wallThickness = this.validateNumber(data.min_wall_thickness, {
            fieldName: 'Wall Thickness',
            min: 0.1,
            max: 10.0
        });
        if (!wallThickness.valid) {
            errors.push(...wallThickness.errors);
        }
        sanitized.min_wall_thickness = wallThickness.value || 0.8;

        // Validate min_feature_size
        const featureSize = this.validateNumber(data.min_feature_size, {
            fieldName: 'Feature Size',
            min: 0.1,
            max: 10.0
        });
        if (!featureSize.valid) {
            errors.push(...featureSize.errors);
        }
        sanitized.min_feature_size = featureSize.value || 0.4;

        // Validate max_overhang_angle
        const overhang = this.validateNumber(data.max_overhang_angle, {
            fieldName: 'Overhang Angle',
            min: 0,
            max: 90,
            integer: true
        });
        if (!overhang.valid) {
            errors.push(...overhang.errors);
        }
        sanitized.max_overhang_angle = overhang.value || 60;

        return {
            valid: errors.length === 0,
            errors,
            data: sanitized
        };
    }

    /**
     * Validate slice settings
     */
    validateSliceSettings(data) {
        const errors = [];
        const sanitized = {};

        // Layer height (required)
        const layerHeight = this.validateNumber(data.layer_height, {
            fieldName: 'Layer Height',
            required: true,
            min: 0.05,
            max: 1.0
        });
        if (!layerHeight.valid) {
            errors.push(...layerHeight.errors);
        }
        sanitized.layer_height = layerHeight.value;

        // Infill density
        const infill = this.validateNumber(data.infill_density, {
            fieldName: 'Infill Density',
            min: 0,
            max: 100,
            integer: true
        });
        if (!infill.valid) {
            errors.push(...infill.errors);
        }
        sanitized.infill_density = infill.value || 20;

        // Print speed
        const speed = this.validateNumber(data.print_speed, {
            fieldName: 'Print Speed',
            min: 10,
            max: 300,
            integer: true
        });
        if (!speed.valid) {
            errors.push(...speed.errors);
        }
        sanitized.print_speed = speed.value || 60;

        // Support enabled (boolean)
        sanitized.support_enabled = Boolean(data.support_enabled);

        // Support angle
        if (sanitized.support_enabled) {
            const supportAngle = this.validateNumber(data.support_angle, {
                fieldName: 'Support Angle',
                min: 0,
                max: 90,
                integer: true
            });
            if (!supportAngle.valid) {
                errors.push(...supportAngle.errors);
            }
            sanitized.support_angle = supportAngle.value || 45;
        }

        return {
            valid: errors.length === 0,
            errors,
            data: sanitized
        };
    }

    /**
     * Validate form data
     */
    validateForm(formElement) {
        const errors = [];
        const data = {};

        const inputs = formElement.querySelectorAll('input, select, textarea');

        inputs.forEach(input => {
            const name = input.name || input.id;
            let value = input.value;

            // Skip validation for disabled inputs
            if (input.disabled) return;

            // Required check
            if (input.required && !value) {
                errors.push(`${name} is required`);
                input.classList.add('is-invalid');
                return;
            }

            // Type-specific validation
            if (input.type === 'number') {
                const result = this.validateNumber(value, {
                    fieldName: name,
                    required: input.required,
                    min: input.min ? parseFloat(input.min) : null,
                    max: input.max ? parseFloat(input.max) : null
                });

                if (!result.valid) {
                    errors.push(...result.errors);
                    input.classList.add('is-invalid');
                } else {
                    input.classList.remove('is-invalid');
                    value = result.value;
                }
            } else if (input.type === 'text' || input.type === 'textarea') {
                // Sanitize text input
                value = this.sanitizeString(value);

                // Check for security threats
                const security = this.checkSecurityThreats(value, name);
                if (!security.safe) {
                    errors.push(...security.threats);
                    input.classList.add('is-invalid');
                } else {
                    input.classList.remove('is-invalid');
                }
            }

            data[name] = value;
        });

        return {
            valid: errors.length === 0,
            errors,
            data
        };
    }

    /**
     * Show validation errors in UI
     */
    showErrors(errors, container = null) {
        if (!errors || errors.length === 0) return;

        const errorHtml = errors.map(error =>
            `<div class="alert alert-danger alert-dismissible fade show" role="alert">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>${this.sanitizeString(error)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>`
        ).join('');

        if (container) {
            container.innerHTML = errorHtml;
        } else {
            // Use notification system if available
            if (window.enhancedUI) {
                errors.forEach(error => {
                    window.enhancedUI.showNotification(error, 'error', 5000);
                });
            } else {
                console.error('Validation errors:', errors);
            }
        }
    }

    /**
     * Clear validation errors
     */
    clearErrors(formElement) {
        const inputs = formElement.querySelectorAll('.is-invalid');
        inputs.forEach(input => input.classList.remove('is-invalid'));

        const errorContainers = formElement.querySelectorAll('.alert-danger');
        errorContainers.forEach(container => container.remove());
    }
}

// Global validator instance
window.clientValidator = new ClientValidator();

// Auto-attach validation to forms
document.addEventListener('DOMContentLoaded', () => {
    const forms = document.querySelectorAll('form[data-validate]');

    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const result = window.clientValidator.validateForm(form);

            if (!result.valid) {
                e.preventDefault();
                window.clientValidator.showErrors(result.errors);
                return false;
            }
        });

        // Real-time validation for inputs
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', () => {
                const name = input.name || input.id;
                let value = input.value;

                if (input.type === 'number') {
                    const result = window.clientValidator.validateNumber(value, {
                        fieldName: name,
                        required: input.required,
                        min: input.min ? parseFloat(input.min) : null,
                        max: input.max ? parseFloat(input.max) : null
                    });

                    if (!result.valid) {
                        input.classList.add('is-invalid');
                    } else {
                        input.classList.remove('is-invalid');
                    }
                } else if (input.type === 'text' || input.type === 'textarea') {
                    const security = window.clientValidator.checkSecurityThreats(value, name);
                    if (!security.safe) {
                        input.classList.add('is-invalid');
                    } else {
                        input.classList.remove('is-invalid');
                    }
                }
            });
        });
    });
});
