# Technical Architecture & Production Design
**GraphOne / FrontierAtlas - Global AI Intelligence Graph**

---

## 1. Scale Strategy: Ingesting 500,000+ Multi-Dimensional Records

Scaling ingestion from $10^3$ to $5 \times 10^5+$ records without manual intervention requires transitioning from single-node asynchronous pipelines to a distributed, event-driven streaming architecture.

```
+-----------------------------------------------------------------------------------+
|                            Distributed Scale Architecture                          |
+-----------------------------------------------------------------------------------+
|  [Seed URLs & Catalog Discovery] (ArXiv, YC, GitHub, News Feeds, Job Boards)      |
|                                       │                                           |
|                                       ▼                                           |
|                  [Distributed Frontier Queue: Apache Kafka]                        |
|                     - Partitioned by Domain Hash (Host Concurrency)               |
|                                       │                                           |
|       ┌───────────────────────────────┼───────────────────────────────┐           |
|       ▼                               ▼                               ▼           |
|  [Crawler Worker 1]            [Crawler Worker 2]            [Crawler Worker N]   |
|  - TLS Impersonation (curl_cffi)- Proxy Pool (BrightData/Oxy) - Token Bucket Rate |
|  - Playwright Headless         - HTML Stripper & Minifier     - Jittered Backoff  |
|                                       │                                           |
|                                       ▼                                           |
|                    [Kafka Topic: raw-extracted-documents]                         |
|                                       │                                           |
|       ┌───────────────────────────────┼───────────────────────────────┐           |
|       ▼                               ▼                               ▼           |
|  [LLM Worker 1]                [LLM Worker 2]                [LLM Worker M]       |
|  - Semantic Chunker (413 Safe) - Token Budget Governor        - Tier Fallback     |
|                                       │                                           |
|                                       ▼                                           |
|              [Deterministic Entity Resolution (Ray / Flink Cluster)]               |
|              - Inverted Alias Triemap + Jaro-Winkler + FastText Vectorizer        |
|                                       │                                           |
|       ┌───────────────────────────────┴───────────────────────────────┐           |
|       ▼                                                               ▼           |
|  [PostgreSQL / ClickHouse]                                     [Neo4j Graph & Qdrant]|
|  (Raw Structured Entities)                                     (Multi-Dimensional KG)|
+-----------------------------------------------------------------------------------+
```

### Architectural Pillars for 500k+ Throughput
1. **Partitioned URL Frontier (Apache Kafka + Celery/Ray)**:
   - URL partitions are hashed by target hostname (`hash(domain) % partitions`). This guarantees that concurrency limits and domain-specific delays (e.g., ArXiv rate policies, Cloudflare challenges) are isolated per partition without global blocking.
2. **Dynamic Proxy Mesh & TLS Fingerprint Rotation**:
   - High-throughput residential and data-center proxy mesh (BrightData / Oxylabs) with automatic round-robin rotation upon receiving status 403/429.
   - Using HTTP/2 and JA3/JA4 TLS fingerprint impersonation (`curl_cffi`) to mimic standard browser handshakes, bypassing Cloudflare Turnstile and Datadome anti-bot defenses.
3. **Headless Browser Tier (Playwright Pool with Chromium Warm-Starts)**:
   - For heavily obfuscated Single-Page Applications (SPAs), lightweight Playwright headless workers render DOMs dynamically, intercepting network XHR/GraphQL responses directly to extract raw JSON payloads rather than scraping rendered HTML.

---

## 2. Handling 413s & 429s Across Thousands of Concurrent Extractions

High-concurrency LLM extraction encounters two critical failure modes: HTTP 413 (Payload Too Large / Context Exceeded) and HTTP 429 (Rate Limits / TPM & RPM limits).

### HTTP 413 Mitigation: Two-Tier Token Budgeting & Semantic Chunking
- **DOM Densification**: Raw HTML is stripped of scripts, styles, SVGs, base64 images, nav bars, and footers. Only semantic elements (`<article>`, `<main>`, `<h1-h3>`, `<p>`, `<meta>`) are retained.
- **Dynamic Token Budgeting**: 
  $$\text{Payload Budget} = \min(\text{Model Context Limit}, 4000 \text{ tokens}) - \text{Schema Prompt Reserve}$$
- **Sentence-Boundary Sliding Truncation**: Documents exceeding the budget are truncated strictly along sentence boundaries using greedy whitespace lookback, ensuring no fragmented tokens or broken JSON instructions are delivered to the LLM.
- **Hierarchical Map-Reduce**: For long research papers or multi-page terms of service, text is partitioned into semantically coherent 2,000-token sections, processed in parallel, and consolidated into a unified schema record.

### HTTP 429 Mitigation: Distributed Token Buckets & Decorrelated Full Jitter
- **Centralized Rate Governor (Redis Token Bucket)**: Crawler and LLM workers query a centralized Redis rate governor before dispatching LLM API calls. Each provider (`Gemini Flash`, `Groq Llama 3`, `DeepSeek`) has an isolated sliding window counter for Requests Per Minute (RPM) and Tokens Per Minute (TPM).
- **Decorrelated Full Jitter Backoff**:
  When an API provider emits HTTP 429 or header `Retry-After`:
  $$\Delta t = \min\left(T_{\max}, \text{base} \cdot 2^{\text{attempt}}\right) \times \text{Uniform}(0.5, 1.5)$$
  This decorrelation mathematically disperses retry waves, completely avoiding thundering-herd synchronizations across thousands of distributed workers.
