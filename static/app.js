/* ══════════════════════════════════════════════════════
   AuthShield AI — Frontend Logic v2
   Multi-user auth · Remember me · Team tab
   ══════════════════════════════════════════════════════ */

const API = '';

// ── Persistent state ──────────────────────────────────────────────────────────
let token = null;
let currentUser = null;
let selectedRole = 'analyst';
let autoRefreshTimer = null;

// Check localStorage first (remember-me), then sessionStorage
function loadToken() {
  return localStorage.getItem('as_token') || sessionStorage.getItem('as_token');
}
function saveToken(t, remember) {
  if (remember) {
    localStorage.setItem('as_token', t);
    sessionStorage.removeItem('as_token');
  } else {
    sessionStorage.setItem('as_token', t);
    localStorage.removeItem('as_token');
  }
  token = t;
}
function clearToken() {
  localStorage.removeItem('as_token');
  sessionStorage.removeItem('as_token');
  token = null;
  currentUser = null;
}

// ── Startup ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  token = loadToken();
  if (token) {
    // Validate token by fetching /api/me
    try {
      const res = await fetch(`${API}/api/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        currentUser = await res.json();
        showDashboard();
        applyUserProfile(currentUser);
        switchTab('events');
        loadFrozenCount();
        startAutoRefresh();
        return;
      }
    } catch { }
    clearToken();
  }
  showAuthPage();
});

// ── Auth page show/hide ───────────────────────────────────────────────────────
function showAuthPage() {
  document.getElementById('auth-page').classList.remove('hidden');
  document.getElementById('dashboard').classList.add('hidden');
}
function showDashboard() {
  document.getElementById('auth-page').classList.add('hidden');
  document.getElementById('dashboard').classList.remove('hidden');
}

function showAuthTab(tab) {
  ['login', 'signup'].forEach(t => {
    document.getElementById(`${t}-form`).classList.toggle('hidden', t !== tab);
    document.getElementById(`tab-${t}-btn`).classList.toggle('active', t === tab);
  });
  clearAuthErrors();
}

function clearAuthErrors() {
  ['login-error', 'signup-error', 'signup-success'].forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.classList.add('hidden'); el.textContent = ''; }
  });
}

// ── User profile helpers ──────────────────────────────────────────────────────
function applyUserProfile(user) {
  const initials = (user.full_name || user.username || '?')
    .split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
  const role = user.role || 'analyst';

  // Sidebar
  document.getElementById('sidebar-avatar').textContent = initials;
  document.getElementById('sidebar-name').textContent = user.full_name || user.username;
  document.getElementById('sidebar-role').textContent = role;

  // Topbar
  document.getElementById('topbar-avatar').textContent = initials;
  document.getElementById('logged-user').textContent = user.username;
  document.getElementById('topbar-role').textContent = role;
}

// ── LOGIN ─────────────────────────────────────────────────────────────────────
async function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  const remember_me = document.getElementById('login-remember').checked;
  const errEl = document.getElementById('login-error');
  const btn = document.getElementById('login-btn');
  const spinner = document.getElementById('login-spinner');
  const btnText = document.getElementById('login-btn-text');

  errEl.classList.add('hidden');
  btn.disabled = true;
  spinner.classList.remove('hidden');
  btnText.textContent = 'Signing in…';

  try {
    const res = await fetch(`${API}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, remember_me })
    });
    if (res.ok) {
      const data = await res.json();
      saveToken(data.token, remember_me);
      currentUser = data;
      showDashboard();
      applyUserProfile(data);
      switchTab('events');
      loadFrozenCount();
      startAutoRefresh();
    } else {
      const err = await res.json();
      errEl.textContent = `❌ ${err.detail || 'Invalid username or password'}`;
      errEl.classList.remove('hidden');
    }
  } catch {
    errEl.textContent = '❌ Network error. Is the server running?';
    errEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    spinner.classList.add('hidden');
    btnText.textContent = 'Sign In to Dashboard';
  }
}

