"""
Continuous News & Jobs Monitoring Pipeline (Phase II)
Enforces:
1. Persistent state store tracking last_run_timestamp and seen hashes.
2. 10 modular crawlers (5 news + 5 job boards) with isolated error boundaries.
3. Deduplication check BEFORE extraction or LLM calls.
4. Structured date normalization + relative parsing + unseen heuristic fallback.
5. 24-hour freshness filter (stale items discarded and marked seen).
6. Immediate per-item persistence to survive crashes.
7. Multi-tier LLM extraction with ambiguity escalation.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.pipeline.state_store import PipelineStateStore
from src.pipeline.deduplicator import ContentDeduplicator
from src.crawler.date_normalizer import DateNormalizer
from src.crawler.modules.base_module import BaseSourceCrawler, CandidateItem
from src.crawler.modules.news.techcrunch import TechCrunchCrawler
from src.crawler.modules.news.mit_tech_review import MITTechReviewCrawler
from src.crawler.modules.news.ai_news import AINewsCrawler
from src.crawler.modules.news.wired import WiredCrawler
from src.crawler.modules.news.ars_technica import ArsTechnicaCrawler
from src.crawler.modules.jobs.remoteok import RemoteOKCrawler
from src.crawler.modules.jobs.remotive import RemotiveCrawler
from src.crawler.modules.jobs.weworkremotely import WeWorkRemotelyCrawler
from src.crawler.modules.jobs.jobicy import JobicyCrawler
from src.crawler.modules.jobs.hn_jobs import HNJobsCrawler
from src.llm.orchestrator import LLMOrchestrator
from src.schemas.news import NewsRecord, NewsContent
from src.schemas.job import JobRecord, JobContent
from src.schemas.startup import SourceMeta
from src.config import DATA_DIR

logger = logging.getLogger("ContinuousPipeline")


class ContinuousMonitoringPipeline:
    def __init__(
        self,
        state_store: Optional[PipelineStateStore] = None,
        llm_orchestrator: Optional[LLMOrchestrator] = None,
        crawlers: Optional[List[BaseSourceCrawler]] = None
    ):
        self.store = state_store or PipelineStateStore()
        self.llm = llm_orchestrator or LLMOrchestrator()

        # Initialize the 10 independent source crawlers
        self.crawlers = crawlers or [
            # 5 News Crawlers
            TechCrunchCrawler(),
            MITTechReviewCrawler(),
            AINewsCrawler(),
            WiredCrawler(),
            ArsTechnicaCrawler(),
            # 5 Job Board Crawlers
            RemoteOKCrawler(),
            RemotiveCrawler(),
            WeWorkRemotelyCrawler(),
            JobicyCrawler(),
            HNJobsCrawler(),
        ]

    async def process_candidate(
        self,
        crawler: BaseSourceCrawler,
        item: CandidateItem,
        seen_hashes: set,
        last_run: Optional[datetime]
    ) -> Optional[Dict[str, Any]]:
        """
        Processes an individual candidate item through Steps 3 -> 4 -> 5 -> 6 -> 7.
        """
        canonical_url = ContentDeduplicator.canonicalize_url(item.url)
        item_hash = ContentDeduplicator.compute_item_hash(
            source_name=crawler.source_name,
            url=canonical_url or item.url,
            title=item.title,
            rough_date=item.raw_date_str
        )
        item.item_hash = item_hash

        # Step 3: Deduplication Check BEFORE expensive full-text extraction or LLM
        if item_hash in seen_hashes or self.store.is_hash_seen(crawler.source_name, item_hash):
            return {"action": "SKIPPED_ALREADY_SEEN", "hash": item_hash}

        # Step 4: Date Normalization & Fallback Heuristic
        resolved_dt = None
        is_fresh = False
        heuristic_used = False

        if item.raw_date_str:
            parsed = DateNormalizer.parse_date(item.raw_date_str)
            if parsed:
                resolved_dt = parsed
                is_fresh = DateNormalizer.is_within_24_hours(parsed)

        # If date is not resolved from listing, fetch full page to inspect structured HTML
        full_text = ""
        if not resolved_dt:
            full_text = await crawler.safe_fetch_full_text(item.url)
            resolved_dt, is_fresh, heuristic_used = DateNormalizer.resolve_date_with_fallback(
                raw_date_str=item.raw_date_str,
                html_content=full_text,
                item_hash=item_hash,
                last_run_timestamp=last_run,
                seen_hashes=seen_hashes
            )

        # Step 5: 24-Hour Freshness Filter
        # Applied AFTER date normalization, independent of dedup check
        iso_date = resolved_dt.isoformat() if resolved_dt else None

        if not is_fresh:
            # DISCARD, but STILL mark as "seen" in SQLite so we don't re-check it forever
            self.store.record_seen_item(
                source_name=crawler.source_name,
                item_hash=item_hash,
                canonical_url=canonical_url,
                title=item.title,
                published_date=iso_date,
                passed_freshness=False,
                heuristic_used=heuristic_used
            )
            seen_hashes.add(item_hash)
            return {"action": "DISCARDED_STALE", "hash": item_hash, "title": item.title}

        # Step 6 & 7: Fresh item confirmed! Proceed to multi-tier extraction
        if not full_text:
            full_text = await crawler.safe_fetch_full_text(item.url)

        content_for_llm = full_text or item.raw_snippet or item.title
        is_ambiguous = heuristic_used or len(content_for_llm) < 120 or not item.metadata.get("company")

        extracted_data, tier_used = await self.llm.extract_with_escalation(
            raw_text_or_html=content_for_llm,
            item_type=crawler.source_type,
            is_ambiguous=is_ambiguous
        )

        # Step 1 immediately persist newly seen items (don't wait until end of run)
        self.store.record_seen_item(
            source_name=crawler.source_name,
            item_hash=item_hash,
            canonical_url=canonical_url,
            title=item.title,
            published_date=iso_date,
            passed_freshness=True,
            heuristic_used=heuristic_used
        )
        seen_hashes.add(item_hash)

        # Build schema record
        extracted_data = extracted_data or {}
        if crawler.source_type == "JOB":
            company = item.metadata.get("company") or extracted_data.get("company") or "Tech Organization"
            title = item.metadata.get("position") or extracted_data.get("title") or item.title
            record = JobRecord(
                schemaVersion="1.0",
                recordType="JOB",
                source=SourceMeta(name=crawler.source_name, url=canonical_url or item.url),
                content=JobContent(
                    title=title,
                    company=company,
                    date=iso_date or datetime.now(timezone.utc).isoformat(),
                    is_remote=item.metadata.get("is_remote", True),
                    role_family=extracted_data.get("role_family", "Engineering"),
                    location=item.metadata.get("location") or extracted_data.get("location") or "Remote",
                    job_url=canonical_url or item.url
                )
            )
        else:
            title = extracted_data.get("title") or item.title
            summary = extracted_data.get("summary") or item.raw_snippet or content_for_llm[:300]
            record = NewsRecord(
                schemaVersion="1.0",
                recordType="NEWS",
                source=SourceMeta(name=crawler.source_name, url=canonical_url or item.url),
                content=NewsContent(
                    title=title,
                    published_date=iso_date or datetime.now(timezone.utc).isoformat(),
                    summary=summary,
                    category=extracted_data.get("category", "Artificial Intelligence"),
                    url=canonical_url or item.url
                )
            )

        return {
            "action": "PROCESSED_FRESH",
            "hash": item_hash,
            "title": item.title,
            "record": record,
            "tier": tier_used,
            "heuristic_used": heuristic_used
        }

    async def run_cycle(self) -> Dict[str, Any]:
        """
        Executes a single complete monitoring cycle across all 10 sources.
        """
        cycle_start = datetime.now(timezone.utc)
        run_id = f"run_{cycle_start.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        logger.info("=" * 70)
        logger.info(f"STARTING CONTINUOUS MONITORING CYCLE [{run_id}]")
        logger.info(f"Timestamp: {cycle_start.isoformat()} | Sources: {len(self.crawlers)}")
        logger.info("=" * 70)

        total_candidates_found = 0
        total_already_seen = 0
        total_discarded_stale = 0
        total_passed_freshness = 0
        source_failures = 0
        fresh_records: List[Any] = []
        source_summaries: Dict[str, Any] = {}

        for crawler in self.crawlers:
            source_name = crawler.source_name
            try:
                # 1. Load seen-set and last_run for this source
                seen_hashes = self.store.get_seen_hashes(source_name)
                last_run = self.store.get_last_run(source_name)

                # 2. Fetch candidate listing
                candidates = await crawler.safe_fetch_listing()
                total_candidates_found += len(candidates)

                src_seen = 0
                src_stale = 0
                src_fresh = 0

                for candidate in candidates:
                    result = await self.process_candidate(
                        crawler=crawler,
                        item=candidate,
                        seen_hashes=seen_hashes,
                        last_run=last_run
                    )
                    if not result:
                        continue

                    action = result.get("action")
                    if action == "SKIPPED_ALREADY_SEEN":
                        src_seen += 1
                        total_already_seen += 1
                    elif action == "DISCARDED_STALE":
                        src_stale += 1
                        total_discarded_stale += 1
                    elif action == "PROCESSED_FRESH":
                        src_fresh += 1
                        total_passed_freshness += 1
                        if "record" in result:
                            fresh_records.append(result["record"])

                # Update source state upon completion
                self.store.update_source_run_completed(
                    source_name=source_name,
                    source_type=crawler.source_type,
                    run_timestamp=cycle_start,
                    status="SUCCESS"
                )

                source_summaries[source_name] = {
                    "status": "SUCCESS",
                    "candidates": len(candidates),
                    "already_seen": src_seen,
                    "discarded_stale": src_stale,
                    "passed_fresh": src_fresh
                }
                logger.info(
                    f"[{source_name}] Candidates: {len(candidates)} | "
                    f"Seen: {src_seen} | Stale: {src_stale} | Fresh: {src_fresh}"
                )

            except Exception as exc:
                source_failures += 1
                logger.error(f"Source {source_name} encounter failure: {exc}", exc_info=True)
                self.store.update_source_run_completed(
                    source_name=source_name,
                    source_type=crawler.source_type,
                    run_timestamp=cycle_start,
                    status=f"FAILED: {str(exc)[:50]}"
                )
                source_summaries[source_name] = {"status": "FAILED", "error": str(exc)}

        cycle_end = datetime.now(timezone.utc)
        elapsed_seconds = (cycle_end - cycle_start).total_seconds()
        run_status = "SUCCESS" if source_failures == 0 else ("PARTIAL" if source_failures < len(self.crawlers) else "FAILED")

        # Save run metrics to SQLite audit log
        self.store.log_crawl_run(
            run_id=run_id,
            start_time=cycle_start,
            end_time=cycle_end,
            sources_checked=len(self.crawlers),
            new_items_found=total_passed_freshness + total_discarded_stale,
            passed_freshness=total_passed_freshness,
            discarded_stale=total_discarded_stale,
            failures_count=source_failures,
            status=run_status,
            summary_data={
                "elapsed_seconds": elapsed_seconds,
                "already_seen_skipped": total_already_seen,
                "sources": source_summaries
            }
        )

        logger.info("=" * 70)
        logger.info(f"CYCLE [{run_id}] COMPLETE in {elapsed_seconds:.2f}s")
        logger.info(f"  Candidates Discovered:  {total_candidates_found}")
        logger.info(f"  Already Seen (Skipped): {total_already_seen}")
        logger.info(f"  Discarded Stale (>24h): {total_discarded_stale} (Persisted as seen)")
        logger.info(f"  Passed 24h Freshness:   {total_passed_freshness}")
        logger.info(f"  Source Failures:        {source_failures}")
        logger.info("=" * 70)

        # Sync any newly discovered fresh records to jobs.csv and news.csv
        if fresh_records:
            self.sync_to_storage(fresh_records)

        return {
            "run_id": run_id,
            "status": run_status,
            "start_time": cycle_start.isoformat(),
            "end_time": cycle_end.isoformat(),
            "elapsed_seconds": elapsed_seconds,
            "candidates_found": total_candidates_found,
            "already_seen_skipped": total_already_seen,
            "discarded_stale": total_discarded_stale,
            "passed_freshness": total_passed_freshness,
            "source_failures": source_failures,
            "fresh_records_count": len(fresh_records),
            "sources": source_summaries
        }

    def sync_to_storage(self, fresh_records: List[Any]):
        """
        Appends newly discovered fresh jobs and news items to jobs.csv and news.csv,
        deduplicating against existing entries.
        """
        import pandas as pd
        jobs_file = DATA_DIR / "jobs.csv"
        news_file = DATA_DIR / "news.csv"

        new_jobs = []
        new_news = []

        for r in fresh_records:
            if isinstance(r, JobRecord):
                new_jobs.append({
                    "schemaVersion": r.schemaVersion,
                    "recordType": r.recordType,
                    "source.name": r.source.name,
                    "job_url": r.content.job_url or r.source.url,
                    "title": r.content.title,
                    "content.company": r.content.company,
                    "content.date": r.content.date,
                    "content.is_remote": r.content.is_remote,
                    "content.role_family": r.content.role_family,
                    "location": r.content.location,
                    "collectedAt": r.collectedAt,
                })
            elif isinstance(r, NewsRecord):
                new_news.append({
                    "schemaVersion": r.schemaVersion,
                    "recordType": r.recordType,
                    "source.name": r.source.name,
                    "source.url": r.content.url or r.source.url,
                    "content.title": r.content.title,
                    "content.published_date": r.content.published_date,
                    "summary": r.content.summary,
                    "category": r.content.category,
                    "collectedAt": r.collectedAt,
                })

        if new_jobs and jobs_file.exists():
            try:
                df_existing = pd.read_csv(jobs_file)
                df_new = pd.DataFrame(new_jobs)
                combined = pd.concat([df_existing, df_new], ignore_index=True)
                combined.drop_duplicates(subset=["job_url"], keep="first", inplace=True)
                combined.to_csv(jobs_file, index=False)
                logger.info(f"Updated jobs.csv: total rows now {len(combined)} (added {len(new_jobs)} fresh).")
            except Exception as e:
                logger.error(f"Error updating jobs.csv: {e}")

        if new_news and news_file.exists():
            try:
                df_existing = pd.read_csv(news_file)
                df_new = pd.DataFrame(new_news)
                combined = pd.concat([df_existing, df_new], ignore_index=True)
                combined.drop_duplicates(subset=["source.url"], keep="first", inplace=True)
                combined.to_csv(news_file, index=False)
                logger.info(f"Updated news.csv: total rows now {len(combined)} (added {len(new_news)} fresh).")
            except Exception as e:
                logger.error(f"Error updating news.csv: {e}")

    async def close(self):

        """Closes all modular crawlers and underlying sessions."""
        for crawler in self.crawlers:
            if hasattr(crawler, "close"):
                await crawler.close()

