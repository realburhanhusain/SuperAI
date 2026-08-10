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
            'aliases': 'aliases',
            'ratelimits': 'rate_limits',
            'payloads': 'payload_rules'
        };
        
        if (resourceMap[tabId]) {
            loadResource(resourceMap[tabId]);
        }
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
                   resourceName === 'aliases' ? 'aliases' :
                   resourceName === 'ratelimits' ? 'rate_limits' :
                   resourceName === 'payloads' ? 'payload_rules' : resourceName;

    const textareaId = `${resourceName === apiName ? resourceName : (
        apiName === 'key_pools' ? 'keys' : 
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
    
    toast.innerHTML = `
        <span>${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        if (toast.parentElement) toast.remove();
    }, 4000);
}
