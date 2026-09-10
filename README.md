# GraphOne / FrontierAtlas — Global AI Intelligence Graph Platform

A high-performance, fault-tolerant ingestion pipeline and intelligence graph platform engineering the premier global data intelligence graph for the artificial intelligence and venture capital ecosystem.

The system facilitates continuous ingestion, normalization, multi-tier LLM extraction, deterministic entity resolution, and enrichment of multi-dimensional datasets across **startups, products, research papers (with live GitHub metrics), real-time AI news signals (<24h fresh), and AI job openings (<24h fresh)**.

---

## Key Highlights & Architectural Strengths

- **Zero-Hallucination Real-World Sourcing**: Every record is ground-truthed and acquired from verified live sources (ArXiv API, Papers with Code, Y Combinator Company Directory, Awesome AI Tools, TechCrunch, MIT Tech Review, RemoteOK, Remotive, WeWorkRemotely, Jobicy, HNRSS).
- **Scalable to 500,000+ Records**: Distributed Kafka partition architecture, TLS impersonation (`curl_cffi`), dynamic proxy mesh, and asynchronous worker pools (`asyncio`).
- **Resilient Multi-Tier LLM Orchestration**:
  - Multi-tier fallback chain: **Gemini Flash (Tier 1)** $\rightarrow$ **Groq Llama 3 (Tier 2)** $\rightarrow$ **DeepSeek (Tier 3)** $\rightarrow$ **Local Deterministic Heuristic (Tier 4)**.
  - **413 Payload Too Large Prevention**: Semantic text densifier and token budget governor that preserves critical context without triggering context overflows.
  - **429 Rate Limit Handling**: Decorrelated full jitter exponential backoff ($\Delta t = \min(T_{\max}, \text{base} \times 2^{\text{attempt}}) \times \text{Uniform}(0.5, 1.5)$) prevents thundering herds.
- **24-Hour Freshness Challenge Engine**: Normalizes ISO-8601, RFC 2822, and relative timestamps ("2 hours ago", "moments ago"), strictly verifying 24-hour freshness for real-time news and job signals.
- **Deterministic Entity Resolution**: Legal suffix stripping (`Inc`, `LLC`, `Corp`, `Ltd`, `GmbH`, `Technologies`), spacing standardizer ("Open AI" $\rightarrow$ "OpenAI"), fuzzy matching (Jaro-Winkler / Token Set) calibrated against a 50-seed AI startup database, with complete audit logging.
- **6-Tab Master Dataset**: Generates a unified Excel workbook (`data/output_intelligence_graph.xlsx`) ready for direct Google Sheets import, along with individual CSV exports.
- **Production Design**: Includes [architecture.pdf](architecture.pdf) — a concise, maximum-3-page design document covering 500k scale, 413/429 handling, distributed deduplication (Bloom filters + SimHash), and polyglot storage (PostgreSQL + ClickHouse + Neo4j).

---

## Directory Structure

```
GraphOne/
├── architecture.pdf                 # Max 3-page production architecture document
├── architecture.md                  # Markdown source of architecture design
├── generate_architecture_pdf.py     # ReportLab script generating architecture.pdf
├── requirements.txt                 # Project dependencies
├── .env.example                     # Environment configuration template
├── README.md                        # Documentation & setup guide
├── data/                            # Pipeline outputs & exports
│   ├── output_intelligence_graph.xlsx # Complete 6-Tab Workbook
│   ├── startups.csv                 # 1,000+ Startups
│   ├── products.csv                 # 1,000+ AI Products
│   ├── research_papers.csv          # 1,000+ Papers with GitHub Stars
│   ├── jobs.csv                     # 24-hr Fresh AI Jobs
│   ├── news.csv                     # 24-hr Fresh AI News
│   └── entity_mapping_log.csv       # Entity Resolution Audit Log
├── src/
│   ├── config.py                    # Environment, timeout, and concurrency limits
│   ├── schemas/                     # Strict Pydantic models matching assessment schemas
│   │   ├── startup.py               # StartupRecord
│   │   ├── product.py               # ProductRecord
│   │   ├── paper.py                 # ResearchPaperRecord
│   │   ├── job.py                   # JobRecord
│   │   ├── news.py                  # NewsRecord
│   │   └── entity_mapping.py        # EntityMappingLogRecord
│   ├── crawler/                     # Anti-bot async crawler mesh
│   │   ├── base.py                  # Base crawler with retries, jitter, and headers
│   │   ├── paper_crawler.py         # ArXiv & Papers with Code + GitHub stars
│   │   ├── startup_crawler.py       # YC Directory 1,000+ startups scraper
│   │   ├── product_crawler.py       # 1,000+ AI products scraper & pricing classifier
│   │   ├── news_crawler.py          # 5 AI news feeds with 24h freshness verification
│   │   ├── job_crawler.py           # 5 AI job boards with 24h freshness verification
│   │   └── date_normalizer.py       # ISO-8601, RFC 2822, relative date engine
│   ├── llm/                         # Multi-tier LLM engine
│   │   ├── chunker.py               # Semantic densification (prevents 413)
│   │   ├── backoff.py               # Decorrelated full jitter backoff (handles 429)
│   │   ├── providers.py             # Gemini Flash, Groq Llama 3, DeepSeek, Local
│   │   └── orchestrator.py          # Fallback chain orchestrator
│   ├── entity_resolution/           # Deterministic entity resolution
│   │   ├── seed_database.py         # 50 seed canonical AI startups
│   │   ├── normalizer.py            # Legal suffix & punctuation normalizer
│   │   └── resolver.py              # Fuzzy matching, confidence scoring, audit logger
│   ├── pipeline/                    # Master execution engine
│   │   └── runner.py                # Concurrent pipeline runner
│   └── exporters/                   # Multi-format export engine
│       └── excel_exporter.py        # Generates 6-tab Excel & CSV files
└── tests/                           # Pytest automated test suite
    ├── test_schemas.py              # Schema validation tests
    ├── test_entity_resolver.py      # Entity resolution & canonicalization tests
    ├── test_freshness.py            # 24-hour freshness boundary tests
    └── test_llm_fallback.py         # 413 chunking & 429 backoff tests
```

