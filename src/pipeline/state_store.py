"""
Persistent State Store for Continuous News & Jobs Pipeline
Tracks per-source run timestamps, seen content hashes, and cycle audit logs in SQLite (WAL mode).
"""

import json
import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Set, Dict, Any, List
from src.config import DATA_DIR

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = DATA_DIR / "pipeline_state.db"


class PipelineStateStore:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode and normal synchronous for fast concurrent reads and crash-safe writes
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        """Initializes tables for source state, seen items, and run audit logs."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS source_state (
                    source_name TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    last_run_timestamp TEXT,
                    total_seen_count INTEGER DEFAULT 0,
                    last_status TEXT
                );

                CREATE TABLE IF NOT EXISTS seen_items (
                    item_hash TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    canonical_url TEXT,
                    title TEXT,
                    first_seen_timestamp TEXT NOT NULL,
                    published_date TEXT,
                    passed_freshness INTEGER DEFAULT 0,
                    heuristic_used INTEGER DEFAULT 0,
                    PRIMARY KEY (item_hash, source_name)
                );

                CREATE INDEX IF NOT EXISTS idx_seen_source ON seen_items(source_name);
                CREATE INDEX IF NOT EXISTS idx_seen_time ON seen_items(first_seen_timestamp);

                CREATE TABLE IF NOT EXISTS crawl_run_logs (
                    run_id TEXT PRIMARY KEY,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    sources_checked INTEGER DEFAULT 0,
                    new_items_found INTEGER DEFAULT 0,
                    passed_freshness INTEGER DEFAULT 0,
                    discarded_stale INTEGER DEFAULT 0,
                    failures_count INTEGER DEFAULT 0,
                    status TEXT NOT NULL,
                    summary_json TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_run_time ON crawl_run_logs(start_time DESC);
            """)

    def get_last_run(self, source_name: str) -> Optional[datetime]:
        """Returns the last successful run timestamp for a specific source."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT last_run_timestamp FROM source_state WHERE source_name = ?",
                (source_name,)
            )
            row = cur.fetchone()
            if row and row["last_run_timestamp"]:
                try:
                    return datetime.fromisoformat(row["last_run_timestamp"])
                except Exception:
                    return None
            return None

    def get_seen_hashes(self, source_name: str) -> Set[str]:
        """Loads all historical seen hashes for a specific source into an in-memory set."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT item_hash FROM seen_items WHERE source_name = ?",
                (source_name,)
            )
            return {row["item_hash"] for row in cur.fetchall()}

    def is_hash_seen(self, source_name: str, item_hash: str) -> bool:
        """Checks if an item hash has been seen previously for this source."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT 1 FROM seen_items WHERE source_name = ? AND item_hash = ? LIMIT 1",
                (source_name, item_hash)
            )
            return cur.fetchone() is not None

    def record_seen_item(
        self,
        source_name: str,
        item_hash: str,
        canonical_url: str,
        title: str,
        published_date: Optional[str] = None,
        passed_freshness: bool = False,
        heuristic_used: bool = False
    ) -> bool:
        """
        Immediately persists a seen item to SQLite.
        Guarantees that if the pipeline crashes mid-run, this item is never re-processed.
        Returns True if inserted, False if already existed.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO seen_items 
                    (item_hash, source_name, canonical_url, title, first_seen_timestamp, published_date, passed_freshness, heuristic_used)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item_hash,
                        source_name,
                        canonical_url,
                        title,
                        now_iso,
                        published_date,
                        1 if passed_freshness else 0,
                        1 if heuristic_used else 0
                    )
                )
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error persisting seen item {item_hash} for {source_name}: {e}")
                return False

    def update_source_run_completed(
        self,
        source_name: str,
        source_type: str,
        run_timestamp: datetime,
        status: str = "SUCCESS"
    ):
        """Updates the last run timestamp and status for a source."""
        iso_str = run_timestamp.isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO source_state (source_name, source_type, last_run_timestamp, last_status, total_seen_count)
                VALUES (?, ?, ?, ?, (SELECT count(*) FROM seen_items WHERE source_name = ?))
                ON CONFLICT(source_name) DO UPDATE SET
                    last_run_timestamp = excluded.last_run_timestamp,
                    last_status = excluded.last_status,
                    total_seen_count = (SELECT count(*) FROM seen_items WHERE source_name = excluded.source_name)
                """,
                (source_name, source_type, iso_str, status, source_name)
            )
            conn.commit()

    def log_crawl_run(
        self,
        run_id: str,
        start_time: datetime,
        end_time: datetime,
        sources_checked: int,
        new_items_found: int,
        passed_freshness: int,
        discarded_stale: int,
        failures_count: int,
        status: str,
        summary_data: Optional[Dict[str, Any]] = None
    ):
        """Records a comprehensive crawl run audit entry."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO crawl_run_logs
                (run_id, start_time, end_time, sources_checked, new_items_found, passed_freshness, discarded_stale, failures_count, status, summary_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    start_time.isoformat(),
                    end_time.isoformat(),
                    sources_checked,
                    new_items_found,
                    passed_freshness,
                    discarded_stale,
                    failures_count,
                    status,
                    json.dumps(summary_data or {})
                )
            )
            conn.commit()

    def get_recent_runs(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Returns recent crawl run history for monitoring."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM crawl_run_logs ORDER BY start_time DESC LIMIT ?",
                (limit,)
            )
            rows = cur.fetchall()
            results = []
            for row in rows:
                d = dict(row)
                if d.get("summary_json"):
                    try:
                        d["summary"] = json.loads(d["summary_json"])
                    except Exception:
                        d["summary"] = {}
                results.append(d)
            return results

    def get_all_source_states(self) -> List[Dict[str, Any]]:
        """Returns the current state of all registered sources."""
        with self._get_connection() as conn:
            cur = conn.execute(
                """
                SELECT s.source_name, s.source_type, s.last_run_timestamp, s.last_status,
                       count(i.item_hash) as total_seen
                FROM source_state s
                LEFT JOIN seen_items i ON s.source_name = i.source_name
                GROUP BY s.source_name, s.source_type, s.last_run_timestamp, s.last_status
                """
            )
            return [dict(r) for r in cur.fetchall()]
