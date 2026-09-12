# GraphOne / FrontierAtlas 🌐
### Global AI Intelligence Graph — Live Web Application

> A real-time intelligence platform that crawls, extracts, resolves, and visualises the AI & venture ecosystem across **7,619 entities** — startups, products, research papers, jobs, and news signals — with an interactive knowledge graph and live entity resolver.

---

## What is GraphOne?

GraphOne is a full-stack intelligence system built for the AI and venture capital ecosystem. It does four things end-to-end:

1. **Crawls** — pulls live data from Y Combinator, ArXiv, Hugging Face, Papers With Code, GitHub, TechCrunch, Wired, MIT Tech Review, and 5 job boards.
2. **Extracts** — uses a multi-tier LLM fallback chain (Gemini Flash → Groq Llama 3 → DeepSeek → Local Regex) to pull structured fields from raw HTML.
3. **Resolves** — a deterministic entity resolver canonicalises names like `"Open AI, Inc."` → `"OpenAI"` using exact normalisation + RapidFuzz fuzzy matching, and logs every decision with confidence scores.
4. **Serves** — an aiohttp web server exposes all data through 14 REST endpoints, powering a browser-based SPA with searchable tables, an interactive knowledge graph, and a live resolver playground.

---

## Live Features

### 📊 Data Tables
- **2,500 Startups** — canonical names, team sizes, industry categories, YC batch badges, website links, direct YC profile links
- **2,500 AI Products** — parent startup, pricing tier (FREE / FREEMIUM / PAID / ENTERPRISE), category, source links
- **2,500 Research Papers** — GitHub stars, HuggingFace upvotes, authors, source platform badges (ArXiv / HF / Papers With Code), PDF links
- **73 AI Jobs** — 24h-fresh openings from 5 job boards, role family, company, location, remote status
- **46 News Signals** — 24h-fresh headlines from TechCrunch, Wired, MIT Tech Review, Ars Technica, AI News
- **5,073 Entity Audit Entries** — every resolution decision logged with raw name, canonical name, method, and confidence score

Search, filter, sort, and paginate all 2,500 rows per vertical. Page size goes up to "Show All".

### 🕸️ Interactive Knowledge Graph
Select any entity — startup, product, paper, job, or news item — and instantly see its near-linkage graph:

- The selected entity sits at the centre as an **oval node**
- Connected nodes radiate out: 🚀 products, 📄 papers, 💼 job openings, 📰 news signals
- **Hover** any node to see a glassmorphic popover with metadata
- **Click** any node to open its live external URL
- Edge labels show relationship type (`DEVELOPS`, `AUTHORED_BY`, `HIRING_TEAM`, `SIGNAL`, etc.)
- Smooth spline edges, no arrows — clean organic graph layout

### 🔍 Entity Resolver Playground
Type any raw company name and see the resolver work live:
- Exact match via normalised canonical map
- Fuzzy match via RapidFuzz + Jaro-Winkler (threshold 0.70)
- Returns `null` rather than guessing — never hallucinates
- Every decision displayed: `{ raw_name, canonical_name, method, confidence }`

### 📡 Continuous Monitoring Pipeline
A persistent background pipeline runs 10 source crawlers (5 news + 5 job boards) on a continuous loop:
- Items deduplicated by SHA-256 hash — never re-processes a seen URL
- 24-hour freshness strictly enforced — stale items discarded, not stored
- State persisted in SQLite — survives server restarts
- Full run history visible in the Pipeline tab with per-source metrics

### 📥 Downloads
- **Download Excel** — `output_intelligence_graph.xlsx`, a 6-tab workbook (901 KB), correct MIME type, opens cleanly in Excel / Google Sheets
- **Architecture PDF** — 3-page technical design document

---

## Architecture Overview

```
Data Sources          Ingestion Pipeline              Storage         Web App
─────────────         ───────────────────             ───────         ───────
YC Directory    ──►   5 Bulk Crawlers (async)   ──►
ArXiv / HF / PWC      10 Signal Monitors (24h)       CSVs      ──►   aiohttp API
GitHub API      ──►         ↓                         SQLite    ──►   14 endpoints
TechCrunch etc        Deduplicator (SHA-256)          Excel     ──►   Browser SPA
RemoteOK etc          LLM Chain (4-tier fallback)               ──►   vis.js Graph
                      Entity Resolver (fuzzy)
```

**LLM Fallback Chain** — Gemini Flash → Groq Llama 3 → DeepSeek → Local Regex. The last tier always succeeds, so data is never lost even if all cloud APIs are down.

**Entity Resolver** — Three-step deterministic flow:
1. Normalise (strip legal suffixes, punctuation, compound fusion)
2. Exact lookup in canonical map
3. RapidFuzz + JaroWinkler fuzzy match ≥ 0.70 threshold
4. Return `null` — never guesses

---

## Quickstart

### Prerequisites
- Python 3.10+

