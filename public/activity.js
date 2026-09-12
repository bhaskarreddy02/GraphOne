// Activity Page Logic - Side-by-side switching bars & recently viewed items

let activeCategory = 'all';
let activeTime = 'all';
let searchFilter = '';

const activeCategoryTitle = document.getElementById('active-category-title');
const activeCategoryCount = document.getElementById('active-category-count');
const activeFilterDesc = document.getElementById('active-filter-desc');
const recentlyViewedList = document.getElementById('recently-viewed-list');
const activitySearchInput = document.getElementById('activity-search-input');
const resetFilterBtn = document.getElementById('activity-reset-filter');
const btnClearActivity = document.getElementById('btn-clear-activity');
const btnExportActivity = document.getElementById('btn-export-activity');

const statTotalVisits = document.getElementById('stat-total-visits');
const statTodayVisits = document.getElementById('stat-today-visits');
const statTopCategory = document.getElementById('stat-top-category');

// Category icons for recently viewed cards
const TYPE_ICONS = {
  startup: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>`,
  product: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path></svg>`,
  paper: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>`,
  job: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>`,
  news: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 20H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v1m2 13a2 2 0 0 1-2-2V7m2 13a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"></path></svg>`,
  search: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>`,
  default: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg>`
};

// Clock activity icon (counter-clockwise arrow around clock face matching user image)
const ACTIVITY_CLOCK_ICON = `
  <svg class="activity-glyph" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
    <path d="M3 3v5h5"></path>
    <path d="M12 7v5l4 2"></path>
  </svg>
`;

function showToast(msg) {
  const toastEl = document.getElementById('toast');
  if (!toastEl) return;
  toastEl.textContent = msg;
  toastEl.classList.add('show');
  setTimeout(() => toastEl.classList.remove('show'), 3500);
}

function initActivityPage() {
  setupSwitchingBars();
  setupSearchAndControls();
  renderAll();
}

function setupSwitchingBars() {
  // Category switching bars
  const catBtns = document.querySelectorAll('#category-switching-bars .switching-bar');
  catBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      catBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeCategory = btn.dataset.category || 'all';
      renderRecentlyViewed();
    });
  });

  // Time horizon switching bars
  const timeBtns = document.querySelectorAll('#time-switching-bars .switching-bar');
  timeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      timeBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeTime = btn.dataset.time || 'all';
      renderRecentlyViewed();
    });
  });
}

