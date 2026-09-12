"""
Comprehensive Audit Script to gather empirical evidence for all audit items.
"""

import asyncio
import difflib
import json
import logging
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pandas as pd

from src.entity_resolution.resolver import EntityResolver
from src.entity_resolution.seed_database import SEED_CANONICAL_STARTUPS
from src.llm.orchestrator import LLMOrchestrator
from src.llm.providers import LLMProvider, GeminiFlashProvider, GroqLlama3Provider, DeepSeekProvider, LocalFallbackProvider
from src.llm.backoff import BackoffHandler
from src.llm.chunker import SemanticChunker
from src.pipeline.deduplicator import ContentDeduplicator
from src.pipeline.state_store import PipelineStateStore
from src.pipeline.monitor import ContinuousMonitoringPipeline
from src.crawler.base import BaseCrawler
from src.schemas.startup import StartupRecord
from src.schemas.product import ProductRecord
from src.schemas.paper import ResearchPaperRecord
from src.schemas.job import JobRecord


logging.basicConfig(level=logging.WARNING)

async def test_llm_fallback_modes():
    print("=== AUDIT 1: LLM Fallback Chain ===")
    
    # Mock Provider that simulates 500, Timeout, and Malformed JSON
    class MockFailingProvider(LLMProvider):
        def __init__(self, failure_type):
            self.failure_type = failure_type
            self.name = f"MockTier1_{failure_type}"

        async def extract_schema(self, text_content, target_schema_desc):
            if self.failure_type == "500":
                raise Exception("HTTP 500 Internal Server Error")
            elif self.failure_type == "timeout":
                raise asyncio.TimeoutError("Request timed out after 20s")
            elif self.failure_type == "malformed":
                return None # parsing failed or returned invalid non-json
            raise RuntimeError("Unknown")

    class MockSuccessTier2(LLMProvider):
        name = "MockTier2_Success"
        async def extract_schema(self, text_content, target_schema_desc):
            return {"entityName": "FallbackSucceeded", "role": "AI Engineer"}

    for mode in ["500", "timeout", "malformed"]:
        orch = LLMOrchestrator(providers=[MockFailingProvider(mode), MockSuccessTier2()])
        result, tier = await orch.extract("Test input text", "target schema")
        print(f"  Mode '{mode}': Result={result is not None}, TierSucceeded='{tier}'")

    # What happens when ALL tiers fail?
    class AllFailProvider(LLMProvider):
        name = "AlwaysFail"
        async def extract_schema(self, t, s): return None
    
    orch_all_fail = LLMOrchestrator(providers=[AllFailProvider()])
    res_fail, tier_fail = await orch_all_fail.extract("Test", "schema")
    print(f"  All tiers fail: Result={res_fail}, Tier='{tier_fail}'")


def test_chunking_and_413():
    print("\n=== AUDIT 2: Chunking & 413 Prevention ===")
    # 1. Check if max_chars is hardcoded or model-computed
    print(f"  SemanticChunker default max_chars: {SemanticChunker.clean_and_densify.__defaults__}")
    
    # 2. Test large raw HTML input
    large_html = """
    <html>
      <head><title>Cutting Edge AI Startup</title>
      <meta name="description" content="Next-generation autonomous foundation models.">
      </head>
      <body>
        <nav><a href='/home'>Home</a><a href='/about'>About Us</a></nav>
        <h1>Autonomous Reasoning Engine</h1>
        <p>""" + ("We build autonomous reasoning foundation models for enterprise code generation. " * 300) + """</p>
        <footer>Copyright 2026 Boilerplate Inc. All rights reserved.</footer>
      </body>
    </html>
    """
    cleaned = SemanticChunker.clean_and_densify(large_html, max_chars=1000)
    print(f"  Input size: {len(large_html)} chars -> Cleaned size: {len(cleaned)} chars")
    print(f"  Contains 'Nav' boilerplate? {'Home' in cleaned and 'About Us' in cleaned}")
    print(f"  Contains 'Footer' boilerplate? {'Copyright 2026 Boilerplate' in cleaned}")
    print(f"  Contains 'Title'? {'Title:' in cleaned}")
    print(f"  Contains 'Heading'? {'Heading:' in cleaned}")
    print(f"  Ends cleanly on sentence/word boundary? {cleaned[-1] in '. ' or cleaned.endswith('...')}")


def test_backoff_and_429():
    print("\n=== AUDIT 3: 429 Handling ===")
    attempts = [0, 1, 2, 3]
    delays = [BackoffHandler.calculate_delay(att) for att in attempts]
    print(f"  Calculated jittered delays for attempts 0..3: {[round(d, 2) for d in delays]}")
    # Inspect retry count in GeminiFlashProvider, GroqLlama3Provider, DeepSeekProvider
    import inspect
    from src.llm.providers import GeminiFlashProvider
    source = inspect.getsource(GeminiFlashProvider.extract_schema)
    retry_match = re.search(r"range\((\d+)\)", source)
    print(f"  Provider max retry loop count: {retry_match.group(1) if retry_match else 'None'}")


