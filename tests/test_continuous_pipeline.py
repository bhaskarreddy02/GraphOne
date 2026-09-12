"""
Integration and behavioral tests for Continuous Monitoring Pipeline (Phase II)
Verifies:
1. Two separate filters: (a) new-since-last-run AND (b) published-within-24h
2. Stale items discarded but marked as seen so they are never re-checked
3. Fallback freshness heuristic when no date exists
4. Deduplication prevents re-extraction on repeated runs
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import List

from src.pipeline.state_store import PipelineStateStore
from src.pipeline.monitor import ContinuousMonitoringPipeline
from src.crawler.modules.base_module import BaseSourceCrawler, CandidateItem
from src.crawler.date_normalizer import DateNormalizer


class MockNewsCrawler(BaseSourceCrawler):
    source_name = "Mock News AI"
    source_type = "NEWS"

    def __init__(self, candidates: List[CandidateItem]):
        super().__init__()
        self.mock_candidates = candidates

    async def fetch_listing(self) -> List[CandidateItem]:
        return self.mock_candidates

    async def fetch_full_text(self, url: str) -> str:
        return f"Full text body content for article at {url}. AI breakthroughs continue."


@pytest.mark.asyncio
async def test_two_separate_filters_fresh_and_stale(tmp_path):
    """
    Validates that:
    - Fresh items (< 24h) pass and get processed.
    - Stale items (> 24h) are discarded from results, BUT are still persisted in SQLite
      as 'seen' so they are not re-processed on subsequent runs.
    """
    store = PipelineStateStore(db_path=tmp_path / "test_pipeline.db")
    now = datetime.now(timezone.utc)

    fresh_item = CandidateItem(
        source_name="Mock News AI",
        source_type="NEWS",
        url="https://mocknews.ai/fresh-article",
        title="Fresh AI Breakthrough",
        raw_date_str=(now - timedelta(hours=3)).isoformat()
    )

    stale_item = CandidateItem(
        source_name="Mock News AI",
        source_type="NEWS",
        url="https://mocknews.ai/stale-article",
        title="Older AI History Article",
        raw_date_str=(now - timedelta(hours=48)).isoformat()
    )

    crawler = MockNewsCrawler([fresh_item, stale_item])
    pipeline = ContinuousMonitoringPipeline(state_store=store, crawlers=[crawler])

    # Run Cycle 1
    summary = await pipeline.run_cycle()

    assert summary["candidates_found"] == 2
    assert summary["passed_freshness"] == 1
    assert summary["discarded_stale"] == 1
    assert summary["fresh_records_count"] == 1

    # Verify both items are now in seen_items in SQLite
    seen_hashes = store.get_seen_hashes("Mock News AI")
    assert len(seen_hashes) == 2

    # Run Cycle 2 with identical listing: both must be skipped as ALREADY_SEEN
    summary_2 = await pipeline.run_cycle()
    assert summary_2["candidates_found"] == 2
    assert summary_2["already_seen_skipped"] == 2
    assert summary_2["passed_freshness"] == 0
    assert summary_2["discarded_stale"] == 0


@pytest.mark.asyncio
async def test_fallback_freshness_heuristic_for_dateless_item(tmp_path):
    """
    Tests rule:
    'If no date signal exists at all: heuristic = if this item's dedup-hash was NOT
    in the seen-set as of last_run_timestamp, treat it as new-since-last-run'
    """
    store = PipelineStateStore(db_path=tmp_path / "test_pipeline.db")

    dateless_item = CandidateItem(
        source_name="Mock News AI",
        source_type="NEWS",
        url="https://mocknews.ai/no-date-article",
        title="Mysterious Dateless Announcement",
        raw_date_str=None  # No date signal
    )

    crawler = MockNewsCrawler([dateless_item])
    pipeline = ContinuousMonitoringPipeline(state_store=store, crawlers=[crawler])

    summary = await pipeline.run_cycle()

    # The dateless item was unseen, so the heuristic triggers and marks it fresh
    assert summary["candidates_found"] == 1
    assert summary["passed_freshness"] == 1
    assert summary["discarded_stale"] == 0

    # In cycle 2, it is already seen, so it is skipped
    summary_2 = await pipeline.run_cycle()
    assert summary_2["already_seen_skipped"] == 1
    assert summary_2["passed_freshness"] == 0
