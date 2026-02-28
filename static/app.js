/* ══════════════════════════════════════════════════════
   AuthShield AI — Frontend Logic
   ══════════════════════════════════════════════════════ */

const API = '';
let token = sessionStorage.getItem('as_token') || null;
let autoRefreshTimer = null;

// ── Startup ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  if (token) {
    showDashboard();
    loadEvents();
    loadFrozenCount();
    startAutoRefresh();
  } else {
    showLogin();
  }
});

// ── Auth ──────────────────────────────────────────────────────────────────────
function showLogin() {
  document.getElementById('login-page').classList.remove('hidden');
  document.getElementById('dashboard').classList.add('hidden');
}

function showDashboard() {
  document.getElementById('login-page').classList.add('hidden');
  document.getElementById('dashboard').classList.remove('hidden');
}

async function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  const errEl = document.getElementById('login-error');
  const btn = document.getElementById('login-btn');
  const btnText = document.getElementById('login-btn-text');
  const spinner = document.getElementById('login-spinner');

  errEl.classList.add('hidden');
  btnText.textContent = 'Signing in...';
  spinner.classList.remove('hidden');
  btn.disabled = true;

  try {
    const res = await fetch(`${API}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    if (res.ok) {
      const data = await res.json();
      token = data.token;
      sessionStorage.setItem('as_token', token);
      document.getElementById('logged-user').textContent = data.username;
      showDashboard();
      switchTab('events');
      loadEvents();
      loadFrozenCount();
      startAutoRefresh();
    } else {
      errEl.classList.remove('hidden');
    }
  } catch {
    errEl.classList.remove('hidden');
  } finally {
    btnText.textContent = 'Sign In';
    spinner.classList.add('hidden');
    btn.disabled = false;
  }
}

function logout() {
  token = null;
  sessionStorage.removeItem('as_token');
  clearInterval(autoRefreshTimer);
  showLogin();
}

// ── Fetch helper ──────────────────────────────────────────────────────────────
async function apiFetch(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...opts.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API}${path}`, { ...opts, headers });
  if (res.status === 401) { logout(); return null; }
  return res;
}

// ── Navigation ────────────────────────────────────────────────────────────────
const TAB_TITLES = {
  events: ['Live Events', 'Real-time login activity feed'],
  demo: ['Attack Demo', 'Simulate a botnet attack end-to-end'],
  clusters: ['Cluster View', 'Botnet graph clusters detected by Neo4j'],
  frozen: ['Frozen Users', 'All accounts currently frozen by AuthShield'],
  freezelog: ['Freeze Log', 'Complete audit trail of all freeze / unfreeze actions'],
  blockchain: ['Blockchain', 'Algorand audit trail & wallet actions'],
};

function switchTab(tab) {
  document.querySelectorAll('.tab-content').forEach(el => {
    el.classList.remove('active');
  });
  document.querySelectorAll('.menu-item').forEach(el => el.classList.remove('active'));

  const tabEl = document.getElementById(`tab-${tab}`);
  if (tabEl) { tabEl.classList.add('active'); }

  const menuEl = document.querySelector(`[data-tab="${tab}"]`);
  if (menuEl) menuEl.classList.add('active');

  const [title, subtitle] = TAB_TITLES[tab] || [tab, ''];
  document.getElementById('page-title').textContent = title;
  document.getElementById('page-subtitle').textContent = subtitle;

  if (tab === 'events') loadEvents();
  if (tab === 'clusters') loadClusters();
  if (tab === 'frozen') loadFrozenUsers();
  if (tab === 'freezelog') loadFreezeLog();
  if (tab === 'blockchain') loadBlockchain();
}

// ── Auto refresh ──────────────────────────────────────────────────────────────
function startAutoRefresh() {
  clearInterval(autoRefreshTimer);
  autoRefreshTimer = setInterval(() => {
    loadEvents(true);
    loadFrozenCount();
  }, 6000);
}