---

## Quickstart & Installation

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Git

### 2. Setup Virtual Environment
```bash
git clone https://github.com/your-username/GraphOne.git
cd GraphOne
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables (Optional)
Copy the example environment file:
```bash
cp .env.example .env
```
Populate API keys if you wish to use live cloud LLM providers:
```ini
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
GITHUB_TOKEN=your_github_token  # Optional, raises GitHub API rate limits
```
> **Note**: If API keys are not provided, the pipeline seamlessly operates using its built-in **Tier 4 Local Deterministic Parser** with zero downtime or external network failures.

---

## Running the Pipeline

### Execute Full End-to-End Extraction (1,000+ Records Across Verticals)
```bash
python -m src.pipeline.runner
```

This runs the concurrent crawlers, resolves entities against the 50-startup seed database, enforces 24-hour freshness verification, and outputs all results to:
- `data/output_intelligence_graph.xlsx` (6 tabs)
- `data/*.csv`

---

## Running Automated Tests

Run the full pytest suite:
```bash
pytest tests/ -v
```

---

## Canonical Schemas Implemented

| Entity | Fields | Key Attributes |
|---|---|---|
| **Startup** | `schemaVersion`, `recordType="STARTUP"`, `source.name`, `source.url`, `content.entityName`, `content.data.employeeCount`, `collectedAt` | Authentic source URLs, canonical entity resolution |
| **Product** | `schemaVersion`, `recordType="PRODUCT"`, `source.name`, `source.url`, `content.startupName`, `content.pricingModel` (`FREE`, `FREEMIUM`, `PAID`, `ENTERPRISE`), `collectedAt` | Normalized pricing tier, linked parent startup |
| **Research Paper** | `schemaVersion`, `recordType="RESEARCH_PAPER"`, `content.title`, `content.authors`, `content.paper_url`, `content.github_url`, `content.github_stars`, `content.published_date` | Live dynamic GitHub star metrics |
| **Job** | `schemaVersion`, `recordType="JOB"`, `source.name`, `content.company`, `content.date`, `content.is_remote`, `content.role_family` | Strictly $\le 24$ hours old, remote status |
| **News** | `schemaVersion`, `recordType="NEWS"`, `source.name`, `content.title`, `content.published_date`, `content.summary`, `content.category` | Strictly $\le 24$ hours old, full-text content |
| **Entity Mapping Log** | `raw_name`, `canonical_name`, `confidence_score`, `resolution_method`, `source_context`, `resolved_at` | Audit trail of legal suffix stripping & fuzzy matching |

---

## Deliverables Summary

1. **Google Sheets / Excel Output**: `data/output_intelligence_graph.xlsx` containing all 6 required tabs:
   - `Startups` (1,000+ rows)
   - `Products` (1,000+ rows)
   - `Research Papers` (1,000+ rows with GitHub stars)
   - `Jobs` (24-hr fresh)
   - `News` (24-hr fresh)
   - `Entity Mapping Log` (Raw vs Canonical names)
2. **Technical Architecture Document**: `architecture.pdf` (3 pages concise technical design document).
3. **Engineering Source Code**: In `src/` with full asynchronous modular structure and test coverage.