// ── SIGN-UP ───────────────────────────────────────────────────────────────────
function selectRole(role) {
  selectedRole = role;
  document.querySelectorAll('.role-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.role === role);
  });
  const btnText = document.getElementById('signup-btn-text');
  const labels = { analyst: 'Create Analyst Account', viewer: 'Create Viewer Account', admin: 'Create Admin Account' };
  btnText.textContent = labels[role] || 'Create Account';
}

function checkStrength(pass) {
  const fill = document.getElementById('strength-fill');
  const label = document.getElementById('strength-label');
  if (!pass) { fill.style.width = '0%'; label.textContent = ''; return; }
  let score = 0;
  if (pass.length >= 8) score++;
  if (/[A-Z]/.test(pass)) score++;
  if (/[0-9]/.test(pass)) score++;
  if (/[^a-zA-Z0-9]/.test(pass)) score++;

  const levels = ['', 'Weak', 'Fair', 'Good', 'Strong'];
  const colors = ['', '#ef4444', '#f59e0b', '#10b981', '#3b82f6'];
  const widths = ['0%', '25%', '50%', '75%', '100%'];

  fill.style.width = widths[score];
  fill.style.background = colors[score];
  label.textContent = levels[score];
  label.style.color = colors[score];
}

async function handleSignup(e) {
  e.preventDefault();
  const full_name = document.getElementById('signup-name').value.trim();
  const username = document.getElementById('signup-username').value.trim();
  const email = document.getElementById('signup-email').value.trim();
  const password = document.getElementById('signup-password').value;
  const confirm = document.getElementById('signup-confirm').value;
  const errEl = document.getElementById('signup-error');
  const succEl = document.getElementById('signup-success');
  const btn = document.getElementById('signup-btn');
  const spinner = document.getElementById('signup-spinner');
  const btnText = document.getElementById('signup-btn-text');

  errEl.classList.add('hidden'); succEl.classList.add('hidden');

  // Client-side validation
  if (password !== confirm) {
    errEl.textContent = '❌ Passwords do not match';
    errEl.classList.remove('hidden'); return;
  }
  if (password.length < 6) {
    errEl.textContent = '❌ Password must be at least 6 characters';
    errEl.classList.remove('hidden'); return;
  }

  btn.disabled = true;
  spinner.classList.remove('hidden');
  btnText.textContent = 'Creating account…';

  try {
    const res = await fetch(`${API}/api/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ full_name, username, email, password, role: selectedRole })
    });
    const data = await res.json();

    if (res.ok) {
      saveToken(data.token, false);
      currentUser = data;
      succEl.textContent = `✅ Welcome, ${data.full_name || data.username}! Redirecting to dashboard…`;
      succEl.classList.remove('hidden');
      setTimeout(() => {
        showDashboard();
        applyUserProfile(data);
        switchTab('events');
        loadFrozenCount();
        startAutoRefresh();
      }, 1200);
    } else {
      errEl.textContent = `❌ ${data.detail || 'Registration failed'}`;
      errEl.classList.remove('hidden');
    }
  } catch {
    errEl.textContent = '❌ Network error. Is the server running?';
    errEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    spinner.classList.add('hidden');
    btnText.textContent = selectRole === 'admin' ? 'Create Admin Account' : 'Create Analyst Account';
  }
}

// ── Logout ────────────────────────────────────────────────────────────────────
function logout() {
  clearToken();
  clearInterval(autoRefreshTimer);
  showAuthPage();
  showAuthTab('login');
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
  team: ['Security Team', 'All registered analysts with dashboard access'],
  blockchain: ['Blockchain', 'Algorand audit trail & wallet actions'],
};

function switchTab(tab) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.menu-item').forEach(el => el.classList.remove('active'));
  const tabEl = document.getElementById(`tab-${tab}`);
  const menuEl = document.querySelector(`[data-tab="${tab}"]`);
  if (tabEl) tabEl.classList.add('active');
  if (menuEl) menuEl.classList.add('active');
  const [title, subtitle] = TAB_TITLES[tab] || [tab, ''];
  document.getElementById('page-title').textContent = title;
  document.getElementById('page-subtitle').textContent = subtitle;
  if (tab === 'events') loadEvents();
  if (tab === 'clusters') loadClusters();
  if (tab === 'frozen') loadFrozenUsers();
  if (tab === 'freezelog') loadFreezeLog();
  if (tab === 'team') loadTeam();
  if (tab === 'blockchain') loadBlockchain();
}

// ── Auto refresh ──────────────────────────────────────────────────────────────
function startAutoRefresh() {
  clearInterval(autoRefreshTimer);
  autoRefreshTimer = setInterval(() => { loadEvents(true); loadFrozenCount(); }, 8000);
}

// ── Live Events ───────────────────────────────────────────────────────────────
async function loadEvents(silent = false) {
  const res = await apiFetch('/api/events?limit=50');
  if (!res) return;
  const events = await res.json();
  const body = document.getElementById('events-body');
  if (!events || events.length === 0) {
    body.innerHTML = '<tr><td colspan="6" class="empty">No events yet. Run the Attack Demo to generate traffic.</td></tr>';
    updateStatCards([]);
    return;
  }
  updateStatCards(events);
  body.innerHTML = events.map(e => {
    const risk = parseFloat(e.risk_score || 0).toFixed(3);
    const entropy = parseFloat(e.entropy_score || 0).toFixed(3);
    const ts = e.created_at ? new Date(e.created_at).toLocaleTimeString() : '—';
    const badge = e.is_suspicious
      ? '<span class="badge badge-danger">⚠ Suspicious</span>'
      : '<span class="badge badge-ok">✔ OK</span>';
    const rColor = parseFloat(risk) > 0.6 ? 'var(--red)' : parseFloat(risk) > 0.35 ? 'var(--yellow)' : 'var(--green)';
    return `<tr>
      <td>${e.user_id || '—'}</td>
      <td>${e.ip_address || '—'}</td>
      <td style="color:${rColor}">${risk}</td>
      <td>${entropy}</td>
      <td>${badge}</td>
      <td>${ts}</td>
    </tr>`;
  }).join('');
}

async function updateStatCards(events) {
  document.getElementById('stat-total').textContent = events.length;
  document.getElementById('stat-legit').textContent = events.filter(e => !e.is_suspicious).length;
  document.getElementById('stat-sus').textContent = events.filter(e => e.is_suspicious).length;
  const frozen = await apiFetch('/api/frozen-users');
  if (frozen) {
    const fd = await frozen.json();
    const cnt = Array.isArray(fd) ? fd.length : 0;
    document.getElementById('stat-frozen-count').textContent = cnt;
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
    const members = c.members || [];
    const size = c.size || c.cluster_size || members.length;
    const hash = (c.behavior_hash || c.hash || '').slice(0, 40);
    return `<div class="cluster-card">
      <h4>🕸️ Cluster #${i + 1} — ${size} members</h4>
      <div class="cluster-meta">Hash: ${hash}…</div>
      <div class="cluster-members">${members.map(m => `<span class="cluster-member">${m}</span>`).join('')}</div>
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
    body.innerHTML = '<tr><td colspan="8" class="empty">No frozen users yet. Run Attack Demo then click Freeze All Bots.</td></tr>';
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
    return `<tr>
      <td>${u.user_id}</td>
      <td>${u.ip_address || '—'}</td>
      <td style="color:var(--red)">${risk}</td>
      <td>${(u.reason || '—').replace(/_/g, ' ')}</td>
      <td>${auth0}</td>
      <td>${chain}</td>
      <td>${ts}</td>
      <td><button class="btn-unfreeze" onclick="unfreeze('${u.user_id}')">Unfreeze</button></td>
    </tr>`;
  }).join('');
  document.getElementById('frozen-badge').textContent = users.length;
}