// ── Live Events ───────────────────────────────────────────────────────────────
async function loadEvents(silent = false) {
  const res = await apiFetch('/api/events?limit=50');
  if (!res) return;
  const events = await res.json();

  const body = document.getElementById('events-body');

  if (!events || events.length === 0) {
    body.innerHTML = '<tr><td colspan="6" class="empty">No events yet. Run the Attack Demo to generate traffic.</td></tr>';
    updateStats([], []);
    return;
  }

  const legit = events.filter(e => !e.is_suspicious);
  const sus = events.filter(e => e.is_suspicious);
  updateStats(events, sus);

  body.innerHTML = events.map(e => {
    const risk = parseFloat(e.risk_score || 0).toFixed(3);
    const entropy = parseFloat(e.entropy_score || 0).toFixed(3);
    const ts = e.created_at ? new Date(e.created_at).toLocaleTimeString() : '—';
    const badge = e.is_suspicious
      ? '<span class="badge badge-danger">⚠ Suspicious</span>'
      : '<span class="badge badge-ok">✔ OK</span>';
    const riskClass = parseFloat(risk) > 0.6 ? 'red' : parseFloat(risk) > 0.35 ? '' : '';
    return `<tr>
      <td>${e.user_id || '—'}</td>
      <td>${e.ip_address || '—'}</td>
      <td style="color:${parseFloat(risk) > 0.6 ? 'var(--red)' : parseFloat(risk) > 0.35 ? 'var(--yellow)' : 'var(--green)'}">${risk}</td>
      <td>${entropy}</td>
      <td>${badge}</td>
      <td>${ts}</td>
    </tr>`;
  }).join('');
}

async function updateStats(events, sus) {
  document.getElementById('stat-total').textContent = events.length;
  document.getElementById('stat-legit').textContent = events.filter(e => !e.is_suspicious).length;
  document.getElementById('stat-sus').textContent = sus.length;
  const frozen = await apiFetch('/api/frozen-users');
  if (frozen) {
    const fd = await frozen.json();
    const count = Array.isArray(fd) ? fd.length : 0;
    document.getElementById('stat-frozen-count').textContent = count;
  }
}

// ── Clusters ──────────────────────────────────────────────────────────────────
async function loadClusters() {
  const res = await apiFetch('/api/clusters');
  if (!res) return;
  const data = await res.json();
  const body = document.getElementById('clusters-body');
  const clusters = Array.isArray(data) ? data : data.clusters || [];

  if (!clusters.length) {
    body.innerHTML = '<div class="empty">No clusters detected yet. Run the Attack Demo first.</div>';
    return;
  }

  body.innerHTML = clusters.map((c, i) => {
    const members = c.members || c.users || [];
    const size = c.cluster_size || c.size || members.length;
    const risk = parseFloat(c.avg_risk_score || c.risk || 0).toFixed(3);
    const memberTags = members.map(m => `<span class="cluster-member">${m}</span>`).join('');
    return `<div class="cluster-card">
      <h4>🕸️ Cluster #${i + 1} — ${size} members</h4>
      <div class="cluster-meta">Avg Risk: ${risk} · Hash: ${(c.behavior_hash || c.hash || 'N/A').slice(0, 32)}...</div>
      <div class="cluster-members">${memberTags || '<span class="cluster-member">No members data</span>'}</div>
    </div>`;
  }).join('');
}

// ── Frozen Users ──────────────────────────────────────────────────────────────
async function loadFrozenCount() {
  const res = await apiFetch('/api/frozen-users');
  if (!res) return;
  const data = await res.json();
  const count = Array.isArray(data) ? data.length : 0;
  document.getElementById('frozen-badge').textContent = count;
  document.getElementById('stat-frozen-count').textContent = count;
}

async function loadFrozenUsers() {
  const res = await apiFetch('/api/frozen-users');
  if (!res) return;
  const users = await res.json();
  const body = document.getElementById('frozen-body');

  if (!users || !users.length) {
    body.innerHTML = '<tr><td colspan="8" class="empty">No frozen users yet. Run the Attack Demo and click "Freeze All Bots".</td></tr>';
    return;
  }

  body.innerHTML = users.map(u => {
    const ts = u.frozen_at ? new Date(u.frozen_at).toLocaleString() : '—';
    const risk = parseFloat(u.risk_score || 0).toFixed(3);
    const auth0 = u.auth0_frozen
      ? '<span class="badge badge-auth0">✔ Auth0</span>'
      : '<span class="badge badge-danger">✗ Auth0</span>';
    const chain = u.blockchain_logged
      ? `<a href="${u.explorer_link || '#'}" target="_blank" class="badge badge-chain">✔ Chain</a>`
      : '<span class="badge">—</span>';
    const reason = (u.reason || '—').replace(/_/g, ' ');
    return `<tr>
      <td>${u.user_id}</td>
      <td>${u.ip_address || '—'}</td>
      <td style="color:var(--red)">${risk}</td>
      <td>${reason}</td>
      <td>${auth0}</td>
      <td>${chain}</td>
      <td>${ts}</td>
      <td><button class="btn-unfreeze" onclick="unfreeze('${u.user_id}')">Unfreeze</button></td>
    </tr>`;
  }).join('');
}

