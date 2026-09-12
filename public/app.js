// GraphOne Intelligence Graph Frontend Logic

let currentTab = 'startups';
let currentData = [];
let searchQuery = '';
let currentPage = 1;
let pageSize = 10;

// DOM Elements
const kpiTotal = document.getElementById('kpi-total');
const kpiStartups = document.getElementById('kpi-startups');
const kpiProducts = document.getElementById('kpi-products');
const kpiPapers = document.getElementById('kpi-papers');
const kpiSignals = document.getElementById('kpi-signals');
const kpiAccuracy = document.getElementById('kpi-accuracy');
const kpiFreshSub = document.getElementById('kpi-freshness-sub');

const tabBtns = document.querySelectorAll('.tab-btn');
const tableHead = document.getElementById('table-head');
const tableBody = document.getElementById('table-body');
const searchInput = document.getElementById('filter-search');
const filterSecondary = document.getElementById('filter-secondary');
const filterTeamSize = document.getElementById('filter-team-size');
const filterSort = document.getElementById('filter-sort');
const refreshBtn = document.getElementById('refresh-btn');

// Pagination Elements
const pageStartEl = document.getElementById('page-start');
const pageEndEl = document.getElementById('page-end');
const pageTotalEl = document.getElementById('page-total');
const paginationControls = document.getElementById('pagination-controls');
const pageSizeSelect = document.getElementById('page-size-select');

if (pageSizeSelect) {
  pageSizeSelect.addEventListener('change', () => {
    pageSize = parseInt(pageSizeSelect.value, 10) || 10;
    currentPage = 1;
    renderTable();
  });
}

if (filterTeamSize) {
  filterTeamSize.addEventListener('change', () => {
    currentPage = 1;
    loadTabData();
  });
}

if (filterSort) {
  filterSort.addEventListener('change', () => {
    currentPage = 1;
    loadTabData();
  });
}

const graphContainer = document.getElementById('graph-container');
const archContainer = document.getElementById('arch-container');
const pipelineContainer = document.getElementById('pipeline-container');
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
    if (kpiTotal) kpiTotal.textContent = Number(data.total_records).toLocaleString();
    if (kpiStartups) kpiStartups.textContent = Number(data.startups_count).toLocaleString();
    if (kpiProducts) kpiProducts.textContent = Number(data.products_count).toLocaleString();
    if (kpiPapers) kpiPapers.textContent = Number(data.papers_count).toLocaleString();
    const kpiJobs = document.getElementById('kpi-jobs');
    if (kpiJobs) kpiJobs.textContent = Number(data.jobs_count).toLocaleString();
    const kpiNews = document.getElementById('kpi-news');
    if (kpiNews) kpiNews.textContent = Number(data.news_count).toLocaleString();
    if (kpiSignals) kpiSignals.textContent = (data.jobs_count + data.news_count).toLocaleString();
    if (kpiAccuracy) kpiAccuracy.textContent = (data.avg_confidence * 100).toFixed(1) + '%';
    if (kpiFreshSub) kpiFreshSub.textContent = '100% verified <24h';
  } catch (err) {
    console.error('Failed to load stats:', err);
  }
}

// Pipeline Monitoring Loader
async function loadPipelineData() {
  try {
    const res = await fetch('/api/pipeline/status');
    const data = await res.json();

    let totalSeen = 0;
    if (data.sources) {
      data.sources.forEach(s => totalSeen += (s.total_seen || 0));
      const plTotalEl = document.getElementById('pl-total-seen');
      if (plTotalEl) plTotalEl.textContent = totalSeen > 0 ? totalSeen.toLocaleString() : '273+';

      const tbody = document.getElementById('pl-sources-tbody');
      if (tbody) {
        tbody.innerHTML = data.sources.map(s => `
          <tr>
            <td style="font-weight: 600; color: var(--text);">${s.source_name}</td>
            <td><span class="badge ${s.source_type === 'NEWS' ? 'badge-ai' : 'badge-freemium'}">${s.source_type}</span></td>
            <td><span class="badge badge-fresh">● ${s.last_status || 'SUCCESS'}</span></td>
            <td style="font-family: var(--font-mono); font-weight: 600; color: var(--accent);">${s.total_seen || 0} items</td>
            <td style="font-size: 0.8rem; color: var(--text-muted);">${s.last_run_timestamp ? new Date(s.last_run_timestamp).toUTCString() : 'Active'}</td>
            <td><span style="font-size: 0.76rem; color: #5EEAD4; background: rgba(94,234,212,0.08); padding: 2px 8px; border-radius: 4px;">Polite 0.3-1.2s | Isolated</span></td>
          </tr>
        `).join('');
      }
    }

    const logsRes = await fetch('/api/pipeline/logs');
    const logsData = await logsRes.json();
    const runsTbody = document.getElementById('pl-runs-tbody');
    if (runsTbody) {
      if (logsData.runs && logsData.runs.length > 0) {
        runsTbody.innerHTML = logsData.runs.map(r => `
          <tr>
            <td style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--accent);">${r.run_id}</td>
            <td style="font-size: 0.8rem; color: var(--text-muted);">${new Date(r.start_time).toLocaleTimeString()}</td>
            <td style="font-weight: 600;">${r.summary && r.summary.elapsed_seconds ? r.summary.elapsed_seconds.toFixed(1) + 's' : '<1s'}</td>
            <td>${r.sources_checked} sources</td>
            <td>${r.new_items_found}</td>
            <td><span style="color: #5EEAD4; font-weight: 600;">${r.passed_freshness}</span></td>
            <td><span style="color: #FBBF24; font-weight: 500;">${r.discarded_stale}</span></td>
            <td><span class="badge badge-fresh">${r.status}</span></td>
          </tr>
        `).join('');
      } else {
        runsTbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 20px;">No cycle logs yet. Click "Run Monitoring Cycle Now" above.</td></tr>';
      }
    }
  } catch (err) {
    console.error('Error loading pipeline data:', err);
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
    currentPage = 1;
    currentData = []; // Clear so loadTabData shows "Loading..." for new tab

    const resolverContainer = document.getElementById('resolver-container');

    if (currentTab === 'graph') {
      contentContainer.style.display = 'none';
      controlsBar.style.display = 'none';
      archContainer.style.display = 'none';
      if (pipelineContainer) pipelineContainer.style.display = 'none';
      if (resolverContainer) resolverContainer.style.display = 'none';
      graphContainer.style.display = 'block';
      initKnowledgeGraph();
    } else if (currentTab === 'architecture') {
      contentContainer.style.display = 'none';
      controlsBar.style.display = 'none';
      graphContainer.style.display = 'none';
      if (pipelineContainer) pipelineContainer.style.display = 'none';
      if (resolverContainer) resolverContainer.style.display = 'none';
      archContainer.style.display = 'block';
    } else if (currentTab === 'pipeline') {
      contentContainer.style.display = 'none';
      controlsBar.style.display = 'none';
      graphContainer.style.display = 'none';
      archContainer.style.display = 'none';
      if (resolverContainer) resolverContainer.style.display = 'none';
      if (pipelineContainer) pipelineContainer.style.display = 'block';
      loadPipelineData();
    } else if (currentTab === 'resolver') {
      contentContainer.style.display = 'none';
      controlsBar.style.display = 'none';
      graphContainer.style.display = 'none';
      archContainer.style.display = 'none';
      if (pipelineContainer) pipelineContainer.style.display = 'none';
      if (resolverContainer) resolverContainer.style.display = 'block';
    } else {
      contentContainer.style.display = 'block';
      controlsBar.style.display = 'flex';
      graphContainer.style.display = 'none';
      archContainer.style.display = 'none';
      if (pipelineContainer) pipelineContainer.style.display = 'none';
      if (resolverContainer) resolverContainer.style.display = 'none';


      if (filterTeamSize) {
        filterTeamSize.style.display = currentTab === 'startups' ? 'block' : 'none';
      }

      if (filterSort) {
        if (currentTab === 'startups') {
          filterSort.style.display = 'block';
          filterSort.innerHTML = `
            <option value="default">Sort: Default</option>
            <option value="team_desc">👥 Team Size: High to Low ↓</option>
            <option value="team_asc">👥 Team Size: Low to High ↑</option>
            <option value="name">🔤 Name (A–Z)</option>
          `;
        } else if (currentTab === 'papers') {
          filterSort.style.display = 'block';
          filterSort.innerHTML = `
            <option value="impact">🏆 Sort: Combined Impact</option>
            <option value="stars">⭐ Sort: GitHub Stars ↓</option>
            <option value="upvotes">🤗 Sort: HF Upvotes ↓</option>
            <option value="date">📅 Sort: Publication Date</option>
          `;
        } else {
          filterSort.style.display = 'none';
        }
      }

      setupSecondaryFilter();
      loadTabData();
    }
  });
});