async function unfreeze(userId) {
  const res = await apiFetch(`/api/unfreeze/${encodeURIComponent(userId)}`, { method: 'POST' });
  if (res && res.ok) { loadFrozenUsers(); loadFrozenCount(); }
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
    return `<tr>
      <td>${l.user_id || '—'}</td>
      <td>${action}</td>
      <td>${(l.reason || '—').replace(/_/g, ' ')}</td>
      <td>${l.risk_score != null ? parseFloat(l.risk_score).toFixed(3) : '—'}</td>
      <td>${l.cluster_id || '—'}</td>
      <td>${ts}</td>
    </tr>`;
  }).join('');
}

// ── Team ──────────────────────────────────────────────────────────────────────
async function loadTeam() {
  const res = await apiFetch('/api/users');
  if (!res) return;
  const users = await res.json();
  const body = document.getElementById('team-body');
  if (!users || !users.length) {
    body.innerHTML = '<tr><td colspan="6" class="empty">No registered users yet. Use the Sign-Up page to add team members.</td></tr>';
    return;
  }
  body.innerHTML = users.map(u => {
    const joined = u.created_at ? new Date(u.created_at).toLocaleDateString() : '—';
    const last = u.last_login ? new Date(u.last_login).toLocaleString() : 'Never';
    const roleCls = `role-${u.role || 'analyst'}`;
    return `<tr>
      <td>${u.full_name || '—'}</td>
      <td>${u.username}</td>
      <td>${u.email || '—'}</td>
      <td><span class="role-tag ${roleCls}">${u.role || 'analyst'}</span></td>
      <td>${joined}</td>
      <td>${last}</td>
    </tr>`;
  }).join('');
}