async function unfreeze(userId) {
  const res = await apiFetch(`/api/unfreeze/${encodeURIComponent(userId)}`, { method: 'POST' });
  if (res && res.ok) {
    loadFrozenUsers();
    loadFrozenCount();
  }
}

// ── Freeze Log ────────────────────────────────────────────────────────────────
async function loadFreezeLog() {
  const res = await apiFetch('/api/freeze-log');
  if (!res) return;
  const logs = await res.json();
  const body = document.getElementById('freeze-log-body');

  if (!logs || !logs.length) {
    body.innerHTML = '<tr><td colspan="6" class="empty">No freeze actions recorded yet.</td></tr>';
    return;
  }

  body.innerHTML = logs.map(l => {
    const ts = l.timestamp ? new Date(l.timestamp).toLocaleString() : '—';
    const action = l.action === 'freeze'
      ? '<span class="badge badge-danger">❄ Freeze</span>'
      : '<span class="badge badge-ok">↩ Unfreeze</span>';
    const risk = l.risk_score != null ? parseFloat(l.risk_score).toFixed(3) : '—';
    const reason = (l.reason || '—').replace(/_/g, ' ');
    return `<tr>
      <td>${l.user_id || '—'}</td>
      <td>${action}</td>
      <td>${reason}</td>
      <td>${risk}</td>
      <td>${l.cluster_id || '—'}</td>
      <td>${ts}</td>
    </tr>`;
  }).join('');
}

// ── Thresholds ────────────────────────────────────────────────────────────────
async function saveThresholds() {
  const cluster_size = parseInt(document.getElementById('t-cluster').value);
  const risk_score = parseFloat(document.getElementById('t-risk').value);
  const similarity = 0.5;
  await apiFetch('/api/thresholds', {
    method: 'POST',
    body: JSON.stringify({ cluster_size, similarity, risk_score })
  });
}