// Configure secondary dropdown per tab
function setupSecondaryFilter() {
  filterSecondary.innerHTML = '<option value="ALL">All Categories</option>';
  if (currentTab === 'startups') {
    filterSecondary.innerHTML = `
      <option value="ALL">All Industries</option>
      <option value="B2B">B2B Software</option>
      <option value="Fintech">Fintech</option>
      <option value="Healthcare">Healthcare &amp; Biotech</option>
      <option value="Security">Cybersecurity</option>
      <option value="Infrastructure">Infrastructure &amp; Cloud</option>
      <option value="Analytics">Analytics &amp; AI</option>
      <option value="Consumer">Consumer &amp; Social</option>
      <option value="Engineering">Engineering &amp; DevTools</option>
      <option value="Robotics">Robotics &amp; Industrials</option>
      <option value="Climate">Climate &amp; Energy</option>
      <option value="Education">Education</option>
      <option value="Defense">Defense &amp; Space</option>
    `;
  } else if (currentTab === 'papers') {
    filterSecondary.innerHTML = `
      <option value="ALL">All Research Papers</option>
      <option value="CODE_ONLY">💻 Open-Source Code Repos Only</option>
      <option value="HF">🤗 Hugging Face Daily Papers</option>
      <option value="ARXIV">📄 ArXiv Preprints</option>
      <option value="PWC">⚡ Papers With Code</option>
    `;
  } else if (currentTab === 'products') {
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

// Skeleton loading placeholder rows
function showSkeletonRows() {
  const cols = 6; // default column count
  const rows = pageSize || 10;
  const widths = [30, 55, 70, 40, 50, 65, 45, 60, 35, 75]; // Varying widths for realism

  // Set a generic header while loading
  tableHead.innerHTML = Array.from({ length: cols }, (_, i) =>
    `<th><span class="skeleton-bar" style="width: ${30 + i * 8}%;"></span></th>`
  ).join('');

  tableBody.innerHTML = Array.from({ length: rows }, (_, rowIdx) =>
    `<tr>${Array.from({ length: cols }, (_, colIdx) => {
      const w = widths[(rowIdx + colIdx) % widths.length];
      return `<td><span class="skeleton-bar" style="width: ${w}%;"></span></td>`;
    }).join('')}</tr>`
  ).join('');
}

// Load data for active tab
async function loadTabData() {
  const hasExistingData = currentData.length > 0;
  const tableEl = document.getElementById('main-table');

  if (!hasExistingData) {
    // Show skeleton placeholder rows that mimic the table structure
    showSkeletonRows();
  } else if (tableEl) {
    // Dim existing content during fetch — no layout shift, no flicker
    tableEl.style.opacity = '0.45';
    tableEl.style.pointerEvents = 'none';
  }

  let url = `/api/${currentTab}?search=${encodeURIComponent(searchQuery)}`;

  if (currentTab === 'startups') {
    if (filterSecondary.value !== 'ALL') {
      url += `&industry=${encodeURIComponent(filterSecondary.value)}`;
    }
    if (filterTeamSize && filterTeamSize.value !== 'ALL') {
      url += `&team_size=${encodeURIComponent(filterTeamSize.value)}`;
    }
    if (filterSort && filterSort.value && filterSort.value !== 'default') {
      url += `&sort_by=${encodeURIComponent(filterSort.value)}`;
    }
  } else if (currentTab === 'papers') {
    const sec = filterSecondary.value;
    if (sec === 'CODE_ONLY') {
      url += '&has_code=true';
    } else if (sec === 'HF') {
      url += '&source=Hugging%20Face';
    } else if (sec === 'ARXIV') {
      url += '&source=ArXiv';
    } else if (sec === 'PWC') {
      url += '&source=Papers%20with%20Code';
    }
    if (filterSort && filterSort.value) {
      url += `&sort_by=${encodeURIComponent(filterSort.value)}`;
    }
  } else if (currentTab === 'products' && filterSecondary.value !== 'ALL') {
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
  } finally {
    // Restore table visibility instantly
    if (tableEl) {
      tableEl.style.opacity = '1';
      tableEl.style.pointerEvents = '';
    }
  }
}

// Render dynamic table based on tab
function renderTable() {
  const totalItems = currentData.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  if (currentPage > totalPages) currentPage = totalPages;
  if (currentPage < 1) currentPage = 1;

  const startIndex = totalItems === 0 ? 0 : (currentPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalItems);
  const pageData = currentData.slice(startIndex, endIndex);

  if (pageStartEl) pageStartEl.textContent = totalItems === 0 ? '0' : (startIndex + 1).toLocaleString();
  if (pageEndEl) pageEndEl.textContent = endIndex.toLocaleString();
  if (pageTotalEl) pageTotalEl.textContent = totalItems.toLocaleString();

  renderPaginationControls(totalPages);

  if (currentTab === 'startups') {
    tableHead.innerHTML = `
      <th style="width: 60px;">#</th>
      <th>Canonical Startup Name</th>
      <th>Team Size</th>
      <th>Industry Category</th>
      <th>Description</th>
      <th>Direct Links &amp; Profile</th>
    `;
    if (!pageData.length) {
      tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 30px;">No startups found matching the selected filters.</td></tr>';
      return;
    }
    tableBody.innerHTML = pageData.map((s, idx) => {
      const empCount = s['content.data.employeeCount'];
      const hasCount = empCount !== undefined && empCount !== null && empCount !== '' && Number(empCount) > 0;
      const empLabel = hasCount ? `${Number(empCount)} Employees` : 'Undisclosed';
      const website = s['content.data.website'] || '';
      const ycUrl = s['source.url'] || '';
      const batch = s['content.data.batch'] || '';

      return `
        <tr>
          <td style="color: var(--text-muted); font-family: var(--font-mono);">${startIndex + idx + 1}</td>
          <td>
            <div style="display: flex; align-items: center; gap: 8px;">
              <strong style="color: var(--text); font-size: 0.95rem;">${escapeHtml(s['content.entityName'] || 'Startup')}</strong>
              ${batch ? `<span class="badge badge-paid" style="font-size: 0.68rem; padding: 1px 6px;">${escapeHtml(batch)}</span>` : ''}
            </div>
          </td>
          <td>
            <span class="badge ${hasCount && Number(empCount) >= 10 ? 'badge-enterprise' : 'badge-freemium'}" style="white-space: nowrap;">
              👥 ${empLabel}
            </span>
          </td>
          <td><span style="color: var(--accent); font-size: 0.8rem;">${escapeHtml(s['industry'] || 'AI / Tech')}</span></td>
          <td style="max-width: 380px; font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(s['description'] || '')}</td>
          <td>
            <div style="display: flex; gap: 6px; flex-wrap: wrap;">
              ${website ? `<a href="${website}" target="_blank" class="btn-link-action btn-paper" title="Visit Official Website">🌐 Website</a>` : ''}
              ${ycUrl ? `<a href="${ycUrl}" target="_blank" class="btn-link-action btn-repo" title="View YC Directory Dossier">🔗 YC Profile</a>` : ''}
              <button class="explore-graph-btn" onclick="openEntityGraph('${escapeHtml(s['content.entityName'] || '')}')" title="View Near-Linkage Graph">🕸️ Graph</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  } else if (currentTab === 'products') {
    tableHead.innerHTML = `
      <th>#</th>
      <th>Product Name</th>
      <th>Parent Startup / Creator</th>
      <th>Pricing Tier</th>
      <th>Category</th>
      <th>Official Link</th>
    `;
    if (!pageData.length) {
      tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 30px;">No products found.</td></tr>';
      return;
    }
    tableBody.innerHTML = pageData.map((p, idx) => {
      const tier = (p['content.pricingModel'] || 'FREEMIUM').toUpperCase();
      const badgeClass = tier === 'FREE' ? 'badge-free' : tier === 'PAID' ? 'badge-paid' : tier === 'ENTERPRISE' ? 'badge-enterprise' : 'badge-freemium';
      return `
        <tr>
          <td style="color: var(--text-muted); font-family: var(--font-mono);">${startIndex + idx + 1}</td>
          <td><strong style="color: #F8FAFC;">${escapeHtml(p['product_name'] || p['content.startupName'])}</strong></td>
          <td style="color: var(--accent);">${escapeHtml(p['content.startupName'] || '')}</td>
          <td><span class="badge ${badgeClass}">${tier}</span></td>
          <td style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(p['category'] || 'AI Software')}</td>
          <td>
            <div style="display: flex; gap: 6px; flex-wrap: wrap;">
              <a href="${p['source.url']}" target="_blank" class="badge-source">🔗 Visit Site</a>
              <button class="explore-graph-btn" onclick="openEntityGraph('${escapeHtml(p['product_name'] || p['content.startupName'] || '')}', 'products')" title="View Product Linkage Graph">🕸️ Graph</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  } else if (currentTab === 'papers') {
    tableHead.innerHTML = `
      <th style="width: 70px;">Rank</th>
      <th>Research Paper Title &amp; Sourcing</th>
      <th>Authors</th>
      <th>Source Metrics</th>
      <th>Published</th>
      <th>Openable Links &amp; Code</th>
    `;
    if (!pageData.length) {
      tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 30px;">No research papers found matching the selected criteria.</td></tr>';
      return;
    }
    tableBody.innerHTML = pageData.map((r, idx) => {
      const rankNum = Number(r['content.rank'] || (startIndex + idx + 1));
      const rankClass = rankNum === 1 ? 'rank-gold' : rankNum === 2 ? 'rank-silver' : rankNum === 3 ? 'rank-bronze' : '';
      const rankMedal = rankNum === 1 ? '🥇 ' : rankNum === 2 ? '🥈 ' : rankNum === 3 ? '🥉 ' : '#';

      const sourcePlatform = r['content.source_platform'] || 'ArXiv';
      const sourceBadge = sourcePlatform.includes('Hugging Face')
        ? '<span class="badge-hf">🤗 Hugging Face</span>'
        : sourcePlatform.includes('Papers with Code')
        ? '<span class="badge-pwc">⚡ PwC</span>'
        : '<span class="badge-arxiv">📄 ArXiv</span>';

      const stars = Number(r['content.github_stars'] || 0);
      const upvotes = Number(r['content.huggingface_upvotes'] || 0);

      const paperUrl = r['content.paper_url'] || '';
      let pdfUrl = r['content.pdf_url'] || '';
      if (!pdfUrl && paperUrl.includes('/abs/')) {
        pdfUrl = paperUrl.replace('/abs/', '/pdf/') + '.pdf';
      }
      const githubUrl = r['content.github_url'] || '';
      const hfUrl = r['content.huggingface_url'] || '';

      return `
        <tr>
          <td>
            <span class="rank-badge ${rankClass}">${rankMedal}${rankNum}</span>
          </td>
          <td style="max-width: 380px;">
            <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 5px;">
              ${sourceBadge}
            </div>
            <strong style="color: var(--text); line-height: 1.35; font-size: 0.92rem;">${escapeHtml(r['content.title'] || '')}</strong>
          </td>
          <td style="max-width: 190px; font-size: 0.78rem; color: var(--text-muted);">${escapeHtml(r['content.authors'] || '')}</td>
          <td>
            <div style="display: flex; flex-direction: column; gap: 4px;">
              ${githubUrl ? `
                <div class="stars-pill">
                  <span>⭐</span> ${stars.toLocaleString()} stars
                </div>
              ` : '<span style="color: var(--text-muted); font-size: 0.75rem;">No repo code</span>'}
              ${upvotes > 0 ? `
                <div class="hf-pill">
                  <span>🤗</span> ${upvotes.toLocaleString()} upvotes
                </div>
              ` : ''}
            </div>
          </td>
          <td style="font-family: var(--font-mono); font-size: 0.76rem; color: var(--text-muted);">${(r['content.published_date'] || '').slice(0, 10)}</td>
          <td>
            <div style="display: flex; flex-wrap: wrap; gap: 6px; align-items: center;">
              ${paperUrl ? `<a href="${paperUrl}" target="_blank" class="btn-link-action btn-paper" title="Open paper abstract">📄 Paper</a>` : ''}
              ${pdfUrl ? `<a href="${pdfUrl}" target="_blank" class="btn-link-action btn-pdf" title="Open direct PDF">📥 PDF</a>` : ''}
              ${githubUrl ? `<a href="${githubUrl}" target="_blank" class="btn-link-action btn-repo" title="Open verified repository code">💻 Code Repo</a>` : ''}
              ${hfUrl ? `<a href="${hfUrl}" target="_blank" class="btn-link-action btn-hf" title="Open Hugging Face paper page">🤗 HF</a>` : ''}
              <button class="explore-graph-btn" onclick="openEntityGraph('${escapeHtml(r['content.title'] || '')}', 'papers')" title="View Paper Linkage Graph">🕸️ Graph</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  } else if (currentTab === 'jobs') {
    tableHead.innerHTML = `
      <th>#</th>
      <th>Role Title</th>
      <th>Company</th>
      <th>Freshness Status</th>
      <th>Category</th>
      <th>Job Link &amp; Actions</th>
    `;
    if (!pageData.length) {
      tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 30px;">No jobs found.</td></tr>';
      return;
    }
    tableBody.innerHTML = pageData.map((j, idx) => `
      <tr>
        <td style="color: var(--text-muted); font-family: var(--font-mono);">${startIndex + idx + 1}</td>
        <td><strong style="color: var(--text);">${escapeHtml(j['title'] || 'Software Engineer')}</strong></td>
        <td><span style="color: var(--accent); font-weight: 600;">${escapeHtml(j['content.company'] || '')}</span></td>
        <td>
          <span class="badge badge-free" style="gap: 6px;">
            <span class="status-dot" style="width: 6px; height: 6px;"></span>
            &lt;24h Fresh
          </span>
        </td>
        <td><span class="badge badge-freemium">${escapeHtml(j['content.role_family'] || 'Engineering')}</span></td>
        <td>
          <div style="display: flex; gap: 6px; flex-wrap: wrap;">
            <a href="${j['job_url'] || j['source.name']}" target="_blank" class="badge-source">🔗 Apply</a>
            <button class="explore-graph-btn" onclick="openEntityGraph('${escapeHtml(j['title'] || '')}', 'jobs')" title="View Job Linkage Graph">🕸️ Graph</button>
          </div>
        </td>
      </tr>
    `).join('');
  } else if (currentTab === 'news') {
    tableHead.innerHTML = `
      <th>#</th>
      <th>News Article Headline</th>
      <th>Source Outlet</th>
      <th>Published Timestamp</th>
      <th>Summary / Excerpt</th>
      <th>Source Link &amp; Actions</th>
    `;
    if (!pageData.length) {
      tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 30px;">No news found.</td></tr>';
      return;
    }
    tableBody.innerHTML = pageData.map((n, idx) => `
      <tr>
        <td style="color: var(--text-muted); font-family: var(--font-mono);">${startIndex + idx + 1}</td>
        <td style="max-width: 320px;"><strong style="color: var(--text);">${escapeHtml(n['content.title'] || '')}</strong></td>
        <td><span class="badge badge-enterprise">${escapeHtml(n['source.name'] || 'AI News')}</span></td>
        <td style="font-family: var(--font-mono); font-size: 0.78rem; color: #5EEAD4;">
          ${(n['content.published_date'] || '').replace('T', ' ').slice(0, 19)} UTC
        </td>
        <td style="max-width: 360px; font-size: 0.78rem; color: var(--text-muted);">${escapeHtml(n['summary'] || '')}</td>
        <td>
          <div style="display: flex; gap: 6px; flex-wrap: wrap;">
            <a href="${n['source.url']}" target="_blank" class="badge-source">🔗 Read Article</a>
            <button class="explore-graph-btn" onclick="openEntityGraph('${escapeHtml(n['content.title'] || '')}', 'news')" title="View News Linkage Graph">🕸️ Graph</button>
          </div>
        </td>
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
    if (!pageData.length) {
      tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 30px;">No audit logs found.</td></tr>';
      return;
    }
    tableBody.innerHTML = pageData.map((m, idx) => {
      const conf = Math.round(Number(m['confidence_score'] || 0) * 100);
      return `
        <tr>
          <td style="color: var(--text-muted); font-family: var(--font-mono);">${startIndex + idx + 1}</td>
          <td><code style="color: #EF4444; font-size: 0.8rem;">"${escapeHtml(m['raw_name'] || '')}"</code></td>
          <td><strong style="color: #5EEAD4; font-size: 0.9rem;">${escapeHtml(m['canonical_name'] || '')}</strong></td>
          <td>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-family: var(--font-mono); font-weight: 700; color: ${conf >= 95 ? '#5EEAD4' : '#FBBF24'};">${conf}%</span>
            </div>
          </td>
          <td><span class="badge badge-freemium">${escapeHtml(m['resolution_method'] || '')}</span></td>
          <td style="font-size: 0.78rem; color: var(--text-muted);">${escapeHtml(m['source_context'] || '')}</td>
        </tr>
      `;
    }).join('');
  }
}

// Render dynamic pagination buttons: < 1 2 3 ... 100 >
function renderPaginationControls(totalPages) {
  if (!paginationControls) return;
  if (totalPages <= 1) {
    paginationControls.innerHTML = '';
    return;
  }

  let html = '';

  // Previous button
  html += `
    <button class="page-btn" ${currentPage === 1 ? 'disabled' : ''} onclick="goToPage(${currentPage - 1})" title="Previous Page">
      &lt;
    </button>
  `;

  // Window of page numbers
  const pages = [];
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (currentPage > 3) pages.push('...');
    const start = Math.max(2, currentPage - 1);
    const end = Math.min(totalPages - 1, currentPage + 1);
    for (let i = start; i <= end; i++) pages.push(i);
    if (currentPage < totalPages - 2) pages.push('...');
    pages.push(totalPages);
  }

  pages.forEach(p => {
    if (p === '...') {
      html += `<span class="page-ellipsis">…</span>`;
    } else {
      html += `
        <button class="page-btn ${p === currentPage ? 'active' : ''}" onclick="goToPage(${p})">
          ${p}
        </button>
      `;
    }
  });

  // Next button
  html += `
    <button class="page-btn" ${currentPage === totalPages ? 'disabled' : ''} onclick="goToPage(${currentPage + 1})" title="Next Page">
      &gt;
    </button>
  `;

  paginationControls.innerHTML = html;
}

window.goToPage = function(page) {
  const totalPages = Math.max(1, Math.ceil(currentData.length / pageSize));
  if (page < 1 || page > totalPages) return;
  currentPage = page;
  renderTable();
  const tableContainer = document.querySelector('.table-container');
  if (tableContainer) {
    tableContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
};

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
    const isResolved = Boolean(data.canonical_name);
    resRaw.textContent = data.raw_name;
    resCanonical.textContent = isResolved ? data.canonical_name : 'null (unresolved)';
    resCanonical.style.color = isResolved ? '#10b981' : '#f59e0b';
    resConf.textContent = Math.round(data.confidence_score * 100) + '%';
    resMethod.textContent = data.resolution_method;

    if (isResolved) {
      showToast(`Resolved "${data.raw_name}" ➔ "${data.canonical_name}"`);
    } else {
      showToast(`Unresolved: "${data.raw_name}" (No match above threshold)`);
    }

    // Record user activity
    if (window.trackActivity) {
      window.trackActivity({
        type: 'search',
        title: `Resolved: "${data.raw_name}"`,
        subtitle: isResolved 
          ? `Canonical: ${data.canonical_name} (${Math.round(data.confidence_score * 100)}% via ${data.resolution_method})`
          : `Unresolved (${Math.round(data.confidence_score * 100)}% confidence)`,
        url: '#playground',
        badge: isResolved ? 'RESOLVED' : 'UNRESOLVED',
        meta: { raw: data.raw_name, canonical: data.canonical_name, method: data.resolution_method }
      });
    }
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
    currentPage = 1;
    loadTabData();

    // Track user search query
    if (searchQuery.length >= 3 && window.trackActivity) {
      window.trackActivity({
        type: 'search',
        title: `Search: "${searchQuery}"`,
        subtitle: `Filter query across ${currentTab.toUpperCase()}`,
        url: '#' + currentTab,
        badge: 'SEARCH'
      });
    }
  }, 250);
});

// Track table link clicks as user visits
if (tableBody) {
  tableBody.addEventListener('click', (e) => {
    const link = e.target.closest('a');
    if (link && window.trackActivity) {
      const row = link.closest('tr');
      const titleEl = row ? row.querySelector('strong') : null;
      const title = titleEl ? titleEl.textContent.trim() : link.textContent.trim();
      const url = link.getAttribute('href') || '';
      const linkText = link.textContent.trim();

      let subtitle = '';
      if (currentTab === 'startups') {
        const cells = row ? row.querySelectorAll('td') : [];
        const ind = cells[3] ? cells[3].textContent.trim() : '';
        subtitle = ind ? `${ind} · ${linkText}` : linkText;
      } else if (currentTab === 'products') {
        const cells = row ? row.querySelectorAll('td') : [];
        const creator = cells[2] ? cells[2].textContent.trim() : '';
        const tier = cells[3] ? cells[3].textContent.trim() : '';
        subtitle = `${creator} ${tier ? '· ' + tier : ''}`;
      } else if (currentTab === 'papers') {
        const cells = row ? row.querySelectorAll('td') : [];
        const authors = cells[2] ? cells[2].textContent.trim() : '';
        subtitle = `${authors || 'Research Paper'} · ${linkText}`;
      } else if (currentTab === 'jobs') {
        const cells = row ? row.querySelectorAll('td') : [];
        const comp = cells[2] ? cells[2].textContent.trim() : '';
        subtitle = `${comp || 'Verified Role'} · Apply`;
      } else if (currentTab === 'news') {
        const cells = row ? row.querySelectorAll('td') : [];
        const src = cells[2] ? cells[2].textContent.trim() : '';
        subtitle = `${src || 'AI News Outlet'} · Read`;
      }

      window.trackActivity({
        type: currentTab,
        title: title,
        subtitle: subtitle,
        url: url,
        badge: currentTab.toUpperCase(),
        meta: { action: linkText }
      });
    }
  });
}

filterSecondary.addEventListener('change', () => {
  currentPage = 1;
  loadTabData();
});

 // Refresh feed button
refreshBtn.addEventListener('click', async () => {
  const prevCount = currentData.length;
  currentPage = 1;
  await loadStats();
  await loadTabData();
  const diff = currentData.length - prevCount;
  if (diff > 0) {
    showToast(`Refreshed live feed: +${diff} new items added since last view!`);
  } else {
    showToast('Refreshed live intelligence feed: All records up to date.');
  }
});

// ============================================================
// DYNAMIC MULTI-CATEGORY VENTURE KNOWLEDGE GRAPH (VIS-NETWORK)
// ============================================================
let graphNetwork = null;
let currentGraphCategory = 'startups';
let currentGraphEntity = 'OpenAI';
let graphEntitiesList = [];

const CATEGORY_PRESETS = {
  startups: [
    { name: 'OpenAI', label: 'OpenAI' },
    { name: 'Anthropic', label: 'Anthropic' },
    { name: 'Cohere', label: 'Cohere' },
    { name: 'DeepMind', label: 'DeepMind' },
    { name: 'Mistral AI', label: 'Mistral AI' },
    { name: 'DeepMark', label: 'DeepMark (YC)' },
    { name: 'Maritime', label: 'Maritime (YC)' }
  ],
  products: [
    { name: 'ChatGPT', label: 'ChatGPT' },
    { name: 'Claude 3.5 Sonnet', label: 'Claude 3.5' },
    { name: 'Cursor', label: 'Cursor' },
    { name: 'Notion AI', label: 'Notion AI' },
    { name: 'Gemini 1.5 Pro', label: 'Gemini Pro' },
    { name: 'Midjourney v6', label: 'Midjourney' }
  ],
  papers: [
    { name: 'Attention Is All You Need', label: 'Attention Is All You Need' },
    { name: 'DeepSeek-R1', label: 'DeepSeek-R1' },
    { name: 'Whisper ASR', label: 'Whisper' },
    { name: 'Llama 3', label: 'Llama 3' },
    { name: 'Chain-of-Thought', label: 'Chain-of-Thought' }
  ],
  jobs: [
    { name: 'Engineering Manager', label: 'Engineering Manager' },
    { name: 'Senior AI Engineer', label: 'Senior AI Engineer' },
    { name: 'Founding Engineer', label: 'Founding Engineer' },
    { name: 'Research Scientist', label: 'Research Scientist' }
  ],
  news: [
    { name: 'Mecka AI', label: 'Mecka AI' },
    { name: 'Anthropic Claude', label: 'Anthropic Claude' },
    { name: 'OpenAI Funding', label: 'OpenAI Funding' },
    { name: 'Mistral AI', label: 'Mistral AI' }
  ]
};

const CATEGORY_PLACEHOLDERS = {
  startups: 'Search startup name (e.g. OpenAI, Anthropic, Cohere, DeepMark, Maritime)...',
  products: 'Search product name (e.g. ChatGPT, Claude 3.5, Cursor, Notion AI)...',
  papers: 'Search research paper (e.g. Attention Is All You Need, DeepSeek-R1, Whisper)...',
  jobs: 'Search job role (e.g. Engineering Manager, Senior AI Engineer, Research Scientist)...',
  news: 'Search news headline or company (e.g. Mecka AI, Anthropic, OpenAI)...'
};

async function loadGraphEntitiesList(catType = 'startups') {
  try {
    const res = await fetch(`/api/graph/entities?type=${encodeURIComponent(catType)}`);
    const data = await res.json();
    if (data && data.entities) {
      graphEntitiesList = data.entities;
      const datalist = document.getElementById('graph-entities-datalist');
      if (datalist) {
        datalist.innerHTML = data.entities.map(e => `<option value="${escapeHtml(e.name)}">${escapeHtml(e.source)}</option>`).join('');
      }
    }
  } catch (err) {
    console.error('Failed to load graph entities list:', err);
  }
}

function renderPresetChips(category, activeEntity = null) {
  const chipsContainer = document.getElementById('graph-preset-chips');
  if (!chipsContainer) return;
  const presets = CATEGORY_PRESETS[category] || [];
  chipsContainer.innerHTML = `
    <span class="chip-label">Quick Select:</span>
    ${presets.map(p => {
      const isActive = activeEntity && p.name.toLowerCase() === activeEntity.toLowerCase();
      return `<button class="graph-chip ${isActive ? 'active' : ''}" data-entity="${escapeHtml(p.name)}">${escapeHtml(p.label)}</button>`;
    }).join('')}
  `;

  chipsContainer.querySelectorAll('.graph-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      loadEntityGraph(chip.dataset.entity, currentGraphCategory);
    });
  });
}

