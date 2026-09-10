// GraphOne Intelligence Graph Frontend Logic

let currentTab = 'startups';
let currentData = [];
let searchQuery = '';

// DOM Elements
const kpiTotal = document.getElementById('kpi-total');
const kpiStartups = document.getElementById('kpi-startups');
const kpiProducts = document.getElementById('kpi-products');
const kpiPapers = document.getElementById('kpi-papers');
const kpiSignals = document.getElementById('kpi-signals');
const kpiAccuracy = document.getElementById('kpi-accuracy');

const tabBtns = document.querySelectorAll('.tab-btn');
const tableHead = document.getElementById('table-head');
const tableBody = document.getElementById('table-body');
const searchInput = document.getElementById('filter-search');
const filterSecondary = document.getElementById('filter-secondary');
const refreshBtn = document.getElementById('refresh-btn');

const graphContainer = document.getElementById('graph-container');
const archContainer = document.getElementById('arch-container');
const contentContainer = document.getElementById('content-container');
const controlsBar = document.getElementById('controls-bar');

const erInput = document.getElementById('er-input');
const erBtn = document.getElementById('er-btn');
const resRaw = document.getElementById('res-raw');
const resCanonical = document.getElementById('res-canonical');
const resConf = document.getElementById('res-conf');
const resMethod = document.getElementById('res-method');
const toastEl = document.getElementById('toast');

// Notification helper
function showToast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.add('show');
  setTimeout(() => toastEl.classList.remove('show'), 3500);
}

// Fetch stats
async function loadStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    kpiTotal.textContent = Number(data.total_records).toLocaleString();
    kpiStartups.textContent = Number(data.startups_count).toLocaleString();
    kpiProducts.textContent = Number(data.products_count).toLocaleString();
    kpiPapers.textContent = Number(data.papers_count).toLocaleString();
    kpiSignals.textContent = (data.jobs_count + data.news_count).toLocaleString();
    kpiAccuracy.textContent = (data.avg_confidence * 100).toFixed(1) + '%';

    document.getElementById('count-startups').textContent = Number(data.startups_count).toLocaleString();
    document.getElementById('count-products').textContent = Number(data.products_count).toLocaleString();
    document.getElementById('count-papers').textContent = Number(data.papers_count).toLocaleString();
    document.getElementById('count-jobs').textContent = Number(data.jobs_count).toLocaleString();
    document.getElementById('count-news').textContent = Number(data.news_count).toLocaleString();
    document.getElementById('count-mappings').textContent = Number(data.mappings_count).toLocaleString();
  } catch (err) {
    console.error('Failed to load stats:', err);
  }
}

// Tab Switching
tabBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    tabBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentTab = btn.dataset.tab;
    searchQuery = '';
    searchInput.value = '';

    if (currentTab === 'graph') {
      contentContainer.style.display = 'none';
      controlsBar.style.display = 'none';
      archContainer.style.display = 'none';
      graphContainer.style.display = 'block';
      initKnowledgeGraph();
    } else if (currentTab === 'architecture') {
      contentContainer.style.display = 'none';
      controlsBar.style.display = 'none';
      graphContainer.style.display = 'none';
      archContainer.style.display = 'block';
    } else {
      contentContainer.style.display = 'block';
      controlsBar.style.display = 'flex';
      graphContainer.style.display = 'none';
      archContainer.style.display = 'none';
      setupSecondaryFilter();
      loadTabData();
    }
  });
});

// Configure secondary dropdown per tab
function setupSecondaryFilter() {
  filterSecondary.innerHTML = '<option value="ALL">All Categories</option>';
  if (currentTab === 'products') {
    filterSecondary.innerHTML = `
      <option value="ALL">All Pricing Tiers</option>
      <option value="FREE">FREE (Open Source)</option>
      <option value="FREEMIUM">FREEMIUM</option>
      <option value="PAID">PAID</option>
      <option value="ENTERPRISE">ENTERPRISE</option>
    `;
  } else if (currentTab === 'jobs') {
    filterSecondary.innerHTML = `
      <option value="ALL">All Roles</option>
      <option value="Machine Learning">AI / Machine Learning</option>
      <option value="Engineering">Engineering</option>
      <option value="Product">Product Management</option>
    `;
  } else if (currentTab === 'news') {
    filterSecondary.innerHTML = `
      <option value="ALL">All News Sources</option>
      <option value="TechCrunch">TechCrunch AI</option>
      <option value="MIT">MIT Technology Review</option>
      <option value="Artificial">AI News</option>
      <option value="Wired">Wired AI</option>
      <option value="Ars Technica">Ars Technica</option>
      <option value="Hacker News">Hacker News AI</option>
    `;
  }
}