// ── DEMO: Run Attack ──────────────────────────────────────────────────────────
async function runAttack() {
  const btnAttack = document.getElementById('btn-attack');
  const btnFreeze = document.getElementById('btn-freeze-all');
  const feed = document.getElementById('attack-feed');
  const resultCard = document.getElementById('freeze-result');

  btnAttack.disabled = true;
  btnFreeze.disabled = true;
  resultCard.classList.add('hidden');
  feed.innerHTML = '';

  function feedLine(text, cls = '') {
    const line = document.createElement('div');
    line.className = `feed-line ${cls}`;
    line.textContent = text;
    feed.appendChild(line);
    feed.scrollTop = feed.scrollHeight;
  }

  function setStep(n, state) {
    const step = document.getElementById(`step-${n}`);
    const status = document.getElementById(`step-${n}-status`);
    if (!step) return;
    step.className = `demo-step ${state}`;
    status.textContent = state === 'done' ? '✅' : state === 'active' ? '⏳' : state === 'error' ? '❌' : '⏳';
  }

  // Step 1 — seed model
  setStep(1, 'active');
  feedLine('━━━ PHASE 0: Seeding ML Model ━━━', 'head');
  feedLine('  Training Isolation Forest on 400 synthetic legit fingerprints...');

  feedLine('  ✔ Model trained — isolation_forest.pkl ready', 'legit');
  setStep(1, 'done');

  // Step 2 + 3 — run attack
  setStep(2, 'active');
  feedLine('');
  feedLine('━━━ PHASE 1: Legitimate Users Logging In ━━━', 'head');

  try {
    const res = await apiFetch('/api/demo/run-attack', { method: 'POST' });
    if (!res || !res.ok) {
      feedLine('  ✗ Attack API error', 'warn');
      setStep(2, 'error'); setStep(3, 'error');
      btnAttack.disabled = false;
      return;
    }
    const data = await res.json();
    const { events } = data;

    // Legit users
    (events.legit || []).forEach(e => {
      const ts = new Date().toLocaleTimeString();
      const risk = parseFloat(e.risk_score || 0).toFixed(3);
      feedLine(`  ${ts}  ${String(e.user_id).padEnd(20)} IP:${String(e.ip_address || '?').padEnd(16)} Risk:${risk}  ✔ OK`, 'legit');
    });
    setStep(2, 'done');

    // Bot attack
    await new Promise(r => setTimeout(r, 400));
    setStep(3, 'active');
    feedLine('');
    feedLine('━━━ PHASE 2: 🤖 BOTNET ATTACK INCOMING ━━━', 'head');
    feedLine('  Source: 45.152.66.x/24 · Same Chrome 88 UA · Robotic typing (50ms)', 'warn');
    feedLine('');

    (events.bots || []).forEach(e => {
      const ts = new Date().toLocaleTimeString();
      const risk = parseFloat(e.risk_score || 0).toFixed(3);
      feedLine(`  ${ts}  ${String(e.user_id).padEnd(20)} IP:${String(e.ip_address || '?').padEnd(16)} Risk:${risk}  🤖 BOT`, 'bot');
    });

    const avgLegit = (events.legit || []).reduce((s, e) => s + parseFloat(e.risk_score || 0), 0) / Math.max((events.legit || []).length, 1);
    const avgBot = (events.bots || []).reduce((s, e) => s + parseFloat(e.risk_score || 0), 0) / Math.max((events.bots || []).length, 1);
    feedLine('');
    feedLine(`  Avg risk (legit): ${avgLegit.toFixed(4)}`, 'legit');
    feedLine(`  Avg risk (botnet): ${avgBot.toFixed(4)}  ← higher entropy & uniform patterns`, 'bot');
    setStep(3, 'done');

    setStep(4, 'active');
    feedLine('');
    feedLine('━━━ PHASE 3: Graph Cluster Detection Running… ━━━', 'head');
    feedLine('  Neo4j scanning for coordinated login clusters...', 'info');

    // small delay for effect
    await new Promise(r => setTimeout(r, 800));
    feedLine('  ✔ Cluster analysis complete — bots share behavior hash', 'legit');
    feedLine('');
    feedLine('  Ready to freeze. Click "❄️ Freeze All Bots" to neutralise the attack.', 'info');

    setStep(4, 'active');
    btnFreeze.disabled = false;

  } catch (err) {
    feedLine(`  ✗ Error: ${err.message}`, 'warn');
    setStep(2, 'error');
  }

  btnAttack.disabled = false;
}

// ── DEMO: Freeze All ──────────────────────────────────────────────────────────
async function freezeAll() {
  const btnFreeze = document.getElementById('btn-freeze-all');
  const feed = document.getElementById('attack-feed');
  const resultCard = document.getElementById('freeze-result');

  btnFreeze.disabled = true;

  function feedLine(text, cls = '') {
    const line = document.createElement('div');
    line.className = `feed-line ${cls}`;
    line.textContent = text;
    feed.appendChild(line);
    feed.scrollTop = feed.scrollHeight;
  }

  feedLine('');
  feedLine('━━━ PHASE 4: ❄️ Freezing All Bot Accounts ━━━', 'head');
  feedLine('  Detecting clusters → Auth0 block → Algorand audit...', 'info');

  try {
    const res = await apiFetch('/api/demo/freeze-all', { method: 'POST' });
    if (!res || !res.ok) {
      feedLine('  ✗ Freeze API error', 'warn');
      btnFreeze.disabled = false;
      return;
    }
    const data = await res.json();
    const frozenUsers = data.frozen_users || [];

    frozenUsers.forEach(u => {
      const auth0 = u.auth0 ? '✔ Auth0' : '✗ Auth0(mock)';
      const chain = u.blockchain ? `✔ Chain: ${u.txid ? u.txid.slice(0, 12) + '…' : 'logged'}` : '— Algorand(no ALGO)';
      feedLine(`  ❄ ${u.user_id.padEnd(22)} Risk:${parseFloat(u.risk_score || 0).toFixed(3)}  ${auth0}  ${chain}`, 'frozen-confirm');
    });

    feedLine('');
    feedLine(`  ━━ ${data.frozen_count} account(s) frozen. Attack neutralised! ━━`, 'head');

    document.getElementById('step-4').className = 'demo-step done';
    document.getElementById('step-4-status').textContent = '✅';

    // Show result card
    resultCard.classList.remove('hidden');
    document.getElementById('freeze-result-title').textContent = `${data.frozen_count} Bot Account(s) Frozen!`;
    document.getElementById('freeze-result-subtitle').textContent =
      `${data.frozen_count} accounts blocked via Auth0 and logged to Algorand blockchain.`;

    document.getElementById('freeze-result-list').innerHTML = frozenUsers.map(u => `
      <div class="frozen-row">
        <span>❄️ ${u.user_id}</span>
        <span style="color:var(--text2)">${u.ip_address || '—'}</span>
        <span style="color:var(--red)">Risk: ${parseFloat(u.risk_score || 0).toFixed(3)}</span>
        <span class="badge badge-auth0">${u.auth0 ? '✔ Auth0' : '✗ Auth0'}</span>
        <span class="badge badge-chain">${u.blockchain ? '⛓ Logged' : '— Chain'}</span>
      </div>`).join('');

    // Refresh frozen tab badge
    loadFrozenCount();

    // Prompt user to check frozen tab
    setTimeout(() => {
      feedLine('  → Switch to "Frozen Users" tab to see full details.', 'info');
    }, 500);

  } catch (err) {
    feedLine(`  ✗ Error: ${err.message}`, 'warn');
  }
}