### 1. Clone & Install
```bash
git clone https://github.com/bhaskarreddy02/GraphOne.git
cd GraphOne
python -m venv venv

# Windows
.\venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. (Optional) Set API Keys
```bash
cp .env.example .env
```
```ini
GEMINI_API_KEY=your_key
GROQ_API_KEY=your_key
DEEPSEEK_API_KEY=your_key
GITHUB_TOKEN=your_token   # raises GitHub rate limits for star scraping
```
> Without any API keys, the system falls back to the local regex parser automatically. Everything still works.

### 3. Start the Web Server
```bash
python -m src.server
```
Open **http://localhost:8000** in your browser.

### 4. (Optional) Re-run the Full Ingestion Pipeline
```bash
python -m src.pipeline.runner
```
This recrawls all sources, re-resolves entities, and regenerates all CSVs and the Excel workbook.

---

## Project Structure

```
GraphOne/
├── Procfile                          # Railway / Render deployment config
├── requirements.txt
├── .env.example
│
├── data/
│   ├── startups.csv                  # 2,500 records
│   ├── products.csv                  # 2,500 records
│   ├── research_papers.csv           # 2,500 records
│   ├── jobs.csv                      # 73 fresh records
│   ├── news.csv                      # 46 fresh records
│   ├── entity_mapping_log.csv        # 5,073 resolution audit entries
│   ├── output_intelligence_graph.xlsx # 6-tab Excel workbook (901 KB)
│   └── pipeline_state.db             # SQLite monitoring state
│
├── public/
│   ├── index.html                    # Main SPA shell
│   ├── app.js                        # All frontend logic
│   ├── style.css                     # Dark glassmorphic UI
│   ├── activity.html                 # Recent visits tracker
│   └── vis-network.min.js            # Graph visualisation (local asset)
│
└── src/
    ├── server.py                     # aiohttp server, 14 REST endpoints
    ├── config.py                     # Environment config
    ├── schemas/                      # Pydantic models
    │   ├── startup.py
    │   ├── product.py
    │   ├── paper.py
    │   ├── job.py
    │   ├── news.py
    │   └── entity_mapping.py
    ├── crawler/
    │   ├── base.py                   # Async base with jitter backoff + UA rotation
    │   ├── startup_crawler.py        # YC Directory
    │   ├── product_crawler.py        # ProductHunt / GitHub
    │   ├── paper_crawler.py          # ArXiv / HF / PWC + GitHub stars
    │   ├── news_crawler.py           # 5 news sources
    │   ├── job_crawler.py            # 5 job boards
    │   ├── date_normalizer.py        # ISO-8601 / RFC 2822 / relative dates
    │   └── modules/
    │       ├── news/                 # TechCrunch, MIT, AINews, Wired, Ars
    │       └── jobs/                 # RemoteOK, Remotive, WWR, Jobicy, HN Jobs
    ├── llm/
    │   ├── orchestrator.py           # 4-tier fallback chain
    │   ├── providers.py              # Gemini / Groq / DeepSeek / Local
    │   ├── chunker.py                # Semantic densifier (prevents 413 errors)
    │   └── backoff.py                # Decorrelated jitter (handles 429 rate limits)
    ├── entity_resolution/
    │   ├── seed_database.py          # 50 canonical AI startup seeds + aliases
    │   ├── normalizer.py             # Legal suffix stripper, compound fusion
    │   └── resolver.py               # Exact + fuzzy resolver with full audit log
    ├── pipeline/
    │   ├── runner.py                 # Master pipeline orchestrator (Phases I–VI)
    │   ├── monitor.py                # Continuous 24h monitoring pipeline
    │   ├── deduplicator.py           # SHA-256 dedup + URL canonicalisation
    │   ├── state_store.py            # SQLite persistent state
    │   └── scheduler.py             # asyncio background scheduling
    └── exporters/
        └── excel_exporter.py         # 6-tab Excel + CSV export
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats` | Platform-wide counts + confidence metrics |
| GET | `/api/startups` | Startups with search, industry, team-size, sort filters |
| GET | `/api/products` | Products with pricing tier filter |
| GET | `/api/papers` | Papers with source + sort-by-stars/upvotes filters |
| GET | `/api/jobs` | Jobs with role filter |
| GET | `/api/news` | News with source filter |
| GET | `/api/mappings` | Entity resolution audit log |
| POST | `/api/resolve` | Live entity resolution — returns decision JSON |
| GET | `/api/graph/entity` | vis.js node+edge payload for any entity |
| GET | `/api/graph/entities` | Entity list for graph category dropdown |
| GET | `/api/download/xlsx` | Download Excel workbook (correct MIME type) |
| GET | `/api/download/pdf` | Download architecture PDF |
| GET | `/api/pipeline/status` | All 10 crawler states |
| POST | `/api/pipeline/run-now` | Trigger a monitoring cycle immediately |

---

## Deploying to the Web

The app is ready to deploy on [Railway](https://railway.app) or [Render](https://render.com) — no Docker needed.

**Railway (recommended):**
1. Go to [railway.app](https://railway.app) → sign in with GitHub
2. "Deploy from GitHub repo" → select `bhaskarreddy02/GraphOne`
3. Railway auto-detects the `Procfile` and starts the server
4. Settings → Networking → Generate Domain → share your link

**Share instantly (local):**
```bash
winget install ngrok
ngrok http 8000
# Gets you a public https://xxxx.ngrok.io URL in seconds
```

---

## Data Scale

| Vertical | Records | Source |
|----------|---------|--------|
| Startups | 2,500 | Y Combinator Directory |
| Products | 2,500 | ProductHunt / GitHub / Awesome Lists |
| Research Papers | 2,500 | ArXiv · Hugging Face · Papers With Code |
| Jobs | 73 (24h fresh) | RemoteOK · Remotive · WeWorkRemotely · Jobicy · HN |
| News | 46 (24h fresh) | TechCrunch · Wired · MIT · Ars Technica · AI News |
| Entity Audit Log | 5,073 | Auto-generated by resolver |
| **Total** | **7,619** | |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+ · aiohttp · asyncio |
| Data | pandas · Pydantic v2 · openpyxl |
| LLM | Gemini Flash · Groq Llama 3 · DeepSeek · Local Regex |
| Entity Resolution | RapidFuzz · JaroWinkler |
| Frontend | Vanilla JS · vis.js · CSS glassmorphism |
| Storage | CSV · SQLite · Excel |
| Fonts | Inter · JetBrains Mono (Google Fonts) |
| Deployment | aiohttp server · Procfile · Railway / Render |
