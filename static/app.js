const API_BASE = '';

async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: { 'Content-Type': 'application/json' },
            ...options
        });
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return { error: error.message };
    }
}

function updateConnectionStatus(connected) {
    const status = document.getElementById('connection-status');
    if (connected) {
        status.textContent = 'Connected';
        status.className = 'status connected';
    } else {
        status.textContent = 'Disconnected';
        status.className = 'status error';
    }
}

function formatTime(timestamp) {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    return date.toLocaleString();
}

function getRiskClass(score) {
    if (score >= 0.7) return 'risk-high';
    if (score >= 0.4) return 'risk-medium';
    return 'risk-low';
}

document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        tab.classList.add('active');
        document.getElementById(tab.dataset.tab).classList.add('active');
    });
});

async function loadEvents() {
    const events = await fetchAPI('/api/events');
    const tbody = document.querySelector('#events-table tbody');
    tbody.innerHTML = '';
    
    if (!events.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No events yet</td></tr>';
        return;
    }
    
    events.forEach(event => {
        const row = document.createElement('tr');
        const riskClass = getRiskClass(event.risk_score);
        const status = event.is_suspicious ? 
            '<span class="status-flagged">Flagged</span>' : 
            '<span class="status-ok">OK</span>';
        
        row.innerHTML = `
            <td>${event.user_id || '-'}</td>
            <td>${event.ip_address || '-'}</td>
            <td class="${riskClass}">${(event.risk_score || 0).toFixed(3)}</td>
            <td>${(event.entropy_score || 0).toFixed(3)}</td>
            <td>${status}</td>
            <td>${formatTime(event.created_at)}</td>
        `;
        tbody.appendChild(row);
    });
    
    updateConnectionStatus(true);
}

async function loadClusters() {
    const clusters = await fetchAPI('/api/clusters');
    const container = document.getElementById('clusters-container');
    container.innerHTML = '';
    
    if (!clusters.length || clusters.error) {
        container.innerHTML = '<div class="empty-state">No clusters detected or Neo4j not connected</div>';
        return;
    }
    
    clusters.forEach(cluster => {
        const card = document.createElement('div');
        card.className = 'cluster-card';
        
        const members = cluster.members || [];
        const memberBadges = members.map(m => 
            `<span class="member-badge">${m}</span>`
        ).join('');
        
        card.innerHTML = `
            <h3>Cluster (${cluster.size} members)</h3>
            <p style="font-size: 12px; color: #64748b; margin-bottom: 10px;">
                Hash: ${cluster.behavior_hash?.substring(0, 16)}...
            </p>
            <div class="cluster-members">${memberBadges}</div>
        `;
        container.appendChild(card);
    });
}

