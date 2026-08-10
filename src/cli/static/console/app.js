// UI State
const state = {
    currentTab: 'overview',
    token: localStorage.getItem('mgmt_token') || '',
    chartsInitialized: false
};

// Initialize UI
document.addEventListener('DOMContentLoaded', () => {
    const tokenInput = document.getElementById('mgmt-token');
    if (state.token) tokenInput.value = state.token;

    tokenInput.addEventListener('change', (e) => {
        state.token = e.target.value;
        localStorage.setItem('mgmt_token', state.token);
        if (state.currentTab !== 'overview') {
            loadResource(state.currentTab);
        }
    });

    // Setup tabs
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            switchTab(tabId);
        });
    });

    // Load initial tab
    switchTab(state.currentTab);
    
    // Theme Toggle
    const themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            document.documentElement.classList.toggle('light-theme');
            const isLight = document.documentElement.classList.contains('light-theme');
            localStorage.setItem('theme', isLight ? 'light' : 'dark');
            
            // Re-init charts if needed
            if (state.chartsInitialized) {
                Chart.defaults.color = isLight ? '#495057' : '#9ca3af';
                Chart.defaults.scale.grid.color = isLight ? 'rgba(0,0,0,0.05)' : 'rgba(255, 255, 255, 0.05)';
                // We'd ideally re-render the charts here, but changing defaults works for next load
            }
        });
        
        // Restore theme
        if (localStorage.getItem('theme') === 'light') {
            document.documentElement.classList.add('light-theme');
        }
    }
    
    // Basic i18n
    const langSelect = document.getElementById('lang-select');
    if (langSelect) {
        langSelect.addEventListener('change', (e) => {
            const lang = e.target.value;
            localStorage.setItem('lang', lang);
            showToast(`Language switched to ${lang.toUpperCase()} (Translations pending)`, "success");
        });
        if (localStorage.getItem('lang')) {
            langSelect.value = localStorage.getItem('lang');
        }
    }
});

function initCharts() {
    if (state.chartsInitialized) return;
    
    // Set Chart.js defaults for dark theme
    Chart.defaults.color = '#9ca3af';
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 17, 26, 0.9)';
    Chart.defaults.plugins.tooltip.titleColor = '#fff';
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 8;
    Chart.defaults.scale.grid.color = 'rgba(255, 255, 255, 0.05)';

    // Daily Token Spend Line Chart
    const ctxSpend = document.getElementById('tokenSpendChart').getContext('2d');
    
    // Gradient for line chart
    const gradient = ctxSpend.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(59, 130, 246, 0.5)');
    gradient.addColorStop(1, 'rgba(59, 130, 246, 0.0)');

    new Chart(ctxSpend, {
        type: 'line',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [{
                label: 'Token Spend (Millions)',
                data: [12, 19, 15, 25, 22, 30, 28],
                borderColor: '#3b82f6',
                backgroundColor: gradient,
                borderWidth: 2,
                pointBackgroundColor: '#fff',
                pointBorderColor: '#3b82f6',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true, grid: { borderDash: [4, 4] } },
                x: { grid: { display: false } }
            },
            interaction: {
                intersect: false,
                mode: 'index',
            }
        }
    });

    // Model Usage Doughnut Chart
    const ctxModel = document.getElementById('modelUsageChart').getContext('2d');
    new Chart(ctxModel, {
        type: 'doughnut',
        data: {
            labels: ['GPT-4o', 'Claude 3.5 Sonnet', 'Gemini 1.5 Pro', 'Llama 3 Local'],
            datasets: [{
                data: [45, 30, 15, 10],
                backgroundColor: [
                    '#10a37f', // OpenAI
                    '#d97757', // Anthropic
                    '#4285f4', // Gemini
                    '#a855f7'  // Local
                ],
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '75%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 20,
                        font: { size: 12 }
                    }
                }
            }
        }
    });

    state.chartsInitialized = true;
}

function switchTab(tabId) {
    // Update active button
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabId);
    });

    // Update active panel
    document.querySelectorAll('.panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === `panel-${tabId}`);
    });

    state.currentTab = tabId;
    
    if (tabId === 'overview') {
        // Initialize charts if not already done, requires slight delay for canvas rendering
        setTimeout(initCharts, 50);
    } else {
        // Only load if it's one of the API-backed tabs
        const resourceMap = {
            'quotas': 'quotas',
            'keys': 'key_pools',
            'clientkeys': 'client_keys',
            'virtualmodels': 'virtual_models',
            'conditional': 'conditional_routes',
            'aliases': 'aliases',
            'ratelimits': 'rate_limits',
            'payloads': 'payload_rules',
            'copilot': 'copilot_settings'
        };
        
        if (resourceMap[tabId]) {
            loadResource(resourceMap[tabId]);
        } else if (tabId === 'launcher') {
            loadLauncherProfiles();
        } else if (tabId === 'livelogs') {
            fetchLiveLogs();
        }
    }
}