// Load data for active tab
async function loadTabData() {
  tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 40px; color: var(--text-muted);">Loading live records...</td></tr>';
  let url = `/api/${currentTab}?search=${encodeURIComponent(searchQuery)}`;

  if (currentTab === 'products' && filterSecondary.value !== 'ALL') {
    url += `&pricing=${encodeURIComponent(filterSecondary.value)}`;
  } else if (currentTab === 'jobs' && filterSecondary.value !== 'ALL') {
    url += `&role=${encodeURIComponent(filterSecondary.value)}`;
  } else if (currentTab === 'news' && filterSecondary.value !== 'ALL') {
    url += `&source=${encodeURIComponent(filterSecondary.value)}`;
  }

  try {
    const res = await fetch(url);
    const result = await res.json();
    currentData = result.data || [];
    renderTable();
  } catch (err) {
    tableBody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #EF4444; padding: 40px;">Error loading data: ${err.message}</td></tr>`;
  }
}

// Render dynamic table based on tab
function renderTable() {
  if (currentTab === 'startups') {
    tableHead.innerHTML = `
      <th>#</th>
      <th>Canonical Startup Name</th>
      <th>Team Size</th>
      <th>Industry / Focus</th>
      <th>Description</th>
      <th>Source &amp; Link</th>
    `;
    if (!currentData.length) {
      tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 30px;">No startups found.</td></tr>';
      return;
    }
    tableBody.innerHTML = currentData.map((s, idx) => `
      <tr>
        <td style="color: var(--text-muted); font-family: var(--font-mono);">${idx + 1}</td>
        <td><strong style="color: #F8FAFC; font-size: 0.95rem;">${escapeHtml(s['content.entityName'] || 'Startup')}</strong></td>
        <td><span class="badge badge-freemium">${s['content.data.employeeCount'] ? s['content.data.employeeCount'] + ' Employees' : 'Undisclosed'}</span></td>
        <td><span style="color: var(--accent-cyan); font-size: 0.8rem;">${escapeHtml(s['industry'] || 'AI / Tech')}</span></td>
        <td style="max-width: 380px; font-size: 0.8rem; color: var(--text-secondary);">${escapeHtml(s['description'] || '')}</td>
        <td>
          <a href="${s['source.url']}" target="_blank" class="badge-source">
            <span>🔗 YC Directory</span>
          </a>
        </td>
      </tr>
    `).join('');
  } else if (currentTab === 'products') {
    tableHead.innerHTML = `
      <th>#</th>
      <th>Product Name</th>
      <th>Parent Startup / Creator</th>
      <th>Pricing Tier</th>
      <th>Category</th>
      <th>Official Link</th>
    `;
    if (!currentData.length) {
      tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 30px;">No products found.</td></tr>';
      return;
    }
    tableBody.innerHTML = currentData.map((p, idx) => {
      const tier = (p['content.pricingModel'] || 'FREEMIUM').toUpperCase();
      const badgeClass = tier === 'FREE' ? 'badge-free' : tier === 'PAID' ? 'badge-paid' : tier === 'ENTERPRISE' ? 'badge-enterprise' : 'badge-freemium';
      return `
        <tr>
          <td style="color: var(--text-muted); font-family: var(--font-mono);">${idx + 1}</td>
          <td><strong style="color: #F8FAFC;">${escapeHtml(p['product_name'] || p['content.startupName'])}</strong></td>
          <td style="color: #93C5FD;">${escapeHtml(p['content.startupName'] || '')}</td>
          <td><span class="badge ${badgeClass}">${tier}</span></td>
          <td style="font-size: 0.8rem; color: var(--text-secondary);">${escapeHtml(p['category'] || 'AI Software')}</td>
          <td><a href="${p['source.url']}" target="_blank" class="badge-source">🔗 Visit Site</a></td>
        </tr>
      `;
    }).join('');
  } else if (currentTab === 'papers') {
    tableHead.innerHTML = `
      <th>#</th>
      <th>Research Paper Title</th>
      <th>Authors</th>
      <th>GitHub Metrics</th>
      <th>Publication Date</th>
      <th>ArXiv / Code Links</th>
    `;
    if (!currentData.length) {
      tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 30px;">No papers found.</td></tr>';
      return;
    }
    tableBody.innerHTML = currentData.map((r, idx) => `
      <tr>
        <td style="color: var(--text-muted); font-family: var(--font-mono);">${idx + 1}</td>
        <td style="max-width: 360px;"><strong style="color: #F8FAFC; line-height: 1.35;">${escapeHtml(r['content.title'] || '')}</strong></td>
        <td style="max-width: 220px; font-size: 0.78rem; color: var(--text-secondary);">${escapeHtml(r['content.authors'] || '')}</td>
        <td>
          ${r['content.github_url'] ? `
            <div class="stars-pill">
              <span>⭐</span> ${Number(r['content.github_stars'] || 0).toLocaleString()} stars
            </div>
          ` : '<span style="color: var(--text-muted); font-size: 0.75rem;">No Repo Link</span>'}
        </td>
        <td style="font-family: var(--font-mono); font-size: 0.76rem; color: var(--text-muted);">${(r['content.published_date'] || '').slice(0, 10)}</td>
        <td>
          <div style="display: flex; gap: 6px;">
            <a href="${r['content.paper_url']}" target="_blank" class="badge-source">📄 Paper</a>
            ${r['content.github_url'] ? `<a href="${r['content.github_url']}" target="_blank" class="badge-source" style="border-color: #F59E0B; color: #FBBF24;">💻 Repo</a>` : ''}
          </div>
        </td>
      </tr>
    `).join('');
  } else if (currentTab === 'jobs') {
    tableHead.innerHTML = `
      <th>#</th>
      <th>Role Title</th>
      <th>Company</th>
      <th>Freshness Status</th>
      <th>Category</th>
      <th>Job Link</th>
    `;
    if (!currentData.length) {
      tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 30px;">No jobs found.</td></tr>';
      return;
    }
    tableBody.innerHTML = currentData.map((j, idx) => `
      <tr>
        <td style="color: var(--text-muted); font-family: var(--font-mono);">${idx + 1}</td>
        <td><strong style="color: #F8FAFC;">${escapeHtml(j['title'] || 'Software Engineer')}</strong></td>
        <td><span style="color: #60A5FA; font-weight: 600;">${escapeHtml(j['content.company'] || '')}</span></td>
        <td>
          <span class="badge badge-free" style="gap: 6px;">
            <span class="status-dot" style="width: 6px; height: 6px;"></span>
            &lt;24h Fresh
          </span>
        </td>
        <td><span class="badge badge-freemium">${escapeHtml(j['content.role_family'] || 'Engineering')}</span></td>
        <td><a href="${j['job_url'] || j['source.name']}" target="_blank" class="badge-source">🔗 Apply</a></td>
      </tr>
    `).join('');
  } else if (currentTab === 'news') {
    tableHead.innerHTML = `
      <th>#</th>
      <th>News Article Headline</th>
      <th>Source Outlet</th>
      <th>Published Timestamp</th>
      <th>Summary / Excerpt</th>
      <th>Source Link</th>
    `;
    if (!currentData.length) {
      tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 30px;">No news found.</td></tr>';
      return;
    }
    tableBody.innerHTML = currentData.map((n, idx) => `
      <tr>
        <td style="color: var(--text-muted); font-family: var(--font-mono);">${idx + 1}</td>
        <td style="max-width: 320px;"><strong style="color: #F8FAFC;">${escapeHtml(n['content.title'] || '')}</strong></td>
        <td><span class="badge badge-enterprise">${escapeHtml(n['source.name'] || 'AI News')}</span></td>
        <td style="font-family: var(--font-mono); font-size: 0.78rem; color: var(--accent-emerald);">
          ${(n['content.published_date'] || '').replace('T', ' ').slice(0, 19)} UTC
        </td>
        <td style="max-width: 360px; font-size: 0.78rem; color: var(--text-secondary);">${escapeHtml(n['summary'] || '')}</td>
        <td><a href="${n['source.url']}" target="_blank" class="badge-source">🔗 Read Article</a></td>
      </tr>
    `).join('');
  } else if (currentTab === 'mappings') {
    tableHead.innerHTML = `
      <th>#</th>
      <th>Raw Unstructured String</th>
      <th>Resolved Canonical Entity</th>
      <th>Confidence Score</th>
      <th>Resolution Method</th>
      <th>Source Context</th>
    `;
    if (!currentData.length) {
      tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 30px;">No audit logs found.</td></tr>';
      return;
    }
    tableBody.innerHTML = currentData.map((m, idx) => {
      const conf = Math.round(Number(m['confidence_score'] || 0) * 100);
      return `
        <tr>
          <td style="color: var(--text-muted); font-family: var(--font-mono);">${idx + 1}</td>
          <td><code style="color: #EF4444; font-size: 0.8rem;">"${escapeHtml(m['raw_name'] || '')}"</code></td>
          <td><strong style="color: #34D399; font-size: 0.9rem;">${escapeHtml(m['canonical_name'] || '')}</strong></td>
          <td>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-family: var(--font-mono); font-weight: 700; color: ${conf >= 95 ? '#34D399' : '#FBBF24'};">${conf}%</span>
            </div>
          </td>
          <td><span class="badge badge-freemium">${escapeHtml(m['resolution_method'] || '')}</span></td>
          <td style="font-size: 0.78rem; color: var(--text-muted);">${escapeHtml(m['source_context'] || '')}</td>
        </tr>
      `;
    }).join('');
  }
}