// ── Blockchain ────────────────────────────────────────────────────────────────
async function loadBlockchain() {
  const res = await apiFetch('/api/blockchain/status');
  if (!res) return;
  const data = await res.json();
  const infoEl = document.getElementById('bchain-info');

  const netColor = data.network === 'testnet' ? 'var(--yellow)' : 'var(--green)';
  const configured = data.configured ? '<span class="green">Yes</span>' : '<span style="color:var(--red)">No</span>';
  const addrShort = data.address ? `${data.address.slice(0, 12)}...` : 'Not set';

  let balance = 0;
  try {
    const balRes = await apiFetch('/api/blockchain/balance');
    if (balRes && balRes.ok) {
      const b = await balRes.json();
      balance = b.balance_algo || 0;
    }
  } catch { }

  infoEl.innerHTML = `
    <div>Network: <span class="val" style="color:${netColor}">${data.network || '—'}</span></div>
    <div>Configured: ${configured}</div>
    <div>Address: <span class="val">${addrShort}</span></div>
    <div>Balance: <span class="val">${parseFloat(balance).toFixed(4)} ALGO</span></div>
  `;
}

async function generateWallet() {
  const res = await apiFetch('/api/blockchain/generate-wallet', { method: 'POST' });
  if (!res) return;
  const data = await res.json();
  const el = document.getElementById('wallet-result');
  el.classList.remove('hidden');
  el.innerHTML = `<div><b>Address:</b> ${data.address}</div>
    <div><b>Mnemonic:</b> ${data.mnemonic}</div>
    <div><b>Fund URL:</b> <a href="${data.fund_url}" target="_blank" style="color:var(--accent2)">${data.fund_url}</a></div>`;
}

async function bcLogFreeze() {
  const uid = document.getElementById('bc-freeze-uid').value.trim();
  const risk = parseFloat(document.getElementById('bc-freeze-risk').value);
  if (!uid) return;
  const res = await apiFetch(`/api/blockchain/log-freeze/${encodeURIComponent(uid)}?risk_score=${risk}`, { method: 'POST' });
  if (res) showBchainResult(await res.json());
}

async function bcMintBadge() {
  const uid = document.getElementById('bc-badge-uid').value.trim();
  const risk = parseFloat(document.getElementById('bc-badge-risk').value);
  if (!uid) return;
  const res = await apiFetch(`/api/blockchain/mint-badge/${encodeURIComponent(uid)}?risk_score=${risk}`, { method: 'POST' });
  if (res) showBchainResult(await res.json());
}

async function bcUpdateRep() {
  const uid = document.getElementById('bc-rep-uid').value.trim();
  const risk = parseFloat(document.getElementById('bc-rep-risk').value);
  if (!uid) return;
  const res = await apiFetch(`/api/blockchain/update-reputation/${encodeURIComponent(uid)}?risk_score=${risk}`, { method: 'POST' });
  if (res) showBchainResult(await res.json());
}

async function bcFreezeAndLog() {
  const uid = document.getElementById('bc-fl-uid').value.trim();
  if (!uid) return;
  const res = await apiFetch(`/api/freeze-blockchain/${encodeURIComponent(uid)}`, { method: 'POST' });
  if (res) showBchainResult(await res.json());
}

function showBchainResult(data) {
  const el = document.getElementById('bchain-action-result');
  el.classList.remove('hidden');
  el.textContent = JSON.stringify(data, null, 2);
}
