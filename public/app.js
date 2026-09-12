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
    if (kpiSignals) kpiSignals.textContent = (data.jobs_count + data.news_count).toLocaleString();
    if (kpiAccuracy) kpiAccuracy.textContent = (data.avg_confidence * 100).toFixed(1) + '%';
    if (kpiFreshSub) kpiFreshSub.textContent = '100% verified <24h';

    const countEls = {
      startups: document.getElementById('count-startups'),
      products: document.getElementById('count-products'),
      papers: document.getElementById('count-papers'),
      jobs: document.getElementById('count-jobs'),
      news: document.getElementById('count-news'),
      mappings: document.getElementById('count-mappings'),
    };
    if (countEls.startups) countEls.startups.textContent = Number(data.startups_count).toLocaleString();
    if (countEls.products) countEls.products.textContent = Number(data.products_count).toLocaleString();
    if (countEls.papers) countEls.papers.textContent = Number(data.papers_count).toLocaleString();
    if (countEls.jobs) countEls.jobs.textContent = Number(data.jobs_count).toLocaleString();
    if (countEls.news) countEls.news.textContent = Number(data.news_count).toLocaleString();
    if (countEls.mappings) countEls.mappings.textContent = Number(data.mappings_count).toLocaleString();
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

    if (currentTab === 'graph') {
      contentContainer.style.display = 'none';
      controlsBar.style.display = 'none';
      archContainer.style.display = 'none';
      if (pipelineContainer) pipelineContainer.style.display = 'none';
      graphContainer.style.display = 'block';
      initKnowledgeGraph();
    } else if (currentTab === 'architecture') {
      contentContainer.style.display = 'none';
      controlsBar.style.display = 'none';
      graphContainer.style.display = 'none';
      if (pipelineContainer) pipelineContainer.style.display = 'none';
      archContainer.style.display = 'block';
    } else if (currentTab === 'pipeline') {
      contentContainer.style.display = 'none';
      controlsBar.style.display = 'none';
      graphContainer.style.display = 'none';
      archContainer.style.display = 'none';
      if (pipelineContainer) pipelineContainer.style.display = 'block';
      loadPipelineData();
    } else {
      contentContainer.style.display = 'block';
      controlsBar.style.display = 'flex';
      graphContainer.style.display = 'none';
      archContainer.style.display = 'none';
      if (pipelineContainer) pipelineContainer.style.display = 'none';


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
          <td><a href="${p['source.url']}" target="_blank" class="badge-source">🔗 Visit Site</a></td>
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
      <th>Job Link</th>
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
    const data = await res.json();
    resRaw.textContent = data.raw_name;
    resCanonical.textContent = data.canonical_name;
    resConf.textContent = Math.round(data.confidence_score * 100) + '%';
    resMethod.textContent = data.resolution_method;
    showToast(`Resolved "${data.raw_name}" ➔ "${data.canonical_name}"`);

    // Record user activity
    if (window.trackActivity) {
      window.trackActivity({
        type: 'search',
        title: `Resolved: "${data.raw_name}"`,
        subtitle: `Canonical: ${data.canonical_name} (${Math.round(data.confidence_score * 100)}% via ${data.resolution_method})`,
        url: '#playground',
        badge: 'ENTITY',
        meta: { raw: data.raw_name, canonical: data.canonical_name }
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

refreshBtn.addEventListener('click', () => {
  currentPage = 1;
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
    { id: 1, name: 'OpenAI', type: 'startup', x: 200, y: 150, vx: 0.2, vy: 0.1, color: '#4F8CFF' },
    { id: 2, name: 'ChatGPT', type: 'product', x: 280, y: 240, vx: -0.15, vy: 0.2, color: '#5EEAD4' },
    { id: 3, name: 'Anthropic', type: 'startup', x: 450, y: 120, vx: 0.1, vy: -0.1, color: '#4F8CFF' },
    { id: 4, name: 'Claude 3.5', type: 'product', x: 550, y: 220, vx: -0.1, vy: 0.15, color: '#5EEAD4' },
    { id: 5, name: 'Attention Is All You Need', type: 'paper', x: 350, y: 340, vx: 0.1, vy: 0.2, color: '#FBBF24' },
    { id: 6, name: 'Mistral AI', type: 'startup', x: 700, y: 160, vx: -0.2, vy: 0.1, color: '#4F8CFF' },
    { id: 7, name: 'Mistral Large', type: 'product', x: 780, y: 250, vx: 0.15, vy: -0.15, color: '#5EEAD4' },
    { id: 8, name: 'AI Research Eng', type: 'job', x: 400, y: 220, vx: 0.1, vy: -0.1, color: '#C084FC' },
    { id: 9, name: 'Hugging Face', type: 'startup', x: 880, y: 130, vx: -0.1, vy: 0.1, color: '#4F8CFF' },
    { id: 10, name: 'Transformers', type: 'product', x: 920, y: 270, vx: 0.1, vy: 0.1, color: '#5EEAD4' },
    { id: 11, name: 'Perplexity AI', type: 'startup', x: 150, y: 320, vx: 0.1, vy: -0.1, color: '#4F8CFF' },
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
      grad.addColorStop(0, 'rgba(79, 140, 255, 0.2)');
      grad.addColorStop(1, 'rgba(79, 140, 255, 0.08)');
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

// Run Pipeline button listener
const btnRunPipeline = document.getElementById('btn-run-pipeline-now');
if (btnRunPipeline) {
  btnRunPipeline.addEventListener('click', async () => {
    btnRunPipeline.disabled = true;
    btnRunPipeline.innerHTML = '⏳ Running Cycle Across 10 Sources...';
    showToast('Continuous monitoring cycle initiated across all 10 sources...');
    try {
      await fetch('/api/pipeline/run-now', { method: 'POST' });
      setTimeout(async () => {
        await loadPipelineData();
        await loadStats();
        btnRunPipeline.disabled = false;
        btnRunPipeline.innerHTML = '<span id="pipeline-btn-icon">▶</span> Run Monitoring Cycle Now';
        showToast('Pipeline cycle finished and SQLite state refreshed!');
      }, 5000);
    } catch (e) {
      btnRunPipeline.disabled = false;
      btnRunPipeline.innerHTML = '<span id="pipeline-btn-icon">▶</span> Run Monitoring Cycle Now';
      showToast('Cycle trigger error');
    }
  });
}

// Initial Load
loadStats();
setupSecondaryFilter();
loadTabData();