// Launcher specific logic
async function loadLauncherProfiles() {
    if (!state.token) return;
    
    try {
        const response = await fetch('/api/agents/profiles', { headers: getHeaders() });
        const json = await response.json();
        
        if (json.ok && json.profiles) {
            const container = document.getElementById('launcher-profiles');
            container.innerHTML = '';
            
            for (const [id, profile] of Object.entries(json.profiles)) {
                const card = document.createElement('div');
                card.className = 'glass-panel';
                card.style.padding = '16px';
                card.style.borderRadius = '8px';
                card.innerHTML = `
                    <h3 style="margin: 0 0 8px 0; color: #fff;">${profile.name}</h3>
                    <p style="margin: 0 0 16px 0; font-size: 0.85rem; color: #9ca3af;">Command: <code>${profile.command.join(' ')}</code></p>
                    <button class="btn btn-primary" onclick="launchAgent('${id}')" style="width: 100%;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"></path></svg>
                        Launch Agent
                    </button>
                `;
                container.appendChild(card);
            }
        }
    } catch (err) {
        showToast(`Error loading profiles: ${err.message}`, "error");
    }
}

async function launchAgent(profileId) {
    const clientKey = document.getElementById('launcher-client-key').value || 'sk-sai-default';
    try {
        showToast(`Spawning ${profileId}...`, "success");
        const response = await fetch('/api/agents/launch', {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ profile_id: profileId, client_key: clientKey })
        });
        
        const json = await response.json();
        if (json.ok) {
            showToast(`Successfully launched! Session ID: ${json.session_id}`, "success");
        } else {
            showToast(`Launch failed: ${json.error}`, "error");
        }
    } catch (err) {
        showToast(`Launch error: ${err.message}`, "error");
    }
}

// API Interaction
function getHeaders() {
    return {
        'Content-Type': 'application/json',
        'x-superai-management-token': state.token
    };
}

async function loadResource(resourceName) {
    if (!state.token) return; // Don't try without a token
    
    // Map tab IDs to resource names if needed
    const apiName = resourceName === 'quotas' ? 'quotas' :
                   resourceName === 'keys' ? 'key_pools' :
                   resourceName === 'clientkeys' ? 'client_keys' :
                   resourceName === 'virtualmodels' ? 'virtual_models' :
                   resourceName === 'conditional' ? 'conditional_routes' :
                   resourceName === 'aliases' ? 'aliases' :
                   resourceName === 'ratelimits' ? 'rate_limits' :
                   resourceName === 'payloads' ? 'payload_rules' : resourceName;

    const textareaId = `${resourceName === apiName ? resourceName : (
        apiName === 'key_pools' ? 'keys' : 
        apiName === 'client_keys' ? 'clientkeys' : 
        apiName === 'virtual_models' ? 'virtualmodels' : 
        apiName === 'conditional_routes' ? 'conditional' : 
        apiName === 'rate_limits' ? 'ratelimits' : 
        apiName === 'payload_rules' ? 'payloads' : apiName
    )}-json`;
    
    const textarea = document.getElementById(textareaId);
    if (!textarea) return;

    try {
        textarea.value = "Loading...";
        const response = await fetch(`/api/${apiName}`, { headers: getHeaders() });
        
        if (response.status === 401) {
            textarea.value = "Unauthorized. Please check your Management Token.";
            return;
        }
        
        const json = await response.json();
        if (json.ok) {
            textarea.value = JSON.stringify(json.data, null, 4);
        } else {
            textarea.value = `Error loading: ${json.error}`;
        }
    } catch (err) {
        textarea.value = `Connection error: ${err.message}`;
    }
}