- **Multi-Tier Cascade Failover**:
  $$\text{Gemini Flash (Tier 1)} \xrightarrow{429 / \text{Timeout}} \text{Groq Llama 3 (Tier 2)} \xrightarrow{429 / \text{Fail}} \text{DeepSeek (Tier 3)} \xrightarrow{\text{Fail}} \text{Local Regex Parser (Tier 4)}$$
  If a provider enters sustained rate limiting, circuit breakers temporarily redirect traffic to downstream tiers for 60 seconds.

---

## 3. Freshness Tracking: Zero-Duplicate Distributed Crawling

To ensure that distributed nodes never re-process the same article or job posting within the 24-hour window:

```
Ingested Item (URL, Canonical Text)
          │
          ▼
 [Step 1: Canonical URL Normalization]
 (Strip UTM params, tracking tags, trailing slashes, scheme lowercasing)
          │
          ▼
 [Step 2: Distributed Scalable Bloom Filter (RedisBloom)]
  - False positive rate < 0.01%
  - In-memory check in O(1) < 1ms
  ├── If Present (Likely Seen) ──► [Step 3: Exact Redis Key Verification] ──► [DROP DUPLICATE]
  └── If Absent (Definitely New) ─┐
                                  ▼
                     [Step 4: SimHash MinHash Fingerprinting]
                      - 64-bit fingerprint of semantic body text
                      - Detects syndicated cross-posts across different URLs
                      ├── Hamming Distance <= 3 ──► [MERGE & DROP]
                      └── Hamming Distance > 3  ──► [ACCEPT & PROCESS]
                                  │
                                  ▼
               [Step 5: Distributed Lock + 48h TTL Key]
                SET key:canonical_url EX 172800 NX
```

- **Distributed Scalable Bloom Filter**: An in-memory RedisBloom filter checks seen URLs with sub-millisecond latency. A false-positive rate of $<0.01\%$ guarantees minimal re-checks.
- **SimHash Content Deduplication**: AI news articles and job postings are frequently syndicated across multiple aggregators with distinct URLs. Computing a 64-bit SimHash of normalized text allows identifying duplicates with Hamming distance $\le 3$, eliminating duplicate signals even when source URLs differ.
- **Idempotency Keys**: Database writes enforce strict uniqueness on `(canonical_company_id, hash(job_title), published_date_truncated_to_day)`.

---

## 4. Storage Strategy: Multi-Model Intelligence Architecture

The GraphOne ecosystem involves high-velocity signals (news, jobs), relational state (funding rounds, employee counts, pricing models), unstructured embeddings, and deep relationship traversals (Founder $\rightarrow$ Startup $\rightarrow$ Product $\rightarrow$ Paper $\rightarrow$ Repo). A single database cannot satisfy these diverging access patterns.

```
+-----------------------------------------------------------------------------------------+
|                                Polyglot Persistence Architecture                         |
+-----------------------------------------------------------------------------------------+
|      Relational State             Analytics & Signals               Graph & Vectors     |
|         (PostgreSQL)                  (ClickHouse)               (Neo4j + Pgvector)     |
|  • Startups Core Metadata     • 24h News Signals              • Entity Knowledge Graph  |
|  • Canonical Product Registry • Job Market Velocity           • Cites, BuiltBy, Founded |
|  • Entity Resolution Mappings • Time-series Star Histories    • Semantic Vector Search  |
+-----------------------------------------------------------------------------------------+
```

### Storage Engine Selection Justification

1. **Primary Relational Store: PostgreSQL 16 (with JSONB & pgvector)**
   - **Role**: Source of truth for entity metadata, canonical resolution mappings, user accounts, and pipeline execution logs.
   - **Justification**: ACID transactions prevent race conditions during distributed entity canonicalization. Native JSONB allows flexible schema evolution across diverse startup types.

2. **Real-Time Signal & Analytical Store: ClickHouse**
   - **Role**: Ingestion sink for continuous news feeds, job postings, and dynamic GitHub star time-series metrics.
   - **Justification**: Columnar storage compresses repetitive string data (e.g. tech tags, author lists) by up to $80\%$. ClickHouse effortlessly ingests hundreds of thousands of signal rows per second and supports sub-second aggregations (`SELECT avg(stars), date FROM papers GROUP BY date`).

3. **Knowledge Graph Store: Neo4j (Cypher Query Engine)**
   - **Role**: Graph representation of the venture intelligence ecosystem:
     - `(:STARTUP)-[:DEVELOPS]->(:PRODUCT)`
     - `(:RESEARCH_PAPER)-[:IMPLEMENTED_IN]->(:GITHUB_REPO)`
     - `(:COMPANY)-[:POSTED]->(:JOB)`
     - `(:ARTICLE)-[:MENTIONS]->(:STARTUP)`
   - **Justification**: Relational JOINs across 5 or 6 levels of venture relations degrade exponentially ($O(n^k)$). Neo4j's index-free adjacency traverses multi-hop graph neighborhoods in $O(1)$ per edge, enabling instant graph queries (e.g., "Find all YC startups whose founders published an ArXiv paper with $>500$ GitHub stars").