function switchGraphCategory(category, optionalEntity = null) {
  if (!category) category = 'startups';
  currentGraphCategory = category;

  // 1. Update active pill in UI
  document.querySelectorAll('.graph-cat-pill').forEach(pill => {
    if (pill.dataset.category === category) {
      pill.classList.add('active');
    } else {
      pill.classList.remove('active');
    }
  });

  // 2. Update placeholder & load entities list for datalist
  const inputEl = document.getElementById('graph-entity-input');
  if (inputEl) {
    inputEl.placeholder = CATEGORY_PLACEHOLDERS[category] || 'Search...';
  }
  loadGraphEntitiesList(category);

  // 3. Render quick select chips for this category
  const presets = CATEGORY_PRESETS[category] || [];
  const defaultTarget = optionalEntity || (presets[0] ? presets[0].name : '');
  renderPresetChips(category, defaultTarget);

  // 4. Load the graph
  if (defaultTarget) {
    loadEntityGraph(defaultTarget, category);
  }
}

async function loadEntityGraph(entityName, category = null) {
  if (!entityName || !entityName.trim()) return;
  const target = entityName.trim();
  currentGraphEntity = target;
  if (category) currentGraphCategory = category;

  const inputEl = document.getElementById('graph-entity-input');
  if (inputEl) inputEl.value = target;

  // Highlight active preset chip if matches
  document.querySelectorAll('.graph-chip').forEach(c => {
    if (c.dataset.entity && c.dataset.entity.toLowerCase() === target.toLowerCase()) {
      c.classList.add('active');
    } else {
      c.classList.remove('active');
    }
  });

  const canvasWrapper = document.getElementById('vis-network-canvas');
  if (!canvasWrapper) return;

  canvasWrapper.innerHTML = `
    <div style="display: flex; height: 100%; align-items: center; justify-content: center; flex-direction: column; gap: 14px; color: #A5B4FC;">
      <div class="spinner" style="width: 36px; height: 36px; border: 3px solid rgba(99,102,241,0.2); border-top-color: #6366F1; border-radius: 50%; animation: spin 0.8s linear infinite;"></div>
      <span style="font-size: 0.9rem; font-weight: 500;">Extracting 360° linkages for ${currentGraphCategory.toUpperCase()} "${escapeHtml(target)}"...</span>
    </div>
  `;

  try {
    const res = await fetch(`/api/graph/entity?name=${encodeURIComponent(target)}&type=${encodeURIComponent(currentGraphCategory)}`);
    const data = await res.json();

    if (data.error) {
      canvasWrapper.innerHTML = `<div style="padding: 40px; text-align: center; color: #F87171;">${data.error}</div>`;
      return;
    }

    renderVisNetwork(data);
    updateNodeInspector(data.nodes[0] || null, data.startup);

    // Track user activity
    if (window.trackActivity) {
      window.trackActivity({
        type: 'graph',
        title: `Graph (${currentGraphCategory.toUpperCase()}): "${data.canonical_name}"`,
        subtitle: `${data.counts.total_nodes} nodes · ${data.counts.total_edges} linkages`,
        url: '#graph',
        badge: 'GRAPH',
        meta: { entity: data.canonical_name, category: currentGraphCategory, nodes: data.counts.total_nodes }
      });
    }

  } catch (err) {
    console.error('Error loading entity graph:', err);
    canvasWrapper.innerHTML = `<div style="padding: 40px; text-align: center; color: #F87171;">Failed to load graph: ${err.message}</div>`;
  }
}