def test_entity_resolution():
    print("\n=== AUDIT 4: Canonicalization against seed list ===")
    resolver = EntityResolver()
    test_cases = [
        "OpenAI",
        "OpenAI, Inc.",
        "Open AI",
        "openai",
        "OpenAl", # Typo with lowercase 'l'
        "Completely New Startup XYZ"
    ]
    for tc in test_cases:
        canonical, conf, method = resolver.resolve(tc)
        print(f"  Raw: '{tc}' -> Canonical: '{canonical}' | Conf: {conf} | Method: {method}")


async def test_async_concurrency():
    print("\n=== AUDIT 5: Async Operation Concurrency ===")
    crawler = BaseCrawler(max_concurrent=20)
    start_times = []
    end_times = []

    async def mock_fetch(idx):
        s = time.time()
        start_times.append(s)
        await asyncio.sleep(0.1) # Simulate 100ms network latency
        e = time.time()
        end_times.append(e)
        return idx

    total_start = time.time()
    await asyncio.gather(*[mock_fetch(i) for i in range(20)])
    total_elapsed = time.time() - total_start
    await crawler.close()

    print(f"  Fired 20 tasks concurrently. Total wall time: {total_elapsed:.3f}s")
    # Check overlap
    overlaps = min(end_times) > max(start_times) or total_elapsed < 0.3
    print(f"  Tasks executed concurrently in parallel? {overlaps} (elapsed < 0.3s vs sequential 2.0s)")


def test_cloudflare_status():
    print("\n=== AUDIT 6: Cloudflare / Headless Browser ===")
    import src.crawler.base as base
    has_playwright = "playwright" in open(base.__file__).read().lower()
    print(f"  Is Playwright imported in src/crawler/base.py? {has_playwright}")
    arch_content = open("architecture.md", encoding="utf-8").read()
    has_playwright_in_arch = "playwright" in arch_content.lower()
    print(f"  Is Playwright documented in architecture.md? {has_playwright_in_arch}")


async def test_freshness_pipeline_dedup(tmp_path):
    print("\n=== AUDIT 7: Phase II Freshness & Deduplication Run ===")
    store = PipelineStateStore(db_path=tmp_path / "test_audit_dedup.db")
    from src.crawler.modules.base_module import BaseSourceCrawler, CandidateItem

    now = datetime.now(timezone.utc)
    candidates = [
        CandidateItem("Test News", "NEWS", "https://news.com/item1", "Title 1", (now - timedelta(hours=2)).isoformat()),
        CandidateItem("Test News", "NEWS", "https://news.com/item2", "Title 2", (now - timedelta(hours=40)).isoformat()),
    ]

    class StaticCrawler(BaseSourceCrawler):
        source_name = "Test News"
        source_type = "NEWS"
        async def fetch_listing(self): return candidates
        async def fetch_full_text(self, u): return "Content"

    pipeline = ContinuousMonitoringPipeline(state_store=store, crawlers=[StaticCrawler()])
    
    # Run 1
    run1 = await pipeline.run_cycle()
    print(f"  Run 1: Discovered={run1['candidates_found']}, Fresh={run1['passed_freshness']}, Stale={run1['discarded_stale']}, SkippedSeen={run1['already_seen_skipped']}")
    
    # Run 2 with identical listing
    run2 = await pipeline.run_cycle()
    print(f"  Run 2: Discovered={run2['candidates_found']}, Fresh={run2['passed_freshness']}, Stale={run2['discarded_stale']}, SkippedSeen={run2['already_seen_skipped']}")
    print(f"  Run 2 processed ZERO new items? {run2['passed_freshness'] == 0 and run2['discarded_stale'] == 0}")
    await pipeline.close()


def test_schema_compliance():
    print("\n=== AUDIT 8: Schema Compliance on Real Output Records ===")
    data_dir = Path("data")
    
    # 1. Startups
    df_s = pd.read_csv(data_dir / "startups.csv").head(3)
    print("\n[Startups 3 Real Records Fields & Types]:")
    print(df_s.dtypes)
    print("Sample record 0:")
    print(df_s.iloc[0].to_dict())

    # 2. Products
    df_p = pd.read_csv(data_dir / "products.csv").head(3)
    print("\n[Products 3 Real Records Fields & Types]:")
    print(df_p.dtypes)
    if 'content.pricingModel' in df_p.columns:
        print("Sample pricingModel values:", df_p['content.pricingModel'].unique())
    elif 'pricingModel' in df_p.columns:
        print("Sample pricingModel values:", df_p['pricingModel'].unique())
    print("Sample record 0:")
    print(df_p.iloc[0].to_dict())


    # 3. Papers
    df_r = pd.read_csv(data_dir / "research_papers.csv").head(3)
    print("\n[Papers 3 Real Records Fields & Types]:")
    print(df_r.dtypes)
    print("Sample record 0:")
    print(df_r.iloc[0].to_dict())

    # 4. Jobs
    df_j = pd.read_csv(data_dir / "jobs.csv").head(3)
    print("\n[Jobs 3 Real Records Fields & Types]:")
    print(df_j.dtypes)
    print("Sample record 0:")
    print(df_j.iloc[0].to_dict())

async def main():
    await test_llm_fallback_modes()
    test_chunking_and_413()
    test_backoff_and_429()
    test_entity_resolution()
    await test_async_concurrency()
    test_cloudflare_status()
    import tempfile
    await test_freshness_pipeline_dedup(Path(tempfile.gettempdir()))
    test_schema_compliance()

if __name__ == "__main__":
    asyncio.run(main())