async function saveResource(resourceName) {
    // Map back to UI ID
    const uiId = resourceName === 'key_pools' ? 'keys' : 
                 resourceName === 'client_keys' ? 'clientkeys' : 
                 resourceName === 'virtual_models' ? 'virtualmodels' : 
                 resourceName === 'conditional_routes' ? 'conditional' : 
                 resourceName === 'rate_limits' ? 'ratelimits' : 
                 resourceName === 'payload_rules' ? 'payloads' : resourceName;
                 
    const textarea = document.getElementById(`${uiId}-json`);
    if (!textarea) return;

    let payload;
    try {
        payload = JSON.parse(textarea.value);
    } catch (e) {
        showToast("Invalid JSON format. Please correct it before saving.", "error");
        return;
    }

    try {
        const response = await fetch(`/api/${resourceName}`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ data: payload })
        });
        
        if (response.status === 401) {
            showToast("Unauthorized! Invalid Management Token.", "error");
            return;
        }

        const json = await response.json();
        if (json.ok) {
            showToast("Saved successfully!");
        } else {
            showToast(`Error saving: ${json.error}`, "error");
        }
    } catch (err) {
        showToast(`Connection error: ${err.message}`, "error");
    }
}

// Toast Notifications
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    toast.textContent = message;
    
    container.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// -----------------------------------------
// Live Logs, OAuth, and Auth Files Logic
// -----------------------------------------

async function fetchLiveLogs() {
    if (!state.token) return;
    try {
        const response = await fetch('/api/logs/tail?lines=100', { headers: getHeaders() });
        const json = await response.json();
        const contentArea = document.getElementById('livelogs-content');
        if (json.ok) {
            contentArea.textContent = json.lines.join('\n') || "No logs available.";
            contentArea.scrollTop = contentArea.scrollHeight;
        } else {
            contentArea.textContent = "Error loading logs: " + (json.detail || "Unknown error");
        }
    } catch (err) {
        document.getElementById('livelogs-content').textContent = "Connection error: " + err.message;
    }
}

let oauthPollInterval = null;
async function startOAuthFlow() {
    if (!state.token) return;
    const provider = document.getElementById('oauth-provider').value;
    const statusDiv = document.getElementById('oauth-status');
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = `<span style="color:#a5d6ff">Starting device flow for ${provider}...</span>`;
    
    try {
        const response = await fetch('/api/oauth/start', {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ provider })
        });
        const json = await response.json();
        if (json.ok) {
            const data = json.data;
            statusDiv.innerHTML = `
                <div style="color: #fff; margin-bottom: 8px;">Please go to: <strong><a href="${data.verification_uri}" target="_blank" style="color: #58a6ff;">${data.verification_uri}</a></strong></div>
                <div style="color: #fff; margin-bottom: 8px;">Enter code: <strong style="font-size: 1.2rem; background: #000; padding: 2px 6px; border-radius: 4px;">${data.user_code}</strong></div>
                <div style="color: #8b949e;">Waiting for authorization...</div>
            `;
            if (oauthPollInterval) clearInterval(oauthPollInterval);
            oauthPollInterval = setInterval(() => pollOAuthFlow(data.device_code), 5000);
        } else {
            statusDiv.innerHTML = `<span style="color:#f85149">Error: ${json.detail || "Failed to start flow"}</span>`;
        }
    } catch (err) {
        statusDiv.innerHTML = `<span style="color:#f85149">Connection error: ${err.message}</span>`;
    }
}

async function pollOAuthFlow(deviceCode) {
    if (!state.token) return;
    try {
        const response = await fetch(`/api/oauth/poll?device_code=${deviceCode}`, { headers: getHeaders() });
        const json = await response.json();
        if (json.ok && json.data.status !== 'pending') {
            const statusDiv = document.getElementById('oauth-status');
            statusDiv.innerHTML = `<span style="color:#3fb950">Authorization successful! Flow complete.</span>`;
            if (oauthPollInterval) clearInterval(oauthPollInterval);
        }
    } catch (err) {
        // silently ignore poll errors
    }
}

async function uploadAuthFile() {
    if (!state.token) return;
    const name = document.getElementById('authfile-name').value;
    let content;
    try {
        content = JSON.parse(document.getElementById('authfile-content').value);
    } catch (err) {
        showToast("Invalid JSON in Auth File content", "error");
        return;
    }
    
    try {
        showToast("Uploading credential...", "success");
        const response = await fetch('/api/credentials/upload', {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ name: name, data: content })
        });
        const json = await response.json();
        if (json.ok) {
            showToast("Credential uploaded successfully!", "success");
            document.getElementById('authfile-name').value = '';
            document.getElementById('authfile-content').value = '';
        } else {
            showToast("Upload failed: " + (json.detail || "Error"), "error");
        }
    } catch (err) {
        showToast("Connection error: " + err.message, "error");
    }
}