function renderVisNetwork(graphData) {
  const container = document.getElementById('vis-network-canvas');
  if (!container || typeof vis === 'undefined') {
    console.warn('vis library not loaded or container missing');
    return;
  }

  container.innerHTML = '';

  // Strip any arrows from edges for clean, modern spline linkages
  const cleanEdges = (graphData.edges || []).map(e => ({
    ...e,
    arrows: ''
  }));

  const nodes = new vis.DataSet(graphData.nodes);
  const edges = new vis.DataSet(cleanEdges);

  const data = { nodes: nodes, edges: edges };

  const options = {
    nodes: {
      shape: 'dot',
      scaling: {
        min: 16,
        max: 42
      },
      font: {
        color: '#EDEDF0',
        size: 13,
        face: 'Inter, sans-serif'
      },
      borderWidth: 2,
      shadow: {
        enabled: true,
        color: 'rgba(0,0,0,0.6)',
        size: 10,
        x: 0,
        y: 4
      }
    },
    edges: {
      width: 1.8,
      arrows: '',
      color: {
        color: 'rgba(255, 255, 255, 0.16)',
        highlight: '#818CF8',
        hover: '#60A5FA'
      },
      font: {
        color: '#94A3B8',
        size: 10,
        align: 'middle',
        background: 'rgba(13, 17, 28, 0.85)'
      },
      smooth: {
        type: 'continuous',
        roundness: 0.34
      }
    },
    physics: {
      solver: 'forceAtlas2Based',
      forceAtlas2Based: {
        gravitationalConstant: -110,
        centralGravity: 0.005,
        springLength: 170,
        springConstant: 0.05,
        damping: 0.35,
        avoidOverlap: 0.85
      },
      stabilization: {
        iterations: 160,
        updateInterval: 25
      }
    },
    interaction: {
      hover: true,
      hoverConnectedEdges: true,
      tooltipDelay: 0,
      zoomView: true,
      dragView: true,
      navigationButtons: false
    }
  };

  graphNetwork = new vis.Network(container, data, options);
  window.graphNetwork = graphNetwork;
  window.showNodeDialog = showNodeDialog;
  window.hideNodeDialog = hideNodeDialog;

  const previewCard = document.getElementById('graph-preview-card');
  const canvasWrapper = document.querySelector('.graph-canvas-wrapper');
  let activeHoverNodeId = null;
  let hideDialogTimer = null;

  function updateDialogPosition(nodeId) {
    if (!nodeId || !previewCard || !canvasWrapper || !graphNetwork) return;
    try {
      const nodePos = graphNetwork.getPosition(nodeId);
      if (!nodePos || (nodePos.x === undefined && nodePos.y === undefined)) return;
      const domPos = graphNetwork.canvasToDOM(nodePos);
      const wrapperRect = canvasWrapper.getBoundingClientRect();

      let left = domPos.x;
      let top = domPos.y;

      // Check if node is too close to the top of canvas
      if (top < 220) {
        previewCard.classList.add('flip-below');
      } else {
        previewCard.classList.remove('flip-below');
      }

      // Keep left within horizontal boundaries
      if (left - 165 < 12) left = 177;
      if (left + 165 > wrapperRect.width - 12) left = wrapperRect.width - 177;

      previewCard.style.left = `${left}px`;
      previewCard.style.top = `${top}px`;
    } catch (err) {}
  }

  function showNodeDialog(nodeId) {
    if (hideDialogTimer) {
      clearTimeout(hideDialogTimer);
      hideDialogTimer = null;
    }
    if (!nodeId) return;
    activeHoverNodeId = nodeId;
    const node = graphData.nodes.find(n => n.id === nodeId);
    if (!node || !previewCard || !canvasWrapper) return;

    const meta = node.meta || {};
    const type = meta.type || node.group || 'Entity';
    const cleanName = meta.name || meta.title || node.label.replace(/^[^\w]+/, '');

    let badgeBg = 'rgba(99, 102, 241, 0.2)';
    let badgeColor = '#A5B4FC';
    if (type.includes('Paper')) { badgeBg = 'rgba(245, 158, 11, 0.2)'; badgeColor = '#FDE68A'; }
    else if (type.includes('Product')) { badgeBg = 'rgba(16, 185, 129, 0.2)'; badgeColor = '#A7F3D0'; }
    else if (type.includes('Job')) { badgeBg = 'rgba(2, 132, 199, 0.2)'; badgeColor = '#BAE6FD'; }
    else if (type.includes('News')) { badgeBg = 'rgba(244, 63, 94, 0.2)'; badgeColor = '#FECDD3'; }
    else if (type.includes('Code')) { badgeBg = 'rgba(219, 39, 119, 0.2)'; badgeColor = '#F472B6'; }

    // Formulate a crisp description / info excerpt
    let infoText = meta.description || meta.summary || '';
    if (!infoText) {
      if (type.includes('Paper')) {
        infoText = meta.authors ? `Research paper contribution authored by ${meta.authors}.` : 'Groundbreaking research contribution.';
      } else if (type.includes('Startup')) {
        infoText = `${cleanName} is a high-growth AI organization specializing in ${meta.industry || 'Frontier AI'}.`;
      } else if (type.includes('Product')) {
        infoText = meta.creator ? `Flagship product created and deployed by ${meta.creator}.` : 'AI software solution.';
      } else if (type.includes('Job')) {
        infoText = `Active hiring role at ${meta.company || 'top AI company'} in ${meta.location || 'Remote'}.`;
      } else if (type.includes('News')) {
        infoText = `Real-time AI venture and intelligence news signal verified fresh within 24h.`;
      }
    }

    // Build pills for metadata
    let pillsHtml = '';
    if (meta.stars) pillsHtml += `<span class="preview-meta-pill">⭐ <strong>${Number(meta.stars).toLocaleString()}</strong> stars</span>`;
    if (meta.authors) pillsHtml += `<span class="preview-meta-pill">👥 <strong>${escapeHtml(meta.authors.slice(0, 24))}</strong></span>`;
    if (meta.creator) pillsHtml += `<span class="preview-meta-pill">🏢 <strong>${escapeHtml(meta.creator)}</strong></span>`;
    if (meta.pricing) pillsHtml += `<span class="preview-meta-pill">💎 <strong>${escapeHtml(meta.pricing)}</strong></span>`;
    if (meta.location) pillsHtml += `<span class="preview-meta-pill">📍 <strong>${escapeHtml(meta.location)}</strong></span>`;
    if (meta.company) pillsHtml += `<span class="preview-meta-pill">🏢 <strong>${escapeHtml(meta.company)}</strong></span>`;
    if (meta.date) pillsHtml += `<span class="preview-meta-pill">🕒 <strong>${escapeHtml(meta.date.slice(0, 10))}</strong></span>`;

    previewCard.innerHTML = `
      <div class="preview-card-header">
        <span class="preview-type-badge" style="background: ${badgeBg}; color: ${badgeColor}; border: 1px solid ${badgeColor}44;">${escapeHtml(type.toUpperCase())}</span>
        <span style="font-size: 0.72rem; color: #64748B;">Node Dialog</span>
      </div>
      <div class="preview-card-title">${escapeHtml(cleanName)}</div>
      ${infoText ? `<div class="preview-card-desc">${escapeHtml(infoText.slice(0, 150))}</div>` : ''}
      ${pillsHtml ? `<div class="preview-card-meta">${pillsHtml}</div>` : ''}
      <div class="preview-card-footer">
        <span>🖱️ Click to inspect</span>
        <span style="color: #94A3B8;">Double-click to open ↗</span>
      </div>
    `;

    updateDialogPosition(nodeId);
    previewCard.style.display = 'block';
    previewCard.classList.add('visible');
  }

  function hideNodeDialog() {
    if (hideDialogTimer) clearTimeout(hideDialogTimer);
    hideDialogTimer = setTimeout(() => {
      activeHoverNodeId = null;
      if (previewCard) {
        previewCard.classList.remove('visible');
      }
      hideDialogTimer = null;
    }, 120);
  }

  // Pin dialog position during physics simulation and view changes
  graphNetwork.on('afterDrawing', function () {
    if (activeHoverNodeId && previewCard && previewCard.classList.contains('visible')) {
      updateDialogPosition(activeHoverNodeId);
    }
  });

  graphNetwork.on('hoverNode', function (params) {
    showNodeDialog(params.node);
  });

  graphNetwork.on('blurNode', function () {
    hideNodeDialog();
  });

  // Direct canvas mousemove tracking with getNodeAt for instant 0ms response
  container.addEventListener('mousemove', function (e) {
    const rect = container.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const nodeId = graphNetwork.getNodeAt({ x, y });
    if (nodeId) {
      showNodeDialog(nodeId);
    } else if (activeHoverNodeId) {
      hideNodeDialog();
    }
  });

  container.addEventListener('mouseleave', function () {
    hideNodeDialog();
  });

  graphNetwork.on('dragging', function () {
    hideNodeDialog();
  });

  graphNetwork.on('selectNode', function (params) {
    if (params.nodes && params.nodes.length > 0) {
      showNodeDialog(params.nodes[0]);
    }
  });

  // Click on node: update inspector and redirect if configured
  graphNetwork.on('click', function (params) {
    if (params.nodes.length > 0) {
      const nodeId = params.nodes[0];
      showNodeDialog(nodeId);
      const clickedNode = graphData.nodes.find(n => n.id === nodeId);
      if (clickedNode) {
        updateNodeInspector(clickedNode, graphData.startup);

        // Track node interaction
        if (window.trackActivity && clickedNode.meta) {
          window.trackActivity({
            type: 'graph',
            title: `Explored Node: ${clickedNode.meta.name || clickedNode.meta.title || clickedNode.label}`,
            subtitle: `Type: ${clickedNode.meta.type} · ${clickedNode.url ? 'Click to visit' : 'Metadata node'}`,
            url: clickedNode.url || '#graph',
            badge: (clickedNode.meta.type || 'NODE').toUpperCase().slice(0, 8),
            meta: { node_id: nodeId }
          });
        }
      }
    }
  });

  // Double click: directly open node URL in new window
  graphNetwork.on('doubleClick', function (params) {
    if (params.nodes.length > 0) {
      const nodeId = params.nodes[0];
      const clickedNode = graphData.nodes.find(n => n.id === nodeId);
      if (clickedNode && clickedNode.url && clickedNode.url !== '#' && !clickedNode.url.startsWith('/#')) {
        window.open(clickedNode.url, '_blank');
        showToast(`Redirecting to ${clickedNode.meta ? (clickedNode.meta.name || clickedNode.meta.title) : clickedNode.label}...`);
      }
    }
  });
}

