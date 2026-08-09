// UI State
const state = {
    currentTab: 'quotas',
    token: localStorage.getItem('mgmt_token') || ''
};

// Initialize UI
document.addEventListener('DOMContentLoaded', () => {
    const tokenInput = document.getElementById('mgmt-token');
    if (state.token) tokenInput.value = state.token;

    tokenInput.addEventListener('change', (e) => {
        state.token = e.target.value;
        localStorage.setItem('mgmt_token', state.token);
        loadResource(state.currentTab);
    });

    // Setup tabs
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            switchTab(tabId);
        });
    });

    // Load initial tab
    loadResource(state.currentTab);
});

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
