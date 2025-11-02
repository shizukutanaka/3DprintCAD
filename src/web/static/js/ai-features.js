/**
 * AI Features for 3D Print CAD Assistant
 * Includes text-to-3D generation and AI chat assistant
 */

class AIFeatures {
    constructor() {
        this.aiFeaturesVisible = false;
        this.analysisToolsVisible = false;
        this.init();
    }

    init() {
        // Bind methods
        this.generateFromText = this.generateFromText.bind(this);
        this.askAIAssistant = this.askAIAssistant.bind(this);
        this.toggleAIFeatures = this.toggleAIFeatures.bind(this);
        this.toggleAnalysisTools = this.toggleAnalysisTools.bind(this);
        this.runStructuralAnalysis = this.runStructuralAnalysis.bind(this);
        this.runTopologyOptimization = this.runTopologyOptimization.bind(this);

        // Make functions globally available
        window.generateFromText = this.generateFromText;
        window.askAIAssistant = this.askAIAssistant;
        window.toggleAIFeatures = this.toggleAIFeatures;
        window.toggleAnalysisTools = this.toggleAnalysisTools;
        window.runStructuralAnalysis = this.runStructuralAnalysis;
        window.runTopologyOptimization = this.runTopologyOptimization;

        // Add keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'g') {
                e.preventDefault();
                this.showTextGenerator();
            }
            if (e.ctrlKey && e.key === 'h') {
                e.preventDefault();
                this.showChatAssistant();
            }
        });
    }

    toggleAIFeatures() {
        this.aiFeaturesVisible = !this.aiFeaturesVisible;

        const generatorContainer = document.getElementById('aiGeneratorContainer');
        const chatContainer = document.getElementById('aiChatContainer');
        const defectsContainer = document.getElementById('aiDefectsContainer');

        if (this.aiFeaturesVisible) {
            // Show all AI features
            if (generatorContainer) generatorContainer.style.display = 'block';
            if (chatContainer) chatContainer.style.display = 'block';
            if (defectsContainer) defectsContainer.style.display = 'block';
            // Hide analysis tools
            if (this.analysisToolsVisible) {
                this.toggleAnalysisTools();
            }
        } else {
            // Hide AI features
            if (generatorContainer) generatorContainer.style.display = 'none';
            if (chatContainer) chatContainer.style.display = 'none';
            if (defectsContainer) defectsContainer.style.display = 'none';
        }

        // Update nav button
        const aiButton = document.querySelector('[onclick="toggleAIFeatures()"]');
        if (aiButton) {
            aiButton.classList.toggle('active', this.aiFeaturesVisible);
        }
    }

    toggleAnalysisTools() {
        this.analysisToolsVisible = !this.analysisToolsVisible;

        const analysisContainer = document.getElementById('analysisContainer');

        if (this.analysisToolsVisible) {
            // Show analysis tools
            if (analysisContainer) analysisContainer.style.display = 'block';
            // Hide AI features
            if (this.aiFeaturesVisible) {
                this.toggleAIFeatures();
            }
        } else {
            // Hide analysis tools
            if (analysisContainer) analysisContainer.style.display = 'none';
        }

    runStructuralAnalysis() {
        const form = document.getElementById('structuralAnalysisForm');
        const resultsDiv = document.getElementById('analysisResults');

        if (!form || !resultsDiv) {
            console.error('Required elements not found');
            return;
        }

        const formData = new FormData(form);
        const fileInput = form.querySelector('input[type="file"]');

        if (!fileInput || !fileInput.files[0]) {
            this.showNotification('Please select a 3D model file', 'warning');
            return;
        }

        // Show loading state
        resultsDiv.style.display = 'block';
        resultsDiv.className = 'alert alert-info mt-2';
        resultsDiv.innerHTML = '<small>Running structural analysis...</small>';

        // Send request
        fetch('/api/simulation/analyze', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const result = data.analysis_result;
                let html = `
                    <strong>Analysis Results:</strong><br>
                    <small>
                    Max Displacement: ${result.max_displacement.toFixed(3)} mm<br>
                    Max Stress: ${result.max_stress.toFixed(1)} MPa<br>
                    Max Strain: ${(result.max_strain * 100).toFixed(2)}%<br>
                    Material: ${data.material_used}<br>
                    Converged: ${result.converged ? 'Yes' : 'No'}<br>
                    Iterations: ${result.iterations}
                    </small>
                `;

                if (result.fundamental_frequency) {
                    html += `<br><small>Fundamental Frequency: ${result.fundamental_frequency.toFixed(1)} Hz</small>`;
                }

                if (data.recommendations && data.recommendations.length > 0) {
                    html += '<br><br><strong>Recommendations:</strong><br><small>';
                    data.recommendations.forEach(rec => {
                        const severityClass = rec.severity === 'critical' ? 'text-danger' :
                                            rec.severity === 'high' ? 'text-warning' : 'text-info';
                        html += `<span class="${severityClass}">• ${rec.description}</span><br>`;
                    });
                    html += '</small>';
                }

                resultsDiv.className = 'alert alert-success mt-2';
                resultsDiv.innerHTML = html;
            } else {
                resultsDiv.className = 'alert alert-danger mt-2';
                resultsDiv.innerHTML = `<small>Error: ${data.error || 'Analysis failed'}</small>`;
            }
        })
        .catch(error => {
            console.error('Analysis error:', error);
            resultsDiv.className = 'alert alert-danger mt-2';
            resultsDiv.innerHTML = '<small>Error: Failed to run analysis</small>';
        });
    }

    runTopologyOptimization() {
        const form = document.getElementById('topologyOptimizationForm');
        const resultsDiv = document.getElementById('topologyResults');

        if (!form || !resultsDiv) {
            console.error('Required elements not found');
            return;
        }

        const formData = new FormData(form);
        const fileInput = form.querySelector('input[type="file"]');

        if (!fileInput || !fileInput.files[0]) {
            this.showNotification('Please select a 3D model file', 'warning');
            return;
        }

        // Show loading state
        resultsDiv.style.display = 'block';
        resultsDiv.className = 'alert alert-warning mt-2';
        resultsDiv.innerHTML = '<small>Running topology optimization... This may take several minutes.</small>';

        // Send request
        fetch('/api/topology/optimize', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const result = data.optimization_result;
                let html = `
                    <strong>Optimization Results:</strong><br>
                    <small>
                    Final Objective: ${result.final_objective.toFixed(4)}<br>
                    Final Volume Fraction: ${(result.final_volume_fraction * 100).toFixed(1)}%<br>
                    Iterations Used: ${result.iterations_used}<br>
                    Converged: ${result.convergence_achieved ? 'Yes' : 'No'}<br>
                    Optimization Time: ${result.optimization_time.toFixed(1)}s
                    </small>
                `;

                if (data.download_url) {
                    html += `<br><br><a href="${data.download_url}" class="btn btn-sm btn-outline-success" download>
                        <i class="bi bi-download me-1"></i>Download Optimized Model
                    </a>`;
                }

                resultsDiv.className = 'alert alert-success mt-2';
                resultsDiv.innerHTML = html;
            } else {
                resultsDiv.className = 'alert alert-danger mt-2';
                resultsDiv.innerHTML = `<small>Error: ${data.error || 'Optimization failed'}</small>`;
            }
        })
        .catch(error => {
            console.error('Optimization error:', error);
            resultsDiv.className = 'alert alert-danger mt-2';
            resultsDiv.innerHTML = '<small>Error: Failed to run optimization</small>';
        });
    }

    showTextGenerator() {
        const container = document.getElementById('aiGeneratorContainer');
        if (container) {
            container.style.display = 'block';
            this.aiFeaturesVisible = true;

            // Focus on input
            const input = document.getElementById('textPrompt');
            if (input) {
                input.focus();
            }
        }
    }

    showChatAssistant() {
        const container = document.getElementById('aiChatContainer');
        if (container) {
            container.style.display = 'block';
            this.aiFeaturesVisible = true;

            // Focus on input
            const input = document.getElementById('chatQuery');
            if (input) {
                input.focus();
            }
        }
    }

    async generateFromText() {
        const promptInput = document.getElementById('textPrompt');
        const generateBtn = document.getElementById('generateBtn');
        const statusDiv = document.getElementById('generationStatus');

        if (!promptInput || !generateBtn || !statusDiv) {
            console.error('Required elements not found');
            return;
        }

        const prompt = promptInput.value.trim();
        if (!prompt) {
            this.showNotification('Please enter a text description', 'warning');
            return;
        }

        // Show loading state
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Generating...';
        statusDiv.style.display = 'block';
        statusDiv.className = 'alert alert-info';
        statusDiv.innerHTML = '<small>Generating 3D model from text...</small>';

        try {
            // Send request to backend
            const response = await fetch('/api/ai/generate-3d', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt: prompt,
                    quality: 'medium'
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();

            if (result.success) {
                statusDiv.className = 'alert alert-success';
                statusDiv.innerHTML = `
                    <small>
                        <strong>Success!</strong> Generated ${result.metadata.vertex_count} vertices,
                        ${result.metadata.face_count} faces.
                        Confidence: ${(result.confidence_score * 100).toFixed(1)}%
                    </small>
                `;

                // Clear input
                promptInput.value = '';

                // Show download option
                this.showModelDownload(result);

                // Update file list if available
                if (window.updateFileList) {
                    window.updateFileList();
                }

            } else {
                statusDiv.className = 'alert alert-danger';
                statusDiv.innerHTML = `<small>Error: ${result.error || 'Generation failed'}</small>`;
            }

        } catch (error) {
            console.error('Generation error:', error);
            statusDiv.className = 'alert alert-danger';
            statusDiv.innerHTML = `<small>Error: ${error.message}</small>`;
        } finally {
            // Reset button
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="bi bi-wand me-2"></i>Generate';
        }
    }

    async askAIAssistant() {
        const queryInput = document.getElementById('chatQuery');
        const chatBtn = document.getElementById('chatBtn');
        const responseDiv = document.getElementById('chatResponse');
        const answerDiv = document.getElementById('chatAnswer');
        const suggestionsDiv = document.getElementById('chatSuggestions');

        if (!queryInput || !chatBtn || !responseDiv || !answerDiv || !suggestionsDiv) {
            console.error('Required elements not found');
            return;
        }

        const query = queryInput.value.trim();
        if (!query) {
            this.showNotification('Please enter a question', 'warning');
            return;
        }

        // Show loading state
        chatBtn.disabled = true;
        chatBtn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Thinking...';
        responseDiv.style.display = 'block';
        answerDiv.innerHTML = '<em>Analyzing your question...</em>';

        try {
            // Send request to backend
            const response = await fetch('/api/ai/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    context: this.getCurrentContext()
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();

            // Display answer
            answerDiv.innerHTML = `<strong>Answer:</strong> ${result.answer}`;

            // Display suggestions
            if (result.suggestions && result.suggestions.length > 0) {
                const suggestionsHtml = result.suggestions.map(suggestion =>
                    `<div class="badge bg-light text-dark me-1 mb-1" style="cursor: pointer;" onclick="this.parentElement.parentElement.parentElement.querySelector('#chatQuery').value = '${suggestion.replace(/'/g, '\\\'')}'; this.parentElement.parentElement.parentElement.querySelector('#chatBtn').click();">${suggestion}</div>`
                ).join('');
                suggestionsDiv.innerHTML = `<strong>Suggestions:</strong><br>${suggestionsHtml}`;
            } else {
                suggestionsDiv.innerHTML = '';
            }

            // Clear input
            queryInput.value = '';

        } catch (error) {
            console.error('Chat error:', error);
            answerDiv.innerHTML = `<span class="text-danger">Error: ${error.message}</span>`;
            suggestionsDiv.innerHTML = '';
        } finally {
            // Reset button
            chatBtn.disabled = false;
            chatBtn.innerHTML = '<i class="bi bi-send me-2"></i>Ask';
        }
    }

    showModelDownload(result) {
        // Create a temporary download link
        const downloadBtn = document.createElement('a');
        downloadBtn.href = `/api/download/generated/${result.id || 'model'}.stl`;
        downloadBtn.download = 'generated_model.stl';
        downloadBtn.className = 'btn btn-sm btn-outline-success ms-2';
        downloadBtn.innerHTML = '<i class="bi bi-download me-1"></i>Download STL';

        const statusDiv = document.getElementById('generationStatus');
        if (statusDiv) {
            statusDiv.appendChild(downloadBtn);
        }
    }

    getCurrentContext() {
        // Get current page context for better AI responses
        const context = {
            page: window.location.pathname,
            hasUploadedFiles: document.querySelectorAll('#fileList .file-item').length > 0,
            lastAction: sessionStorage.getItem('lastAction') || null
        };

        // Add information about current validation results if available
        const issues = document.querySelectorAll('.validation-issue');
        if (issues.length > 0) {
            context.currentIssues = Array.from(issues).map(issue => issue.textContent);
        }

        return context;
    }

    showNotification(message, type = 'info') {
        // Use existing notification system if available
        if (window.enhancedUI && window.enhancedUI.showNotification) {
            window.enhancedUI.showNotification(message, type);
        } else {
            // Fallback notification
            const notification = document.createElement('div');
            notification.className = `alert alert-${type} position-fixed`;
            notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 300px;';
            notification.innerHTML = `<small>${message}</small>`;

            document.body.appendChild(notification);

            setTimeout(() => {
                notification.remove();
            }, 3000);
        }
    }
}

// Initialize AI features when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.aiFeatures = new AIFeatures();
    });
} else {
    window.aiFeatures = new AIFeatures();
}