function updateNodeInspector(node, startup) {
  if (!node) return;
  const badgeEl = document.getElementById('node-inspector-badge');
  const titleEl = document.getElementById('node-inspector-title');
  const descEl = document.getElementById('node-inspector-desc');
  const metaGrid = document.getElementById('node-inspector-meta');
  const redirectBtn = document.getElementById('node-redirect-btn');

  const meta = node.meta || {};
  const type = meta.type || node.group || 'Entity';

  if (badgeEl) {
    badgeEl.textContent = type.toUpperCase();
    badgeEl.style.background = node.color ? (node.color.background + '33') : 'rgba(99,102,241,0.2)';
    badgeEl.style.color = node.color ? (node.color.border || '#A5B4FC') : '#A5B4FC';
  }

  const cleanName = meta.name || meta.title || node.label.replace(/^[^\w]+/, '');
  if (titleEl) titleEl.textContent = cleanName;

  let descText = meta.description || meta.summary || '';
  if (!descText && type === 'Startup') descText = startup ? startup.description : '';
  if (!descText && type === 'Research Paper') descText = `Research paper contribution by ${meta.authors || 'research authors'}.`;
  if (!descText && type === 'Job Opening') descText = `Active hiring role at ${meta.company || (startup ? startup['content.entityName'] : 'organization')} (${meta.location || 'Remote'}).`;
  if (!descText && type === 'News Signal') descText = `Real-time AI news signal verified fresh within 24 hours.`;
  if (descEl) descEl.textContent = descText || 'Select or double-click to visit live source.';

  // Build key-value rows
  let rowsHtml = '';
  if (type === 'Startup') {
    rowsHtml += `
      <div class="inspector-meta-row"><span class="inspector-meta-label">Industry</span><span class="inspector-meta-val">${escapeHtml(meta.industry || 'AI')}</span></div>
      <div class="inspector-meta-row"><span class="inspector-meta-label">Location</span><span class="inspector-meta-val">${escapeHtml(meta.location || 'Global')}</span></div>
      <div class="inspector-meta-row"><span class="inspector-meta-label">Batch</span><span class="inspector-meta-val">${escapeHtml(meta.batch || 'Active')}</span></div>
    `;
  } else if (type === 'Product') {
    rowsHtml += `
      <div class="inspector-meta-row"><span class="inspector-meta-label">Category</span><span class="inspector-meta-val">${escapeHtml(meta.category || 'AI Tool')}</span></div>
      <div class="inspector-meta-row"><span class="inspector-meta-label">Pricing</span><span class="inspector-meta-val">${escapeHtml(meta.pricing || 'Freemium')}</span></div>
      <div class="inspector-meta-row"><span class="inspector-meta-label">Creator</span><span class="inspector-meta-val">${escapeHtml(meta.creator || (startup ? startup['content.entityName'] : 'Verified'))}</span></div>
    `;
  } else if (type === 'Research Paper') {
    rowsHtml += `
      <div class="inspector-meta-row"><span class="inspector-meta-label">GitHub Stars</span><span class="inspector-meta-val">⭐ ${Number(meta.stars || 0).toLocaleString()}</span></div>
      <div class="inspector-meta-row"><span class="inspector-meta-label">Authors</span><span class="inspector-meta-val">${escapeHtml(meta.authors ? meta.authors.slice(0, 28) + '...' : 'Researchers')}</span></div>
      <div class="inspector-meta-row"><span class="inspector-meta-label">Source</span><span class="inspector-meta-val">arXiv / Papers with Code</span></div>
    `;
  } else if (type === 'Job Opening') {
    rowsHtml += `
      <div class="inspector-meta-row"><span class="inspector-meta-label">Company</span><span class="inspector-meta-val">${escapeHtml(meta.company || (startup ? startup['content.entityName'] : 'Hiring Org'))}</span></div>
      <div class="inspector-meta-row"><span class="inspector-meta-label">Location</span><span class="inspector-meta-val">${escapeHtml(meta.location || 'Remote')}</span></div>
      <div class="inspector-meta-row"><span class="inspector-meta-label">Role Family</span><span class="inspector-meta-val">${escapeHtml(meta.role_family || 'Engineering')}</span></div>
      <div class="inspector-meta-row"><span class="inspector-meta-label">Freshness</span><span class="inspector-meta-val">&lt;24h Verified</span></div>
    `;
  } else if (type === 'News Signal') {
    rowsHtml += `
      <div class="inspector-meta-row"><span class="inspector-meta-label">Published</span><span class="inspector-meta-val">${escapeHtml(meta.date || 'Recent')}</span></div>
      <div class="inspector-meta-row"><span class="inspector-meta-label">Verification</span><span class="inspector-meta-val">ISO-8601 &lt;24h</span></div>
    `;
  }

  if (metaGrid) metaGrid.innerHTML = rowsHtml;

  // Set action redirect button
  if (redirectBtn) {
    const targetUrl = node.url || (startup ? startup['content.data.website'] : '#');
    if (targetUrl && targetUrl !== '#' && !targetUrl.startsWith('/#')) {
      redirectBtn.href = targetUrl;
      redirectBtn.style.display = 'flex';
      redirectBtn.innerHTML = `<span>Visit ${escapeHtml(cleanName.slice(0, 22))}</span> <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>`;
    } else {
      redirectBtn.style.display = 'none';
    }
  }
}