// Live Entity Resolution Playground Tester
async function testEntityResolution() {
  const raw = erInput.value.trim();
  if (!raw) return;
  erBtn.disabled = true;
  erBtn.textContent = 'Resolving...';

  try {
    const res = await fetch('/api/resolve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: raw })
    });
    const data = await res.json();
    resRaw.textContent = data.raw_name;
    resCanonical.textContent = data.canonical_name;
    resConf.textContent = Math.round(data.confidence_score * 100) + '%';
    resMethod.textContent = data.resolution_method;
    showToast(`Resolved "${data.raw_name}" ➔ "${data.canonical_name}"`);
  } catch (err) {
    showToast('Resolution error: ' + err.message);
  } finally {
    erBtn.disabled = false;
    erBtn.textContent = 'Resolve Entity';
  }
}

erBtn.addEventListener('click', testEntityResolution);
erInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') testEntityResolution();
});

// Search and Filter Handlers
let searchDebounce;
searchInput.addEventListener('input', e => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => {
    searchQuery = e.target.value.trim();
    loadTabData();
  }, 250);
});

filterSecondary.addEventListener('change', () => {
  loadTabData();
});

refreshBtn.addEventListener('click', () => {
  loadStats();
  loadTabData();
  showToast('Refreshed live intelligence feed.');
});

