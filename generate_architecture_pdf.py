"""
Architecture PDF Generator using ReportLab
Compiles architecture.md into a professional, concise 3-page technical design document.
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_PDF = PROJECT_ROOT / "architecture.pdf"


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running Header
        self.drawString(54, 750, "GraphOne / FrontierAtlas — System Architecture & Production Design")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 742, 558, 742)

        # Running Footer
        self.line(54, 45, 558, 45)
        self.drawString(54, 32, "Confidential — AI Engineer Assessment Submission")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_str)
        self.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=58,
        bottomMargin=55,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#2563EB"),
        spaceAfter=12,
    )
    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )
    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
        spaceBefore=6,
        spaceAfter=2,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#334155"),
        spaceAfter=4,
    )
    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.8,
        leading=10,
        textColor=colors.HexColor("#334155"),
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2,
    )
    callout_style = ParagraphStyle(
        "Callout_Text",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#1E293B"),
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#1E293B"),
    )
    table_header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.8,
        leading=10,
        textColor=colors.white,
    )

    story = []

    # ==================== PAGE 1 ====================
    story.append(Paragraph("System Architecture & Production Design", title_style))
    story.append(Paragraph("GraphOne / FrontierAtlas — Global AI Intelligence Graph Platform", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#3B82F6"), spaceAfter=8))

    story.append(Paragraph("1. Scale Strategy: Ingesting 500,000+ Multi-Dimensional Records", h1_style))
    story.append(Paragraph(
        "Scaling ingestion to 500,000+ records without manual intervention requires transitioning from "
        "single-node asynchronous scrapers to a partitioned, event-driven distributed pipeline built on "
        "<b>Apache Kafka</b>, <b>Ray Core</b> worker pools, and an adaptive proxy/TLS impersonation mesh.",
        body_style
    ))

    # Architecture Pipeline Table
    flow_data = [
        [Paragraph("Pipeline Stage", table_header), Paragraph("Underlying Technology", table_header), Paragraph("Scaling & Concurrency Strategy", table_header)],
        [
            Paragraph("<b>Frontier Scheduler</b>", table_cell),
            Paragraph("Apache Kafka + Redis", table_cell),
            Paragraph("URL queues partitioned by domain hash (<code>hash(host) % N</code>). Domain-level rate limit isolation.", table_cell)
        ],
        [
            Paragraph("<b>Async Crawler Mesh</b>", table_cell),
            Paragraph("Python <code>asyncio</code> + <code>curl_cffi</code>", table_cell),
            Paragraph("JA3/JA4 TLS fingerprint spoofing; dynamic residential proxy mesh; automatic 403/429 IP eviction.", table_cell)
        ],
        [
            Paragraph("<b>Heavy SPA Engine</b>", table_cell),
            Paragraph("Playwright Headless Pool", table_cell),
            Paragraph("Browser context pooling for JS-rendered apps; intercepts raw GraphQL/XHR JSON responses directly.", table_cell)
        ],
        [
            Paragraph("<b>LLM Extraction Pool</b>", table_cell),
            Paragraph("Ray Tasks + Central Redis Governor", table_cell),
            Paragraph("Distributed token bucket throttler; semantic densifier preventing 413s; multi-tier fallback cascade.", table_cell)
        ],
        [
            Paragraph("<b>Deterministic Entity Engine</b>", table_cell),
            Paragraph("Ray Cluster + Jaro-Winkler", table_cell),
            Paragraph("Inverted index alias matching, legal suffix normalization, fuzzy token set resolution in &lt;2ms/record.", table_cell)
        ],
        [
            Paragraph("<b>Polyglot Storage</b>", table_cell),
            Paragraph("PostgreSQL + ClickHouse + Neo4j", table_cell),
            Paragraph("Dual write: ACID relational metadata in Postgres, columnar time-series in ClickHouse, KG in Neo4j.", table_cell)
        ],
    ]
    t_flow = Table(flow_data, colWidths=[110, 130, 264])
    t_flow.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F8FAFC"), colors.white]),
    ]))
    story.append(t_flow)
    story.append(Spacer(1, 6))

    story.append(Paragraph("Core Pillars of 500k+ Data Acquisition", h2_style))
    story.append(Paragraph("• <b>Domain-Partitioned Concurrency:</b> Isolating requests by target hostname prevents slow or throttled targets (e.g. ArXiv) from causing head-of-line blocking for fast targets (e.g. YC, Job boards).", bullet_style))
    story.append(Paragraph("• <b>TLS Impersonation & Anti-Bot Navigation:</b> Datadome and Cloudflare Turnstile actively detect Python <code>aiohttp</code> TLS signatures. Using <code>curl_cffi</code> impersonates genuine Chrome 128/Firefox TLS handshakes and HTTP/2 settings.", bullet_style))
    story.append(Paragraph("• <b>Automatic Dead-Letter Queue (DLQ):</b> Crawling failures that exceed max retries are automatically shunted to a Kafka DLQ for offline analysis and specialized headless replay.", bullet_style))

    # ==================== PAGE 2 ====================
    story.append(PageBreak())

    story.append(Paragraph("2. Resilient LLM Extraction: Managing 413s & 429s at Scale", h1_style))
    story.append(Paragraph(
        "At thousands of concurrent extractions, LLM pipelines face strict rate envelopes (TPM/RPM) "
        "and payload context boundaries. Our multi-tier architecture prevents failures before they reach the provider.",
        body_style
    ))

    story.append(Paragraph("A. Prevention of HTTP 413 (Payload Too Large)", h2_style))
    story.append(Paragraph("• <b>DOM Stripping & Semantic Densification:</b> Pre-processing strips scripts, CSS, navigation bars, ads, and footers. Only semantic elements (<code>&lt;article&gt;</code>, <code>&lt;h1-h3&gt;</code>, <code>&lt;p&gt;</code>, meta tags) are preserved, reducing payload size by 75-90%.", bullet_style))
    story.append(Paragraph("• <b>Token Budget Governor:</b> Payload length is constrained to <code>min(Model Context, 4000 tokens) - Prompt Reserve</code>. Inputs exceeding this ceiling undergo sentence-boundary lookback truncation, preserving semantic integrity without mid-word cuts.", bullet_style))
    story.append(Paragraph("• <b>Hierarchical Map-Reduce:</b> Long multi-page documents (whitepapers, lengthy filings) are chunked into 2,000-token sections, processed in parallel, and consolidated through a structured merge step.", bullet_style))

    story.append(Paragraph("B. Resilience Against HTTP 429 (Rate Limits & Throttling)", h2_style))
    story.append(Paragraph("• <b>Centralized Token Bucket Governor (Redis):</b> Workers reserve tokens prior to invocation against per-provider RPM/TPM sliding windows, stopping rate limit violations proactively.", bullet_style))
    story.append(Paragraph("• <b>Decorrelated Full Jitter Backoff:</b> When encountering a 429: <code>delay = Uniform(0.5, 1.5) * min(MaxDelay, Base * 2^attempt)</code>. This spreads retry bursts uniformly, preventing synchronized thundering-herd spikes across workers.", bullet_style))
    story.append(Paragraph("• <b>Multi-Tier Failover Cascade:</b>", bullet_style))

    # LLM Cascade Table
    llm_cascade_data = [
        [Paragraph("Tier", table_header), Paragraph("Provider / Model", table_header), Paragraph("Role & Failover Condition", table_header), Paragraph("Latency / Cost", table_header)],
        [
            Paragraph("<b>Tier 1</b>", table_cell),
            Paragraph("Gemini 1.5 / 2.0 Flash", table_cell),
            Paragraph("Primary high-throughput JSON extraction. Active provider.", table_cell),
            Paragraph("&lt;400ms / $0.075/1M tok", table_cell)
        ],
        [
            Paragraph("<b>Tier 2</b>", table_cell),
            Paragraph("Groq Llama 3.3 70B", table_cell),
            Paragraph("Failover on Gemini 429, quota exhaustion, or timeout &gt;4s.", table_cell),
            Paragraph("&lt;280ms / $0.59/1M tok", table_cell)
        ],
        [
            Paragraph("<b>Tier 3</b>", table_cell),
            Paragraph("DeepSeek Chat", table_cell),
            Paragraph("Failover if Tier 1 &amp; Tier 2 are saturated. Deep structural reasoning.", table_cell),
            Paragraph("&lt;750ms / $0.14/1M tok", table_cell)
        ],
        [
            Paragraph("<b>Tier 4</b>", table_cell),
            Paragraph("Deterministic Heuristic Parser", table_cell),
            Paragraph("Zero-downtime safety net. Extracts schema via regex and DOM rules.", table_cell),
            Paragraph("&lt;2ms / $0.00", table_cell)
        ],
    ]
    t_llm = Table(llm_cascade_data, colWidths=[55, 125, 204, 120])
    t_llm.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F8FAFC"), colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_llm)
    story.append(Spacer(1, 6))

    story.append(Paragraph("3. Freshness Tracking: Zero-Duplicate Distributed Crawling", h1_style))
    story.append(Paragraph(
        "Guaranteeing that no article or job posting is processed twice within the 24-hour freshness window "
        "requires a multi-tier deduplication filter operating across memory, network, and database layers.",
        body_style
    ))
    story.append(Paragraph("• <b>Canonical URL Normalization:</b> Strips query trackers (UTMs, fbclid, session IDs), removes trailing slashes, normalizes protocols, and resolves canonical redirects.", bullet_style))
    story.append(Paragraph("• <b>Distributed Bloom Filter (RedisBloom):</b> Sub-millisecond lookup checks seen URLs with &lt;0.01% false positive probability across thousands of crawler nodes.", bullet_style))
    story.append(Paragraph("• <b>SimHash / MinHash Content Fingerprinting:</b> Syndicated articles often share identical text across different domains. 64-bit SimHash identifies semantic duplicates where Hamming Distance &le; 3.", bullet_style))
    story.append(Paragraph("• <b>Idempotency Database Constraints:</b> PostgreSQL partial unique indices enforce: <code>UNIQUE(canonical_entity_id, hash(job_title), publication_date::date)</code>.", bullet_style))

    # ==================== PAGE 3 ====================
    story.append(PageBreak())

    story.append(Paragraph("4. Storage Strategy: Polyglot Multi-Model Intelligence Architecture", h1_style))
    story.append(Paragraph(
        "The GraphOne venture ecosystem exhibits four conflicting access patterns: transactional entity records, "
        "high-velocity signal streams, dense embedding vectors, and multi-hop relationship graphs. "
        "We implement a polyglot persistence architecture optimized for each workload.",
        body_style
    ))

    # Storage Strategy Table
    storage_data = [
        [Paragraph("Database Engine", table_header), Paragraph("Workload & Entities", table_header), Paragraph("Architectural Justification", table_header)],
        [
            Paragraph("<b>PostgreSQL 16</b><br/>(Primary Relational)", table_cell),
            Paragraph("• Startups Core Records<br/>• Canonical Products<br/>• Entity Resolution Mappings<br/>• Pipeline Execution State", table_cell),
            Paragraph("ACID compliance guarantees data integrity during concurrent entity resolution. JSONB columns accommodate rapidly evolving startup attributes without disruptive schema migrations. Connection pooling via PgBouncer.", table_cell)
        ],
        [
            Paragraph("<b>ClickHouse</b><br/>(Real-Time Analytics)", table_cell),
            Paragraph("• 24h News Signal Streams<br/>• Job Market Postings<br/>• GitHub Star Time-Series<br/>• Crawler Telemetry Logs", table_cell),
            Paragraph("Columnar compression achieves up to 80% storage savings on repetitive strings. Ingests 250,000+ rows/sec per node. Sub-second analytical queries (e.g. <i>'Compute star velocity across 10,000 ML papers over 90 days'</i>).", table_cell)
        ],
        [
            Paragraph("<b>Neo4j Enterprise</b><br/>(Graph Database)", table_cell),
            Paragraph("• Intelligence Knowledge Graph<br/>• Founder-Startup-Product Links<br/>• Citation & Dependency Networks", table_cell),
            Paragraph("Index-free adjacency provides constant-time $O(1)$ traversal per hop. Relational JOINs across 5 levels degrade exponentially; Neo4j executes complex graph pattern matching in milliseconds.", table_cell)
        ],
        [
            Paragraph("<b>Qdrant / Pgvector</b><br/>(Vector Search)", table_cell),
            Paragraph("• Entity Semantic Embeddings<br/>• Article & Paper Summaries<br/>• Fuzzy Semantic Matching", table_cell),
            Paragraph("HNSW index enables semantic search: <i>'Find startups building autonomous synthetic data pipelines'</i> even without exact keyword overlaps.", table_cell)
        ],
    ]
    t_storage = Table(storage_data, colWidths=[110, 150, 244])
    t_storage.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F8FAFC"), colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    story.append(t_storage)
    story.append(Spacer(1, 6))

    story.append(Paragraph("5. Target Canonical Data Schemas", h1_style))
    story.append(Paragraph(
        "All ingested and resolved records adhere to strict, versioned schemas matching GraphOne specifications:",
        body_style
    ))

    # Schema summary callout
    schema_summary = [
        [
            Paragraph("<b>Startup Entity</b>", table_cell),
            Paragraph("<code>schemaVersion, recordType='STARTUP', source.name, source.url, content.entityName, content.data.employeeCount, collectedAt</code>", table_cell)
        ],
        [
            Paragraph("<b>Product Entity</b>", table_cell),
            Paragraph("<code>schemaVersion, recordType='PRODUCT', source.name, source.url, content.startupName, content.pricingModel (FREE|FREEMIUM|PAID|ENTERPRISE), collectedAt</code>", table_cell)
        ],
        [
            Paragraph("<b>Research Paper</b>", table_cell),
            Paragraph("<code>schemaVersion, recordType='RESEARCH_PAPER', content.title, content.authors, content.paper_url, content.github_url, content.github_stars, content.published_date</code>", table_cell)
        ],
        [
            Paragraph("<b>Job Entity</b>", table_cell),
            Paragraph("<code>schemaVersion, recordType='JOB', source.name, content.company, content.date (&lt;24h), content.is_remote, content.role_family</code>", table_cell)
        ],
    ]
    t_sch = Table(schema_summary, colWidths=[110, 394])
    t_sch.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    story.append(t_sch)
    story.append(Spacer(1, 6))

    story.append(Paragraph("6. Compliance & Zero-Hallucination Guarantee", h1_style))
    story.append(Paragraph(
        "Every single record in the Intelligence Graph is grounded in an authentic source URL verified during ingestion. "
        "Raw HTTP responses and timestamps are preserved in immutable audit storage, guaranteeing complete lineage "
        "and reproducible trace-back for all 500,000+ entities.",
        body_style
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Architecture PDF generated at: {OUTPUT_PDF.resolve()}")


if __name__ == "__main__":
    build_pdf()