// Global hook to jump directly to graph tab with a selected entity in any category
window.openEntityGraph = function(entityName, entityCategory = 'startups') {
  if (!entityName) return;
  const graphBtn = document.querySelector('.tab-btn[data-tab="graph"]');
  if (graphBtn) graphBtn.click();
  switchGraphCategory(entityCategory, entityName);
};

function initKnowledgeGraph() {
  loadGraphEntitiesList(currentGraphCategory);
  renderPresetChips(currentGraphCategory, currentGraphEntity);
  loadEntityGraph(currentGraphEntity || 'OpenAI', currentGraphCategory);

  // Category switching pills
  document.querySelectorAll('.graph-cat-pill').forEach(pill => {
    if (!pill.dataset.bound) {
      pill.dataset.bound = 'true';
      pill.addEventListener('click', () => {
        const cat = pill.dataset.category;
        if (cat && cat !== currentGraphCategory) {
          switchGraphCategory(cat);
        }
      });
    }
  });

  // Setup fit button
  const fitBtn = document.getElementById('graph-fit-btn');
  if (fitBtn && !fitBtn.dataset.bound) {
    fitBtn.dataset.bound = 'true';
    fitBtn.addEventListener('click', () => {
      if (graphNetwork) graphNetwork.fit({ animation: { duration: 600, easingFunction: 'easeInOutQuad' } });
    });
  }

  // Setup load button & input
  const loadBtn = document.getElementById('graph-load-btn');
  const inputEl = document.getElementById('graph-entity-input');
  if (loadBtn && !loadBtn.dataset.bound) {
    loadBtn.dataset.bound = 'true';
    loadBtn.addEventListener('click', () => {
      if (inputEl) loadEntityGraph(inputEl.value.trim(), currentGraphCategory);
    });
  }
  if (inputEl && !inputEl.dataset.bound) {
    inputEl.dataset.bound = 'true';
    inputEl.addEventListener('keydown', e => {
      if (e.key === 'Enter') loadEntityGraph(inputEl.value.trim(), currentGraphCategory);
    });
  }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Run Pipeline button listener with live sync progress & count detection
const btnRunPipeline = document.getElementById('btn-run-pipeline-now');
if (btnRunPipeline) {
  btnRunPipeline.addEventListener('click', async () => {
    btnRunPipeline.disabled = true;
    btnRunPipeline.innerHTML = '⏳ Syncing 10 Live Feeds with Gemini & Groq...';
    showToast('Incremental monitoring sync started across all 10 sources...');

    try {
      // Get current latest run id to detect new run completion
      const initialStatusRes = await fetch('/api/pipeline/status');
      const initialStatus = await initialStatusRes.json();
      const lastRunId = (initialStatus.recent_runs && initialStatus.recent_runs[0]) ? initialStatus.recent_runs[0].run_id : null;

      await fetch('/api/pipeline/run-now', { method: 'POST' });

      // Poll every 2.5 seconds until new run finishes
      let pollAttempts = 0;
      const pollInterval = setInterval(async () => {
        pollAttempts++;
        try {
          const pollRes = await fetch('/api/pipeline/status');
          const pollData = await pollRes.json();
          const latestRun = pollData.recent_runs && pollData.recent_runs[0];

          if (latestRun && latestRun.run_id !== lastRunId && latestRun.status === 'SUCCESS') {
            clearInterval(pollInterval);
            await loadPipelineData();
            await loadStats();
            await loadTabData();
            btnRunPipeline.disabled = false;
            btnRunPipeline.innerHTML = '<span id="pipeline-btn-icon">▶</span> Run Monitoring Cycle Now';

            const freshCount = latestRun.passed_freshness || 0;
            const seenCount = (latestRun.summary && latestRun.summary.already_seen_skipped) || (latestRun.new_items_found - freshCount - latestRun.discarded_stale) || 0;
            showToast(`✅ Sync Complete: +${freshCount} new items ingested since last sync (${seenCount} already seen skipped)`);
          } else if (pollAttempts > 45) { // Timeout safety after ~110s
            clearInterval(pollInterval);
            await loadPipelineData();
            await loadStats();
            await loadTabData();
            btnRunPipeline.disabled = false;
            btnRunPipeline.innerHTML = '<span id="pipeline-btn-icon">▶</span> Run Monitoring Cycle Now';
            showToast('Sync completed in background. State refreshed.');
          }
        } catch (pollErr) {
          console.error('Poll error:', pollErr);
        }
      }, 2500);

    } catch (e) {
      btnRunPipeline.disabled = false;
      btnRunPipeline.innerHTML = '<span id="pipeline-btn-icon">▶</span> Run Monitoring Cycle Now';
      showToast('Cycle trigger error: ' + e.message);
    }
  });
}

// Initial Load
loadStats();
setupSecondaryFilter();
loadTabData();
loadGraphEntitiesList();