// Interactive Knowledge Graph Canvas Animation
let graphAnimId;
function initKnowledgeGraph() {
  const canvas = document.getElementById('graph-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  canvas.width = canvas.parentElement.clientWidth - 40;
  canvas.height = 460;

  const nodes = [
    { id: 1, name: 'OpenAI', type: 'startup', x: 200, y: 150, vx: 0.2, vy: 0.1, color: '#3B82F6' },
    { id: 2, name: 'ChatGPT', type: 'product', x: 280, y: 240, vx: -0.15, vy: 0.2, color: '#06B6D4' },
    { id: 3, name: 'Anthropic', type: 'startup', x: 450, y: 120, vx: 0.1, vy: -0.1, color: '#6366F1' },
    { id: 4, name: 'Claude 3.5', type: 'product', x: 550, y: 220, vx: -0.1, vy: 0.15, color: '#06B6D4' },
    { id: 5, name: 'Attention Is All You Need', type: 'paper', x: 350, y: 340, vx: 0.1, vy: 0.2, color: '#F59E0B' },
    { id: 6, name: 'Mistral AI', type: 'startup', x: 700, y: 160, vx: -0.2, vy: 0.1, color: '#10B981' },
    { id: 7, name: 'Mistral Large', type: 'product', x: 780, y: 250, vx: 0.15, vy: -0.15, color: '#06B6D4' },
    { id: 8, name: 'AI Research Eng', type: 'job', x: 400, y: 220, vx: 0.1, vy: -0.1, color: '#EC4899' },
    { id: 9, name: 'Hugging Face', type: 'startup', x: 880, y: 130, vx: -0.1, vy: 0.1, color: '#8B5CF6' },
    { id: 10, name: 'Transformers', type: 'product', x: 920, y: 270, vx: 0.1, vy: 0.1, color: '#06B6D4' },
    { id: 11, name: 'Perplexity AI', type: 'startup', x: 150, y: 320, vx: 0.1, vy: -0.1, color: '#3B82F6' },
  ];

  const links = [
    [1, 2], [3, 4], [6, 7], [9, 10], [1, 5], [3, 5], [1, 8], [3, 8], [6, 8], [1, 11]
  ];

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw links
    ctx.lineWidth = 1;
    for (const [fromId, toId] of links) {
      const from = nodes.find(n => n.id === fromId);
      const to = nodes.find(n => n.id === toId);
      if (!from || !to) continue;
      const grad = ctx.createLinearGradient(from.x, from.y, to.x, to.y);
      grad.addColorStop(0, 'rgba(99, 102, 241, 0.25)');
      grad.addColorStop(1, 'rgba(6, 182, 212, 0.25)');
      ctx.strokeStyle = grad;
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();
    }

    // Update and draw nodes
    for (const n of nodes) {
      n.x += n.vx;
      n.y += n.vy;
      if (n.x < 50 || n.x > canvas.width - 50) n.vx *= -1;
      if (n.y < 50 || n.y > canvas.height - 50) n.vy *= -1;

      // Glow
      ctx.shadowBlur = 14;
      ctx.shadowColor = n.color;
      ctx.fillStyle = n.color;
      ctx.beginPath();
      ctx.arc(n.x, n.y, 8, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;

      // Label
      ctx.fillStyle = '#E2E8F0';
      ctx.font = '11px Outfit, Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(n.name, n.x, n.y + 20);
    }

    graphAnimId = requestAnimationFrame(draw);
  }

  cancelAnimationFrame(graphAnimId);
  draw();
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Initial Load
loadStats();
setupSecondaryFilter();
loadTabData();
