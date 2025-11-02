/**
 * Material Manager JavaScript - Professional material and settings management
 */

class MaterialManager {
    constructor() {
        this.materials = new Map();
        this.profiles = new Map();
        this.printers = new Map();
        this.currentMaterial = null;
        this.currentProfile = null;
        this.searchTimeout = null;

        this.init();
    }

    async init() {
        await this.loadData();
        this.setupEventListeners();
        this.renderMaterialList();
        this.updateDashboard();
    }

    async loadData() {
        try {
            // Load materials
            const materialsResponse = await fetch('/api/materials');
            const materialsData = await materialsResponse.json();
            materialsData.forEach(material => {
                this.materials.set(material.id, material);
            });

            // Load print profiles
            const profilesResponse = await fetch('/api/profiles');
            const profilesData = await profilesResponse.json();
            profilesData.forEach(profile => {
                this.profiles.set(profile.id, profile);
            });

            // Load printer profiles
            const printersResponse = await fetch('/api/printers');
            const printersData = await printersResponse.json();
            printersData.forEach(printer => {
                this.printers.set(printer.name, printer);
            });

        } catch (error) {
            console.error('Failed to load data:', error);
        }
    }

    setupEventListeners() {
        // Search functionality
        const searchInput = document.getElementById('material-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(this.searchTimeout);
                this.searchTimeout = setTimeout(() => {
                    this.filterMaterials(e.target.value);
                }, 300);
            });
        }

        // Filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const filter = e.target.dataset.filter;
                this.filterByType(filter);

                // Update active state
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
            });
        });

        // Material selection
        document.addEventListener('click', (e) => {
            if (e.target.closest('.material-item')) {
                const materialId = e.target.closest('.material-item').dataset.materialId;
                this.selectMaterial(materialId);
            }
        });

        // Profile selection
        document.addEventListener('change', (e) => {
            if (e.target.id === 'profile-select') {
                this.selectProfile(e.target.value);
            }
        });

        // Save buttons
        document.getElementById('save-material')?.addEventListener('click', () => {
            this.saveMaterial();
        });

        document.getElementById('save-profile')?.addEventListener('click', () => {
            this.saveProfile();
        });

        // Temperature controls
        document.querySelectorAll('.temp-control input').forEach(input => {
            input.addEventListener('change', (e) => {
                this.updateTemperature(e.target.name, e.target.value);
            });
        });

        // Speed controls
        document.querySelectorAll('.speed-control input').forEach(input => {
            input.addEventListener('change', (e) => {
                this.updateSpeed(e.target.name, e.target.value);
            });
        });

        // Export/Import
        document.getElementById('export-settings')?.addEventListener('click', () => {
            this.exportSettings();
        });

        document.getElementById('import-settings')?.addEventListener('click', () => {
            document.getElementById('import-file').click();
        });

        document.getElementById('import-file')?.addEventListener('change', (e) => {
            this.importSettings(e.target.files[0]);
        });
    }

    renderMaterialList() {
        const container = document.getElementById('material-list');
        if (!container) return;

        container.innerHTML = '';

        this.materials.forEach((material, id) => {
            const item = this.createMaterialItem(material);
            container.appendChild(item);
        });
    }

    createMaterialItem(material) {
        const item = document.createElement('div');
        item.className = 'material-item';
        item.dataset.materialId = material.id;

        const typeIcon = this.getTypeIcon(material.type);
        const strengthBar = this.createStrengthBar(material.tensile_strength);

        item.innerHTML = `
            <div class="material-header">
                <div class="material-icon">${typeIcon}</div>
                <div class="material-info">
                    <div class="material-name">${material.name}</div>
                    <div class="material-brand">${material.brand}</div>
                </div>
                <div class="material-type">${material.type}</div>
            </div>
            <div class="material-properties">
                <div class="property">
                    <span class="label">Print Temp:</span>
                    <span class="value">${material.print_temp_optimal}°C</span>
                </div>
                <div class="property">
                    <span class="label">Bed Temp:</span>
                    <span class="value">${material.bed_temp_optimal}°C</span>
                </div>
                <div class="property">
                    <span class="label">Strength:</span>
                    <div class="strength-indicator">${strengthBar}</div>
                </div>
            </div>
            <div class="material-tags">
                ${material.food_safe ? '<span class="tag food-safe">Food Safe</span>' : ''}
                ${material.biodegradable ? '<span class="tag eco">Eco-Friendly</span>' : ''}
                ${material.uv_resistant ? '<span class="tag uv">UV Resistant</span>' : ''}
                ${material.chemical_resistant ? '<span class="tag chemical">Chemical Resistant</span>' : ''}
            </div>
        `;

        return item;
    }

    getTypeIcon(type) {
        const icons = {
            'PLA': '🌱',
            'ABS': '🔧',
            'PETG': '💎',
            'TPU': '🔄',
            'Nylon': '💪',
            'PC': '🔥',
            'ASA': '☀️',
            'PVA': '💧',
            'Carbon Fiber': '⚡',
            'Wood Fill': '🌳',
            'Metal Fill': '⚙️'
        };
        return icons[type] || '📦';
    }

    createStrengthBar(strength) {
        const maxStrength = 100;
        const percentage = Math.min((strength / maxStrength) * 100, 100);

        let color = '#ff4444';
        if (percentage > 60) color = '#44ff44';
        else if (percentage > 30) color = '#ffaa44';

        return `
            <div class="strength-bar">
                <div class="strength-fill" style="width: ${percentage}%; background: ${color}"></div>
                <span class="strength-value">${strength} MPa</span>
            </div>
        `;
    }

    filterMaterials(searchTerm) {
        const items = document.querySelectorAll('.material-item');

        items.forEach(item => {
            const material = this.materials.get(item.dataset.materialId);
            const matchesSearch = !searchTerm ||
                material.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                material.brand.toLowerCase().includes(searchTerm.toLowerCase()) ||
                material.type.toLowerCase().includes(searchTerm.toLowerCase());

            item.style.display = matchesSearch ? 'block' : 'none';
        });
    }

    filterByType(type) {
        const items = document.querySelectorAll('.material-item');

        items.forEach(item => {
            const material = this.materials.get(item.dataset.materialId);
            const matchesFilter = type === 'all' || material.type === type;

            item.style.display = matchesFilter ? 'block' : 'none';
        });
    }

    selectMaterial(materialId) {
        this.currentMaterial = this.materials.get(materialId);

        // Update UI selection
        document.querySelectorAll('.material-item').forEach(item => {
            item.classList.remove('selected');
        });
        document.querySelector(`[data-material-id="${materialId}"]`).classList.add('selected');

        // Load material details
        this.loadMaterialDetails();
        this.loadProfilesForMaterial();

        // Update charts
        this.updatePropertyCharts();
        this.updateCostCalculator();
    }

    selectProfile(profileId) {
        this.currentProfile = this.profiles.get(profileId);
        this.loadProfileDetails();
    }

    loadMaterialDetails() {
        if (!this.currentMaterial) return;

        const material = this.currentMaterial;

        // Basic info
        document.getElementById('detail-name').textContent = material.name;
        document.getElementById('detail-brand').textContent = material.brand;
        document.getElementById('detail-type').textContent = material.type;
        document.getElementById('detail-color').textContent = material.color;
        document.getElementById('detail-diameter').textContent = `${material.diameter}mm`;

        // Print settings
        document.getElementById('print-temp-min').value = material.print_temp_min;
        document.getElementById('print-temp-max').value = material.print_temp_max;
        document.getElementById('print-temp-optimal').value = material.print_temp_optimal;
        document.getElementById('bed-temp-min').value = material.bed_temp_min;
        document.getElementById('bed-temp-max').value = material.bed_temp_max;
        document.getElementById('bed-temp-optimal').value = material.bed_temp_optimal;

        // Physical properties
        document.getElementById('density').value = material.density;
        document.getElementById('tensile-strength').value = material.tensile_strength;
        document.getElementById('elongation').value = material.elongation_at_break;
        document.getElementById('flexural-strength').value = material.flexural_strength;

        // Special properties
        document.getElementById('moisture-sensitive').checked = material.moisture_sensitive;
        document.getElementById('food-safe').checked = material.food_safe;
        document.getElementById('biodegradable').checked = material.biodegradable;
        document.getElementById('uv-resistant').checked = material.uv_resistant;

        // Processing notes
        document.getElementById('processing-tips').value = material.processing_tips || '';
        document.getElementById('safety-warnings').value = material.safety_warnings || '';

        // Cost info
        document.getElementById('cost-per-kg').value = material.cost_per_kg;
        document.getElementById('availability').value = material.availability;
    }

    loadProfilesForMaterial() {
        if (!this.currentMaterial) return;

        const select = document.getElementById('profile-select');
        select.innerHTML = '<option value="">Select Profile</option>';

        this.profiles.forEach((profile, id) => {
            if (profile.material_id === this.currentMaterial.id) {
                const option = document.createElement('option');
                option.value = id;
                option.textContent = `${profile.quality} - ${profile.name}`;
                select.appendChild(option);
            }
        });
    }

    loadProfileDetails() {
        if (!this.currentProfile) return;

        const profile = this.currentProfile;

        // Layer settings
        document.getElementById('layer-height').value = profile.layer_height;
        document.getElementById('first-layer-height').value = profile.first_layer_height;

        // Temperature
        document.getElementById('nozzle-temp').value = profile.nozzle_temp;
        document.getElementById('bed-temp').value = profile.bed_temp;

        // Speed settings
        document.getElementById('print-speed').value = profile.print_speed;
        document.getElementById('travel-speed').value = profile.travel_speed;
        document.getElementById('first-layer-speed').value = profile.first_layer_speed;

        // Quality settings
        document.getElementById('wall-count').value = profile.wall_count;
        document.getElementById('infill-density').value = profile.infill_density;
        document.getElementById('infill-pattern').value = profile.infill_pattern;

        // Support settings
        document.getElementById('support-enable').checked = profile.support_enable;
        document.getElementById('support-density').value = profile.support_density;
        document.getElementById('support-overhang').value = profile.support_overhang_angle;
    }

    updatePropertyCharts() {
        if (!this.currentMaterial) return;

        // Temperature gauge
        this.updateTemperatureGauge();

        // Strength comparison
        this.updateStrengthChart();

        // Property radar
        this.updatePropertyRadar();
    }

    updateTemperatureGauge() {
        const material = this.currentMaterial;
        const canvas = document.getElementById('temp-gauge');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const radius = Math.min(centerX, centerY) - 20;

        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw gauge background
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0.75 * Math.PI, 2.25 * Math.PI);
        ctx.lineWidth = 20;
        ctx.strokeStyle = '#333';
        ctx.stroke();

        // Draw temperature range
        const minAngle = 0.75 * Math.PI;
        const maxAngle = 2.25 * Math.PI;
        const tempRange = material.print_temp_max - material.print_temp_min;
        const optimalAngle = minAngle + ((material.print_temp_optimal - material.print_temp_min) / tempRange) * (maxAngle - minAngle);

        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, minAngle, optimalAngle);
        ctx.lineWidth = 20;
        ctx.strokeStyle = '#4CAF50';
        ctx.stroke();

        // Draw temperature text
        ctx.fillStyle = '#fff';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(`${material.print_temp_optimal}°C`, centerX, centerY + 5);
        ctx.font = '12px Arial';
        ctx.fillText('Optimal Print Temp', centerX, centerY + 25);
    }

    updateStrengthChart() {
        const material = this.currentMaterial;
        const canvas = document.getElementById('strength-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;

        ctx.clearRect(0, 0, width, height);

        // Sample materials for comparison
        const materials = [
            { name: 'PLA', strength: 65 },
            { name: 'ABS', strength: 40 },
            { name: 'PETG', strength: 50 },
            { name: 'Nylon', strength: 75 },
            { name: 'Current', strength: material.tensile_strength }
        ];

        const maxStrength = 100;
        const barWidth = width / materials.length - 10;
        const barSpacing = 10;

        materials.forEach((mat, index) => {
            const x = index * (barWidth + barSpacing) + 5;
            const barHeight = (mat.strength / maxStrength) * (height - 40);
            const y = height - barHeight - 20;

            // Draw bar
            ctx.fillStyle = mat.name === 'Current' ? '#FF6B35' : '#4CAF50';
            ctx.fillRect(x, y, barWidth, barHeight);

            // Draw label
            ctx.fillStyle = '#fff';
            ctx.font = '10px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(mat.name, x + barWidth / 2, height - 5);
            ctx.fillText(`${mat.strength}`, x + barWidth / 2, y - 5);
        });
    }

    updatePropertyRadar() {
        const material = this.currentMaterial;
        const canvas = document.getElementById('property-radar');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const radius = Math.min(centerX, centerY) - 30;

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Properties to display
        const properties = [
            { name: 'Strength', value: material.tensile_strength / 100 },
            { name: 'Flexibility', value: material.elongation_at_break / 200 },
            { name: 'Heat Resist', value: material.print_temp_optimal / 300 },
            { name: 'Durability', value: material.flexural_strength / 150 },
            { name: 'Ease of Use', value: material.type === 'PLA' ? 0.9 : 0.6 }
        ];

        const angleStep = (2 * Math.PI) / properties.length;

        // Draw grid
        for (let i = 1; i <= 5; i++) {
            ctx.beginPath();
            for (let j = 0; j < properties.length; j++) {
                const angle = j * angleStep - Math.PI / 2;
                const x = centerX + Math.cos(angle) * (radius * i / 5);
                const y = centerY + Math.sin(angle) * (radius * i / 5);

                if (j === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.closePath();
            ctx.strokeStyle = '#333';
            ctx.stroke();
        }

        // Draw axes
        for (let i = 0; i < properties.length; i++) {
            const angle = i * angleStep - Math.PI / 2;
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.lineTo(
                centerX + Math.cos(angle) * radius,
                centerY + Math.sin(angle) * radius
            );
            ctx.strokeStyle = '#666';
            ctx.stroke();

            // Label
            const labelX = centerX + Math.cos(angle) * (radius + 20);
            const labelY = centerY + Math.sin(angle) * (radius + 20);
            ctx.fillStyle = '#fff';
            ctx.font = '10px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(properties[i].name, labelX, labelY);
        }

        // Draw data
        ctx.beginPath();
        for (let i = 0; i < properties.length; i++) {
            const angle = i * angleStep - Math.PI / 2;
            const value = Math.min(properties[i].value, 1);
            const x = centerX + Math.cos(angle) * (radius * value);
            const y = centerY + Math.sin(angle) * (radius * value);

            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.fillStyle = 'rgba(76, 175, 80, 0.3)';
        ctx.fill();
        ctx.strokeStyle = '#4CAF50';
        ctx.lineWidth = 2;
        ctx.stroke();
    }

    updateCostCalculator() {
        if (!this.currentMaterial) return;

        const material = this.currentMaterial;
        const weight = parseFloat(document.getElementById('calc-weight')?.value || 50);
        const cost = (weight / 1000) * material.cost_per_kg;

        document.getElementById('calc-cost').textContent = `$${cost.toFixed(2)}`;
        document.getElementById('calc-cost-per-kg').textContent = `$${material.cost_per_kg}/kg`;
    }

    updateTemperature(field, value) {
        if (!this.currentMaterial) return;
        this.currentMaterial[field] = parseFloat(value);
        this.updateTemperatureGauge();
    }

    updateSpeed(field, value) {
        if (!this.currentProfile) return;
        this.currentProfile[field] = parseFloat(value);
    }

    async saveMaterial() {
        if (!this.currentMaterial) return;

        try {
            const response = await fetch(`/api/materials/${this.currentMaterial.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.currentMaterial)
            });

            if (response.ok) {
                this.showNotification('Material saved successfully', 'success');
                this.renderMaterialList();
            } else {
                throw new Error('Failed to save material');
            }
        } catch (error) {
            this.showNotification('Failed to save material', 'error');
            console.error(error);
        }
    }

    async saveProfile() {
        if (!this.currentProfile) return;

        try {
            const response = await fetch(`/api/profiles/${this.currentProfile.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.currentProfile)
            });

            if (response.ok) {
                this.showNotification('Profile saved successfully', 'success');
            } else {
                throw new Error('Failed to save profile');
            }
        } catch (error) {
            this.showNotification('Failed to save profile', 'error');
            console.error(error);
        }
    }

    exportSettings() {
        const settings = {
            materials: Array.from(this.materials.values()),
            profiles: Array.from(this.profiles.values()),
            printers: Array.from(this.printers.values()),
            exported_at: new Date().toISOString()
        };

        const blob = new Blob([JSON.stringify(settings, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = `3dprint_settings_${new Date().toISOString().split('T')[0]}.json`;
        a.click();

        URL.revokeObjectURL(url);
        this.showNotification('Settings exported successfully', 'success');
    }

    async importSettings(file) {
        if (!file) return;

        try {
            const text = await file.text();
            const settings = JSON.parse(text);

            // Validate format
            if (!settings.materials && !settings.profiles && !settings.printers) {
                throw new Error('Invalid settings file format');
            }

            // Import materials
            if (settings.materials) {
                for (const material of settings.materials) {
                    this.materials.set(material.id, material);
                }
            }

            // Import profiles
            if (settings.profiles) {
                for (const profile of settings.profiles) {
                    this.profiles.set(profile.id, profile);
                }
            }

            // Import printers
            if (settings.printers) {
                for (const printer of settings.printers) {
                    this.printers.set(printer.name, printer);
                }
            }

            this.renderMaterialList();
            this.showNotification('Settings imported successfully', 'success');

        } catch (error) {
            this.showNotification('Failed to import settings', 'error');
            console.error(error);
        }
    }

    updateDashboard() {
        // Update statistics
        document.getElementById('total-materials').textContent = this.materials.size;
        document.getElementById('total-profiles').textContent = this.profiles.size;
        document.getElementById('total-printers').textContent = this.printers.size;

        // Most used material
        const mostUsed = Array.from(this.materials.values())[0];
        if (mostUsed) {
            document.getElementById('most-used-material').textContent = mostUsed.name;
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.classList.add('show');
        }, 100);

        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.materialManager = new MaterialManager();
});