function setupSearchAndControls() {
  if (activitySearchInput) {
    activitySearchInput.addEventListener('input', (e) => {
      searchFilter = e.target.value.trim().toLowerCase();
      renderRecentlyViewed();
    });
  }

  if (resetFilterBtn) {
    resetFilterBtn.addEventListener('click', () => {
      activeCategory = 'all';
      activeTime = 'all';
      searchFilter = '';
      if (activitySearchInput) activitySearchInput.value = '';

      document.querySelectorAll('#category-switching-bars .switching-bar').forEach(b => {
        b.classList.toggle('active', b.dataset.category === 'all');
      });
      document.querySelectorAll('#time-switching-bars .switching-bar').forEach(b => {
        b.classList.toggle('active', b.dataset.time === 'all');
      });

      renderRecentlyViewed();
      showToast('Filters reset to All Recent Visits');
    });
  }

  if (btnClearActivity) {
    btnClearActivity.addEventListener('click', () => {
      if (confirm('Clear all your recent visits and activity history?')) {
        window.clearAllActivity();
        renderAll();
        showToast('Activity history cleared.');
      }
    });
  }

  if (btnExportActivity) {
    btnExportActivity.addEventListener('click', () => {
      const items = window.getActivityHistory();
      const blob = new Blob([JSON.stringify(items, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `graphone_activity_${new Date().toISOString().slice(0,10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast('Exported activity history as JSON');
    });
  }
}

function computeStats(items) {
  const total = items.length;
  const now = Date.now();
  const oneDayMs = 24 * 3600 * 1000;

  const todayCount = items.filter(it => {
    const t = new Date(it.timestamp).getTime();
    return (now - t) < oneDayMs;
  }).length;

  const categoryCounts = {};
  items.forEach(it => {
    const cat = it.type || 'item';
    categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
  });

  let topCat = 'All';
  let maxCatCount = 0;
  for (const [k, v] of Object.entries(categoryCounts)) {
    if (v > maxCatCount) {
      maxCatCount = v;
      topCat = k.charAt(0).toUpperCase() + k.slice(1);
    }
  }

  if (statTotalVisits) statTotalVisits.textContent = total.toLocaleString();
  if (statTodayVisits) statTodayVisits.textContent = todayCount.toLocaleString();
  if (statTopCategory) statTopCategory.textContent = total > 0 ? topCat : 'None';

  // Update switching bars counts
  const setElCount = (id, count) => {
    const el = document.getElementById(id);
    if (el) el.textContent = count.toLocaleString();
  };

  setElCount('count-all', total);
  setElCount('count-startups', categoryCounts['startup'] || categoryCounts['startups'] || 0);
  setElCount('count-products', categoryCounts['product'] || categoryCounts['products'] || 0);
  setElCount('count-papers', categoryCounts['paper'] || categoryCounts['papers'] || 0);
  setElCount('count-jobs', categoryCounts['job'] || categoryCounts['jobs'] || 0);
  setElCount('count-news', categoryCounts['news'] || 0);
  setElCount('count-search', (categoryCounts['search'] || 0) + (categoryCounts['resolution'] || 0));
}

function filterItems(items) {
  const now = Date.now();
  const oneHourMs = 3600 * 1000;
  const oneDayMs = 24 * 3600 * 1000;
  const twoDaysMs = 48 * 3600 * 1000;

  return items.filter(item => {
    // Category filter
    if (activeCategory !== 'all') {
      const type = (item.type || '').toLowerCase();
      if (activeCategory === 'startups' && type !== 'startup' && type !== 'startups') return false;
      if (activeCategory === 'products' && type !== 'product' && type !== 'products') return false;
      if (activeCategory === 'papers' && type !== 'paper' && type !== 'papers') return false;
      if (activeCategory === 'jobs' && type !== 'job' && type !== 'jobs') return false;
      if (activeCategory === 'news' && type !== 'news') return false;
      if (activeCategory === 'search' && type !== 'search' && type !== 'resolution') return false;
    }

    // Time filter
    if (activeTime !== 'all') {
      const t = new Date(item.timestamp).getTime();
      const diff = now - t;
      if (activeTime === 'hour' && diff > oneHourMs) return false;
      if (activeTime === 'today' && diff > oneDayMs) return false;
      if (activeTime === 'yesterday' && (diff <= oneDayMs || diff > twoDaysMs)) return false;
      if (activeTime === 'older' && diff <= twoDaysMs) return false;
    }

    // Search filter
    if (searchFilter) {
      const target = `${item.title || ''} ${item.subtitle || ''} ${item.badge || ''} ${item.url || ''}`.toLowerCase();
      if (!target.includes(searchFilter)) return false;
    }

    return true;
  });
}

function renderRecentlyViewed() {
  const allItems = window.getActivityHistory();
  computeStats(allItems);

  const filtered = filterItems(allItems);

  // Update header text
  const catLabels = {
    all: 'All Recent Visits',
    startups: 'Recent Startups',
    products: 'Recent Products',
    papers: 'Recent Research Papers',
    jobs: 'Recent Jobs',
    news: 'Recent News Articles',
    search: 'Recent Searches & Entity Lookups'
  };

  if (activeCategoryTitle) {
    activeCategoryTitle.textContent = catLabels[activeCategory] || 'Recent Visits';
  }
  if (activeCategoryCount) {
    activeCategoryCount.textContent = `${filtered.length} item${filtered.length === 1 ? '' : 's'}`;
  }
  if (activeFilterDesc) {
    const timeText = activeTime === 'all' ? 'All time' : activeTime === 'today' ? 'Today' : activeTime === 'yesterday' ? 'Yesterday' : 'Older records';
    const queryText = searchFilter ? ` • Matching "${searchFilter}"` : '';
    activeFilterDesc.textContent = `${timeText}${queryText} • Sorted newest first`;
  }

  // Render cards
  if (!recentlyViewedList) return;

  if (filtered.length === 0) {
    recentlyViewedList.innerHTML = `
      <div class="activity-empty-state">
        <div class="activity-empty-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75">
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
            <path d="M3 3v5h5"></path>
            <path d="M12 7v5l4 2"></path>
          </svg>
        </div>
        <div class="activity-empty-title">No matching visits found</div>
        <div class="activity-empty-desc">
          ${searchFilter ? 'Try clearing your search query or switching to another category.' : 'Browse the GraphOne Intelligence Dashboard to automatically record your visits.'}
        </div>
        <a href="/" class="btn btn-secondary" style="margin-top: 14px; font-size: 0.8rem;">
          Return to Dashboard
        </a>
      </div>
    `;
    return;
  }

  recentlyViewedList.innerHTML = filtered.map(item => {
    const icon = TYPE_ICONS[item.type] || TYPE_ICONS.default;
    const relTime = window.formatRelativeTime(item.timestamp);
    const badgeType = (item.badge || item.type || 'ACTIVITY').toUpperCase();

    // Map badge classes
    let badgeClass = 'badge-freemium';
    if (badgeType.includes('STARTUP')) badgeClass = 'badge-paid';
    else if (badgeType.includes('PRODUCT')) badgeClass = 'badge-free';
    else if (badgeType.includes('PAPER')) badgeClass = 'badge-enterprise';
    else if (badgeType.includes('JOB')) badgeClass = 'badge-freemium';
    else if (badgeType.includes('NEWS')) badgeClass = 'badge-enterprise';
    else if (badgeType.includes('SEARCH') || badgeType.includes('ENTITY')) badgeClass = 'badge-paid';

    const hasUrl = item.url && item.url !== '#' && item.url !== '#playground';

    return `
      <div class="activity-card" id="${item.id}">
        <!-- Left End Activity & Time Symbol -->
        <div class="activity-card-lead">
          <div class="activity-icon-bubble" title="${badgeType}">
            ${icon}
          </div>
          <div class="activity-time-stamp" title="${item.timestamp}">
            ${ACTIVITY_CLOCK_ICON}
            <span>${relTime}</span>
          </div>
        </div>

        <!-- Center Content -->
        <div class="activity-card-main">
          <div class="activity-card-heading">
            <span class="activity-card-title">${escapeHtml(item.title)}</span>
            <span class="badge ${badgeClass}" style="font-size: 0.68rem; padding: 2px 7px;">${badgeType}</span>
          </div>
          ${item.subtitle ? `<div class="activity-card-subtitle">${escapeHtml(item.subtitle)}</div>` : ''}
          ${hasUrl ? `<div class="activity-card-url">${escapeHtml(item.url)}</div>` : ''}
        </div>

        <!-- Right End Actions -->
        <div class="activity-card-actions">
          ${hasUrl ? `
            <a href="${item.url}" target="_blank" rel="noopener noreferrer" class="activity-action-btn" title="Open source link">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
              <span>Visit</span>
            </a>
          ` : `
            <a href="/${item.url.startsWith('#') ? item.url : ''}" class="activity-action-btn" title="View in Dashboard">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
              <span>Explore</span>
            </a>
          `}
          <button class="activity-action-delete" onclick="handleDeleteItem('${item.id}')" title="Remove from recent visits">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
          </button>
        </div>
      </div>
    `;
  }).join('');
}

window.handleDeleteItem = function(id) {
  const card = document.getElementById(id);
  if (card) {
    card.style.opacity = '0';
    card.style.transform = 'translateX(12px)';
    setTimeout(() => {
      window.deleteActivityItem(id);
      renderRecentlyViewed();
      showToast('Item removed from recent visits');
    }, 150);
  } else {
    window.deleteActivityItem(id);
    renderRecentlyViewed();
  }
};

function renderAll() {
  renderRecentlyViewed();
}

function escapeHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

document.addEventListener('DOMContentLoaded', initActivityPage);
