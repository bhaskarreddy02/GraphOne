"""
Unit tests for Persistent State Store (SQLite WAL mode)
Verifies per-source tracking, immediate persistence, deduplication checks, and crash survival.
"""

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from src.pipeline.state_store import PipelineStateStore


@pytest.fixture
def temp_store(tmp_path):
    db_path = tmp_path / "test_pipeline_state.db"
    return PipelineStateStore(db_path=db_path)


def test_init_and_wal_mode(temp_store):
    with temp_store._get_connection() as conn:
        cur = conn.execute("PRAGMA journal_mode;")
        row = cur.fetchone()
        assert row[0].lower() == "wal"


def test_immediate_seen_persistence(temp_store):
    source = "TechCrunch AI"
    item_hash = "abc123hash"
    url = "https://techcrunch.com/article-1"
    title = "OpenAI Releases New Model"

    assert not temp_store.is_hash_seen(source, item_hash)

    # Record seen item immediately
    inserted = temp_store.record_seen_item(
        source_name=source,
        item_hash=item_hash,
        canonical_url=url,
        title=title,
        published_date=datetime.now(timezone.utc).isoformat(),
        passed_freshness=True
    )
    assert inserted is True

    # Check immediate visibility
    assert temp_store.is_hash_seen(source, item_hash) is True
    seen_set = temp_store.get_seen_hashes(source)
    assert item_hash in seen_set

    # Second insert should be ignored without error
    inserted_again = temp_store.record_seen_item(
        source_name=source,
        item_hash=item_hash,
        canonical_url=url,
        title=title,
        passed_freshness=True
    )
    assert inserted_again is True


def test_source_state_tracking(temp_store):
    source = "RemoteOK"
    now = datetime.now(timezone.utc)

    # Initial state should be None
    assert temp_store.get_last_run(source) is None

    # Update completion
    temp_store.update_source_run_completed(
        source_name=source,
        source_type="JOB",
        run_timestamp=now,
        status="SUCCESS"
    )

    last_run = temp_store.get_last_run(source)
    assert last_run is not None
    assert abs((last_run - now).total_seconds()) < 2


def test_crawl_run_logging(temp_store):
    run_id = "run_test_001"
    start = datetime.now(timezone.utc) - timedelta(seconds=15)
    end = datetime.now(timezone.utc)

    temp_store.log_crawl_run(
        run_id=run_id,
        start_time=start,
        end_time=end,
        sources_checked=10,
        new_items_found=25,
        passed_freshness=18,
        discarded_stale=7,
        failures_count=0,
        status="SUCCESS",
        summary_data={"notes": "test cycle"}
    )

    recent = temp_store.get_recent_runs(limit=5)
    assert len(recent) == 1
    assert recent[0]["run_id"] == run_id
    assert recent[0]["passed_freshness"] == 18
    assert recent[0]["discarded_stale"] == 7
    assert recent[0]["status"] == "SUCCESS"