async function loadFlagged() {
    const flagged = await fetchAPI('/api/flagged');
    const tbody = document.querySelector('#flagged-table tbody');
    tbody.innerHTML = '';
    
    if (!flagged.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No flagged users</td></tr>';
        return;
    }
    
    flagged.forEach(user => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${user.user_id || '-'}</td>
            <td class="${getRiskClass(user.risk_score)}">${(user.risk_score || 0).toFixed(3)}</td>
            <td>${(user.entropy_score || 0).toFixed(3)}</td>
            <td>
                <button onclick="freezeUser('${user.user_id}')" class="danger">Freeze</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

async function loadFreezeLog() {
    const logs = await fetchAPI('/api/freeze-log');
    const tbody = document.querySelector('#freeze-log-table tbody');
    tbody.innerHTML = '';
    
    if (!logs.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No freeze actions yet</td></tr>';
        return;
    }
    
    logs.forEach(log => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${log.user_id || '-'}</td>
            <td>${log.action || '-'}</td>
            <td>${log.reason || '-'}</td>
            <td>${(log.risk_score || 0).toFixed(3)}</td>
            <td>${formatTime(log.timestamp)}</td>
        `;
        tbody.appendChild(row);
    });
}

async function loadThresholds() {
    const thresholds = await fetchAPI('/api/thresholds');
    document.getElementById('threshold-cluster').value = thresholds.cluster_size;
    document.getElementById('threshold-similarity').value = thresholds.similarity;
    document.getElementById('threshold-risk').value = thresholds.risk_score;
}

document.getElementById('save-thresholds').addEventListener('click', async () => {
    const thresholds = {
        cluster_size: parseInt(document.getElementById('threshold-cluster').value),
        similarity: parseFloat(document.getElementById('threshold-similarity').value),
        risk_score: parseFloat(document.getElementById('threshold-risk').value)
    };
    
    const result = await fetchAPI('/api/thresholds', {
        method: 'POST',
        body: JSON.stringify(thresholds)
    });
    
    alert(result.success ? 'Thresholds saved!' : 'Error saving thresholds');
});

document.getElementById('check-clusters').addEventListener('click', async () => {
    if (!confirm('This will check all clusters and auto-freeze flagged users. Continue?')) return;
    
    const result = await fetchAPI('/api/check-clusters', { method: 'POST' });
    alert(`Frozen ${result.frozen_count || 0} users. Flagged: ${result.flagged_count || 0}`);
    loadFlagged();
    loadFreezeLog();
});

document.getElementById('refresh-events').addEventListener('click', loadEvents);
document.getElementById('refresh-clusters').addEventListener('click', loadClusters);
document.getElementById('refresh-flagged').addEventListener('click', loadFlagged);
document.getElementById('refresh-freeze-log').addEventListener('click', loadFreezeLog);

document.getElementById('simulate-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const typingStr = document.getElementById('sim-typing').value;
    const typingArray = typingStr ? typingStr.split(',').map(n => parseFloat(n.trim())) : [];
    
    const payload = {
        user_id: document.getElementById('sim-user-id').value,
        ip_address: document.getElementById('sim-ip').value,
        user_agent: document.getElementById('sim-ua').value,
        screen_resolution: document.getElementById('sim-screen').value,
        timezone: document.getElementById('sim-tz').value,
        webgl_hash: document.getElementById('sim-webgl').value,
        canvas_hash: document.getElementById('sim-canvas').value,
        typing_latency_array: typingArray
    };
    
    const result = await fetchAPI('/api/simulate', {
        method: 'POST',
        body: JSON.stringify(payload)
    });
    
    document.getElementById('simulate-result').textContent = JSON.stringify(result, null, 2);
    loadEvents();
});

document.getElementById('btn-freeze').addEventListener('click', async () => {
    const userId = document.getElementById('action-user-id').value;
    if (!userId) return alert('Enter a user ID');
    
    const result = await fetchAPI(`/api/freeze/${userId}`, { method: 'POST' });
    document.getElementById('action-result').textContent = JSON.stringify(result, null, 2);
    loadFreezeLog();
});

document.getElementById('btn-unfreeze').addEventListener('click', async () => {
    const userId = document.getElementById('action-user-id').value;
    if (!userId) return alert('Enter a user ID');
    
    const result = await fetchAPI(`/api/unfreeze/${userId}`, { method: 'POST' });
    document.getElementById('action-result').textContent = JSON.stringify(result, null, 2);
    loadFreezeLog();
});

async function freezeUser(userId) {
    if (!confirm(`Freeze user ${userId}?`)) return;
    
    const result = await fetchAPI(`/api/freeze/${userId}`, { method: 'POST' });
    alert(result.success ? 'User frozen!' : 'Error: ' + result.error);
    loadFlagged();
    loadFreezeLog();
}

window.freezeUser = freezeUser;

async function init() {
    try {
        await fetchAPI('/api/health');
        updateConnectionStatus(true);
    } catch {
        updateConnectionStatus(false);
    }
    
    loadThresholds();
    loadEvents();
    loadClusters();
    loadFlagged();
    loadFreezeLog();
    loadBlockchainStatus();
}

init();

setInterval(loadEvents, 30000);

async function loadBlockchainStatus() {
    const status = await fetchAPI('/api/blockchain/status');
    document.getElementById('bc-network').textContent = status.network || '-';
    document.getElementById('bc-configured').textContent = status.configured ? 'Yes' : 'No';
    document.getElementById('bc-address').textContent = status.address ? 
        status.address.substring(0, 20) + '...' : '-';
    
    if (status.configured) {
        const balance = await fetchAPI('/api/blockchain/balance');
        document.getElementById('bc-balance').textContent = 
            (balance.balance_algo || 0).toFixed(4);
    }
}

document.getElementById('refresh-blockchain').addEventListener('click', loadBlockchainStatus);

document.getElementById('generate-wallet').addEventListener('click', async () => {
    const result = await fetchAPI('/api/blockchain/generate-wallet', { method: 'POST' });
    
    if (result.address) {
        document.getElementById('wallet-result').textContent = 
            `NEW WALLET GENERATED\n\n` +
            `Address: ${result.address}\n\n` +
            `Mnemonic (25 words):\n${result.mnemonic}\n\n` +
            `Fund URL: ${result.fund_url}\n\n` +
            `⚠️ SAVE THIS MNEMONIC SECURELY! ⚠️\n` +
            `Add to .env as ALGORAND_MNEMONIC`;
    } else {
        document.getElementById('wallet-result').textContent = JSON.stringify(result, null, 2);
    }
});

document.getElementById('bc-log-freeze').addEventListener('click', async () => {
    const userId = document.getElementById('bc-freeze-user').value;
    const riskScore = document.getElementById('bc-freeze-risk').value;
    
    if (!userId) return alert('Enter User ID');
    
    const result = await fetchAPI(
        `/api/blockchain/log-freeze/${userId}?risk_score=${riskScore}`,
        { method: 'POST' }
    );
    
    showBlockchainResult(result);
});

document.getElementById('bc-mint-badge').addEventListener('click', async () => {
    const userId = document.getElementById('bc-badge-user').value;
    const riskScore = parseFloat(document.getElementById('bc-badge-risk').value);
    
    if (!userId) return alert('Enter User ID');
    
    const result = await fetchAPI(
        `/api/blockchain/mint-badge/${userId}?risk_score=${riskScore}`,
        { method: 'POST' }
    );
    
    showBlockchainResult(result);
});

document.getElementById('bc-update-rep').addEventListener('click', async () => {
    const userId = document.getElementById('bc-rep-user').value;
    const riskScore = document.getElementById('bc-rep-risk').value;
    
    if (!userId) return alert('Enter User ID');
    
    const result = await fetchAPI(
        `/api/blockchain/update-reputation/${userId}?risk_score=${riskScore}`,
        { method: 'POST' }
    );
    
    showBlockchainResult(result);
});

document.getElementById('bc-full-freeze').addEventListener('click', async () => {
    const userId = document.getElementById('bc-full-freeze-user').value;
    
    if (!userId) return alert('Enter User ID');
    if (!confirm(`Freeze ${userId} on Auth0 AND log to blockchain?`)) return;
    
    const result = await fetchAPI(`/api/freeze-blockchain/${userId}`, { method: 'POST' });
    
    showBlockchainResult(result);
    loadFreezeLog();
});

function showBlockchainResult(result) {
    let output = JSON.stringify(result, null, 2);
    
    if (result.explorer_link) {
        output += `\n\n🔗 Explorer: ${result.explorer_link}`;
    }
    if (result.blockchain && result.blockchain.explorer_link) {
        output += `\n\n🔗 Blockchain TX: ${result.blockchain.explorer_link}`;
    }
    
    document.getElementById('blockchain-result').textContent = output;
}
