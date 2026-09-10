"""
Master Ingestion Pipeline Orchestrator (Phases I - VI)
Runs concurrent data acquisition, entity resolution, signal ingestion, and 6-tab export.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any

from src.crawler.startup_crawler import StartupCrawler
from src.crawler.product_crawler import ProductCrawler
from src.crawler.paper_crawler import PaperCrawler
from src.crawler.news_crawler import NewsCrawler
from src.crawler.job_crawler import JobCrawler
from src.entity_resolution.resolver import EntityResolver
from src.exporters.excel_exporter import DataExporter
from src.config import DATA_DIR

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("PipelineRunner")


class PipelineRunner:
    def __init__(self, target_startups: int = 1000, target_products: int = 1000, target_papers: int = 1000):
        self.target_startups = target_startups
        self.target_products = target_products
        self.target_papers = target_papers
        self.resolver = EntityResolver()

    async def run(self) -> Dict[str, Any]:
        start_time = time.time()
        logger.info("=" * 70)
        logger.info("GRAPHONE / FRONTIERATLAS - INTELLIGENCE GRAPH PIPELINE STARTING")
        logger.info(f"Targeting: {self.target_startups} Startups, {self.target_products} Products, {self.target_papers} Papers")
        logger.info("=" * 70)

        startup_crawler = StartupCrawler(max_concurrent=15)
        product_crawler = ProductCrawler(max_concurrent=15)
        paper_crawler = PaperCrawler(max_concurrent=15)
        news_crawler = NewsCrawler(max_concurrent=10)
        job_crawler = JobCrawler(max_concurrent=10)

        try:
            # 1. Run Data Acquisition Concurrently
            logger.info("Launching Phase I Bulk Crawlers & Phase II Signal Monitors concurrently...")
            tasks = [
                startup_crawler.scrape_target_count(self.target_startups),
                product_crawler.scrape_target_count(self.target_products),
                paper_crawler.scrape_target_count(self.target_papers),
                news_crawler.scrape_all_fresh_news(),
                job_crawler.scrape_all_fresh_jobs(),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            startups = results[0] if isinstance(results[0], list) else []
            products = results[1] if isinstance(results[1], list) else []
            papers = results[2] if isinstance(results[2], list) else []
            news = results[3] if isinstance(results[3], list) else []
            jobs = results[4] if isinstance(results[4], list) else []

            # Log errors if any occurred in sub-tasks
            for idx, res in enumerate(results):
                if isinstance(res, Exception):
                    logger.error(f"Task {idx} failed with error: {res}")

            logger.info("-" * 70)
            logger.info(f"Raw Scraped Counts: Startups={len(startups)}, Products={len(products)}, "
                        f"Papers={len(papers)}, News={len(news)}, Jobs={len(jobs)}")
            logger.info("-" * 70)

            # 2. Phase IV: Deterministic Entity Resolution
            logger.info("Executing Phase IV: Deterministic Entity Resolution & Canonicalization...")
            # Canonicalize Startups
            for s in startups:
                canonical, conf, method = self.resolver.resolve(
                    s.content.entityName, source_context=s.source.name
                )
                s.content.entityName = canonical

            # Canonicalize Products' parent startup name
            for p in products:
                canonical, conf, method = self.resolver.resolve(
                    p.content.startupName, source_context=p.source.name
                )
                p.content.startupName = canonical

            # Canonicalize Job company names
            for j in jobs:
                canonical, conf, method = self.resolver.resolve(
                    j.content.company, source_context=j.source.name
                )
                j.content.company = canonical

            mapping_logs = self.resolver.get_audit_log()
            logger.info(f"Entity Resolution complete. Total resolution log entries: {len(mapping_logs)}")

            # 3. Phase V & VI Deliverable Export
            logger.info("Generating 6-tab Excel workbook and CSV exports...")
            excel_path = DataExporter.export_all(
                startups=startups,
                products=products,
                papers=papers,
                jobs=jobs,
                news=news,
                mapping_logs=mapping_logs,
                output_excel_path=DATA_DIR / "output_intelligence_graph.xlsx"
            )

            elapsed = time.time() - start_time
            logger.info("=" * 70)
            logger.info("GRAPHONE PIPELINE EXECUTION SUMMARY")
            logger.info(f"Total Execution Time: {elapsed:.2f} seconds")
            logger.info(f"  Tab 1 - Startups:          {len(startups)} records")
            logger.info(f"  Tab 2 - Products:          {len(products)} records")
            logger.info(f"  Tab 3 - Research Papers:   {len(papers)} records (with GitHub stars)")
            logger.info(f"  Tab 4 - Jobs (24h Fresh):  {len(jobs)} records")
            logger.info(f"  Tab 5 - News (24h Fresh):  {len(news)} records")
            logger.info(f"  Tab 6 - Entity Audit Log:  {len(mapping_logs)} entries")
            logger.info(f"Exported Workbook:           {excel_path.resolve()}")
            logger.info("=" * 70)

            return {
                "startups_count": len(startups),
                "products_count": len(products),
                "papers_count": len(papers),
                "jobs_count": len(jobs),
                "news_count": len(news),
                "mapping_logs_count": len(mapping_logs),
                "excel_path": str(excel_path),
                "elapsed_seconds": elapsed,
            }

        finally:
            await startup_crawler.close()
            await product_crawler.close()
            await paper_crawler.close()
            await news_crawler.close()
            await job_crawler.close()


async def main():
    runner = PipelineRunner(target_startups=1000, target_products=1000, target_papers=1000)
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