// ── Thresholds ────────────────────────────────────────────────────────────────
async function saveThresholds() {
  const cluster_size = parseInt(document.getElementById('t-cluster').value);
  const risk_score = parseFloat(document.getElementById('t-risk').value);
  await apiFetch('/api/thresholds', {
    method: 'POST',
    body: JSON.stringify({ cluster_size, similarity: 0.5, risk_score })
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
    const el = document.createElement('div');
    el.className = `feed-line ${cls}`;
    el.textContent = text;
    feed.appendChild(el); feed.scrollTop = feed.scrollHeight;
  }
  function setStep(n, state) {
    const s = document.getElementById(`step-${n}`);
    const st = document.getElementById(`step-${n}-status`);
    if (!s) return;
    s.className = `demo-step ${state}`;
    st.textContent = state === 'done' ? '✅' : state === 'active' ? '⏳' : state === 'error' ? '❌' : '⏳';
  }

  setStep(1, 'active');
  feedLine('━━━ PHASE 0: Seeding ML Model ━━━', 'head');
  feedLine('  Training Isolation Forest on 400 synthetic legit fingerprints…');

  try {
    setStep(2, 'active');
    feedLine('');
    feedLine('━━━ PHASE 1: Legitimate Users Logging In ━━━', 'head');

    const res = await apiFetch('/api/demo/run-attack', { method: 'POST' });
    if (!res || !res.ok) { feedLine('  ✗ Attack API error', 'warn'); setStep(1, 'error'); btnAttack.disabled = false; return; }
    const data = await res.json();

    feedLine('  ✔ Model trained — isolation_forest.pkl ready', 'legit');
    setStep(1, 'done');

    (data.events?.legit || []).forEach(e => {
      const risk = parseFloat(e.risk_score || 0).toFixed(3);
      feedLine(`  ${new Date().toLocaleTimeString()}  ${String(e.user_id).padEnd(22)} IP:${String(e.ip_address || '?').padEnd(16)} Risk:${risk}  ✔ OK`, 'legit');
    });
    setStep(2, 'done');

    await new Promise(r => setTimeout(r, 400));
    setStep(3, 'active');
    feedLine('');
    feedLine('━━━ PHASE 2: 🤖 BOTNET ATTACK INCOMING ━━━', 'head');
    feedLine('  Source: 45.152.66.x/24 · Chrome 88 UA · Robotic typing (50ms)', 'warn');
    feedLine('');

    (data.events?.bots || []).forEach(e => {
      const risk = parseFloat(e.risk_score || 0).toFixed(3);
      feedLine(`  ${new Date().toLocaleTimeString()}  ${String(e.user_id).padEnd(22)} IP:${String(e.ip_address || '?').padEnd(16)} Risk:${risk}  🤖 BOT`, 'bot');
    });

    const avgL = (data.events?.legit || []).reduce((s, e) => s + parseFloat(e.risk_score || 0), 0) / Math.max((data.events?.legit || []).length, 1);
    const avgB = (data.events?.bots || []).reduce((s, e) => s + parseFloat(e.risk_score || 0), 0) / Math.max((data.events?.bots || []).length, 1);
    feedLine('');
    feedLine(`  Avg risk (legit): ${avgL.toFixed(4)}`, 'legit');
    feedLine(`  Avg risk (botnet): ${avgB.toFixed(4)}  ← elevated entropy & uniform patterns`, 'bot');
    setStep(3, 'done');

    await new Promise(r => setTimeout(r, 600));
    setStep(4, 'active');
    feedLine('');
    feedLine('━━━ PHASE 3: Graph Cluster Detection Running… ━━━', 'head');
    feedLine('  Neo4j scanning for coordinated login clusters…', 'info');
    await new Promise(r => setTimeout(r, 700));
    feedLine('  ✔ Cluster analysis complete — bots share behavior hash', 'legit');
    feedLine('');
    feedLine('  → Ready to freeze. Click "❄️ Freeze All Bots" to neutralise the attack.', 'info');

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
    const el = document.createElement('div');
    el.className = `feed-line ${cls}`;
    el.textContent = text;
    feed.appendChild(el); feed.scrollTop = feed.scrollHeight;
  }

  feedLine('');
  feedLine('━━━ PHASE 4: ❄️ Freezing All Bot Accounts ━━━', 'head');
  feedLine('  Detecting clusters → Auth0 block → Algorand audit…', 'info');

  try {
    const res = await apiFetch('/api/demo/freeze-all', { method: 'POST' });
    if (!res || !res.ok) { feedLine('  ✗ Freeze API error', 'warn'); btnFreeze.disabled = false; return; }
    const data = await res.json();

    (data.frozen_users || []).forEach(u => {
      const auth0 = u.auth0 ? '✔ Auth0' : '✗ Auth0(mock)';
      const chain = u.blockchain ? `✔ Chain: ${(u.txid || '').slice(0, 12)}…` : '— Chain(no ALGO)';
      feedLine(`  ❄ ${String(u.user_id).padEnd(24)} Risk:${parseFloat(u.risk_score || 0).toFixed(3)}  ${auth0}  ${chain}`, 'frozen-confirm');
    });
    feedLine('');
    feedLine(`  ━━ ${data.frozen_count} account(s) frozen. Attack neutralised! ━━`, 'head');

    document.getElementById('step-4').className = 'demo-step done';
    document.getElementById('step-4-status').textContent = '✅';

    resultCard.classList.remove('hidden');
    document.getElementById('freeze-result-title').textContent = `${data.frozen_count} Bot Account(s) Frozen!`;
    document.getElementById('freeze-result-subtitle').textContent = `${data.frozen_count} accounts blocked · Auth0 & Algorand audit logged.`;
    document.getElementById('freeze-result-list').innerHTML = (data.frozen_users || []).map(u => `
      <div class="frozen-row">
        <span>❄️ ${u.user_id}</span>
        <span style="color:var(--text2)">${u.ip_address || '—'}</span>
        <span style="color:var(--red)">Risk: ${parseFloat(u.risk_score || 0).toFixed(3)}</span>
        <span class="badge badge-auth0">${u.auth0 ? '✔ Auth0' : '✗ Auth0'}</span>
        <span class="badge badge-chain">${u.blockchain ? '⛓ Logged' : '— Chain'}</span>
      </div>`).join('');

    loadFrozenCount();
    setTimeout(() => feedLine('  → Switch to "❄️ Frozen Users" tab to see full details.', 'info'), 500);
  } catch (err) {
    feedLine(`  ✗ Error: ${err.message}`, 'warn');
  }
}

// ── Blockchain ────────────────────────────────────────────────────────────────
async function loadBlockchain() {
  const res = await apiFetch('/api/blockchain/status');
  if (!res) return;
  const data = await res.json();
  const nc = data.network === 'testnet' ? 'var(--yellow)' : 'var(--green)';
  const cfg = data.configured ? '<span class="green">Yes</span>' : '<span style="color:var(--red)">No</span>';
  let balance = 0;
  try {
    const br = await apiFetch('/api/blockchain/balance');
    if (br?.ok) { const b = await br.json(); balance = b.balance_algo || 0; }
  } catch { }
  document.getElementById('bchain-info').innerHTML = `
    <div>Network: <span class="val" style="color:${nc}">${data.network || '—'}</span></div>
    <div>Configured: ${cfg}</div>
    <div>Address: <span class="val">${data.address ? data.address.slice(0, 14) + '…' : 'Not set'}</span></div>
    <div>Balance: <span class="val">${parseFloat(balance).toFixed(4)} ALGO</span></div>`;
}
async function generateWallet() {
  const res = await apiFetch('/api/blockchain/generate-wallet', { method: 'POST' });
  if (!res) return;
  const d = await res.json();
  const el = document.getElementById('wallet-result');
  el.classList.remove('hidden');
  el.innerHTML = `<div><b>Address:</b> ${d.address}</div><div><b>Mnemonic:</b> ${d.mnemonic}</div>
    <div><b>Fund:</b> <a href="${d.fund_url}" target="_blank">${d.fund_url}</a></div>`;
}
async function bcLogFreeze() {
  const uid = document.getElementById('bc-freeze-uid').value.trim();
  const risk = parseFloat(document.getElementById('bc-freeze-risk').value);
  if (!uid) return;
  showBchainResult(await (await apiFetch(`/api/blockchain/log-freeze/${encodeURIComponent(uid)}?risk_score=${risk}`, { method: 'POST' }))?.json());
}
async function bcMintBadge() {
  const uid = document.getElementById('bc-badge-uid').value.trim();
  const risk = parseFloat(document.getElementById('bc-badge-risk').value);
  if (!uid) return;
  showBchainResult(await (await apiFetch(`/api/blockchain/mint-badge/${encodeURIComponent(uid)}?risk_score=${risk}`, { method: 'POST' }))?.json());
}
async function bcUpdateRep() {
  const uid = document.getElementById('bc-rep-uid').value.trim();
  const risk = parseFloat(document.getElementById('bc-rep-risk').value);
  if (!uid) return;
  showBchainResult(await (await apiFetch(`/api/blockchain/update-reputation/${encodeURIComponent(uid)}?risk_score=${risk}`, { method: 'POST' }))?.json());
}
async function bcFreezeAndLog() {
  const uid = document.getElementById('bc-fl-uid').value.trim();
  if (!uid) return;
  showBchainResult(await (await apiFetch(`/api/freeze-blockchain/${encodeURIComponent(uid)}`, { method: 'POST' }))?.json());
}
function showBchainResult(d) {
  const el = document.getElementById('bchain-action-result');
  el.classList.remove('hidden');
  el.textContent = JSON.stringify(d, null, 2);
}
