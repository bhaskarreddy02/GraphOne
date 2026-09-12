// GraphOne User Activity & Recent Visits Tracker
// Centralized storage, tracking, and query helper

const ACTIVITY_STORAGE_KEY = 'graphone_recent_visits';

// Default initial sample visits to populate when user first opens the feature
const SEED_ACTIVITY_ITEMS = [
  {
    id: 'seed_1',
    type: 'startup',
    title: 'Scale AI',
    subtitle: 'Data Infrastructure · YC S16 · 1,200 Employees',
    url: 'https://scale.com',
    timestamp: new Date(Date.now() - 4 * 60 * 1000).toISOString(), // 4 mins ago
    badge: 'STARTUP',
    meta: {
      source: 'Y Combinator',
      category: 'Infrastructure & Cloud',
      action: 'viewed_profile'
    }
  },
  {
    id: 'seed_2',
    type: 'product',
    title: 'Claude 3.5 Sonnet',
    subtitle: 'Anthropic · FREEMIUM · LLM Frontier Model',
    url: 'https://anthropic.com/claude',
    timestamp: new Date(Date.now() - 18 * 60 * 1000).toISOString(), // 18 mins ago
    badge: 'PRODUCT',
    meta: {
      source: 'Direct Site',
      pricing: 'FREEMIUM',
      action: 'visited_site'
    }
  },
  {
    id: 'seed_3',
    type: 'paper',
    title: 'DeepSeek-V3 Technical Report',
    subtitle: 'DeepSeek-AI · 8,420 stars · Hugging Face Daily #1',
    url: 'https://arxiv.org/abs/2412.19437',
    timestamp: new Date(Date.now() - 45 * 60 * 1000).toISOString(), // 45 mins ago
    badge: 'RESEARCH_PAPER',
    meta: {
      source: 'ArXiv Preprints',
      metrics: '8,420 ⭐ · 940 🤗',
      action: 'opened_paper'
    }
  },
  {
    id: 'seed_4',
    type: 'job',
    title: 'Staff Machine Learning Engineer',
    subtitle: 'OpenAI · Engineering · San Francisco, CA',
    url: 'https://openai.com/careers',
    timestamp: new Date(Date.now() - 2 * 3600 * 1000).toISOString(), // 2 hours ago
    badge: 'JOB',
    meta: {
      source: 'Verified 24h Signals',
      company: 'OpenAI',
      action: 'clicked_apply'
    }
  },
  {
    id: 'seed_5',
    type: 'news',
    title: 'Next-Gen AI Hardware Accelerators Set New Benchmarks in Inference Efficiency',
    subtitle: 'TechCrunch AI · Verified <24h Ingested Signal',
    url: 'https://techcrunch.com/category/artificial-intelligence/',
    timestamp: new Date(Date.now() - 5 * 3600 * 1000).toISOString(), // 5 hours ago
    badge: 'NEWS',
    meta: {
      source: 'TechCrunch AI',
      action: 'read_article'
    }
  },
  {
    id: 'seed_6',
    type: 'search',
    title: 'LLM Quantization & Inference Engines',
    subtitle: 'Entity Resolution Playground · 98.2% Match Confidence',
    url: '#playground',
    timestamp: new Date(Date.now() - 24 * 3600 * 1000).toISOString(), // 1 day ago
    badge: 'SEARCH',
    meta: {
      source: 'Graph Query',
      action: 'resolved_entity'
    }
  }
];

function getActivityHistory() {
  try {
    const raw = localStorage.getItem(ACTIVITY_STORAGE_KEY);
    if (!raw) {
      // Seed with initial realistic visits so interface isn't bare
      localStorage.setItem(ACTIVITY_STORAGE_KEY, JSON.stringify(SEED_ACTIVITY_ITEMS));
      return SEED_ACTIVITY_ITEMS;
    }
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed;
  } catch (err) {
    console.error('Error reading activity history:', err);
    return [];
  }
}

function saveActivityHistory(items) {
  try {
    localStorage.setItem(ACTIVITY_STORAGE_KEY, JSON.stringify(items));
    updateHeaderBadge();
  } catch (err) {
    console.error('Error saving activity history:', err);
  }
}

function trackActivity({ type, title, subtitle = '', url = '', badge = '', meta = {} }) {
  if (!title) return;
  const items = getActivityHistory();

  // Deduplicate: remove any existing entry matching same type and title or url
  const filtered = items.filter(it => {
    const sameTitle = it.title.trim().toLowerCase() === title.trim().toLowerCase();
    const sameType = it.type === type;
    const sameUrl = url && it.url && it.url === url;
    return !(sameType && (sameTitle || sameUrl));
  });

  const newEntry = {
    id: 'act_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7),
    type: type || 'item',
    title: title.trim(),
    subtitle: subtitle.trim(),
    url: url.trim(),
    badge: (badge || type || 'ACTIVITY').toUpperCase(),
    timestamp: new Date().toISOString(),
    meta: meta || {}
  };

  filtered.unshift(newEntry);
  // Cap at 150 items
  const trimmed = filtered.slice(0, 150);
  saveActivityHistory(trimmed);
  return newEntry;
}

function deleteActivityItem(id) {
  const items = getActivityHistory();
  const updated = items.filter(it => it.id !== id);
  saveActivityHistory(updated);
  return updated;
}

function clearAllActivity() {
  saveActivityHistory([]);
  return [];
}

function updateHeaderBadge() {
  const badgeEl = document.getElementById('header-activity-count');
  if (badgeEl) {
    const items = getActivityHistory();
    badgeEl.textContent = items.length;
    badgeEl.style.display = items.length > 0 ? 'inline-flex' : 'none';
  }
}

function formatRelativeTime(isoString) {
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) return 'Just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHour < 24) return `${diffHour}h ago`;
    if (diffDay === 1) return 'Yesterday';
    if (diffDay < 7) return `${diffDay}d ago`;

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) +
           ' ' + date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
  } catch (e) {
    return 'Recent';
  }
}

// Global initialization
if (typeof window !== 'undefined') {
  window.getActivityHistory = getActivityHistory;
  window.trackActivity = trackActivity;
  window.deleteActivityItem = deleteActivityItem;
  window.clearAllActivity = clearAllActivity;
  window.updateHeaderBadge = updateHeaderBadge;
  window.formatRelativeTime = formatRelativeTime;

  document.addEventListener('DOMContentLoaded', () => {
    updateHeaderBadge();
  });
}
