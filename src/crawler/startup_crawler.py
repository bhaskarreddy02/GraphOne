"""
Startup Crawler (Phase I: Massive One-Time Data Acquisition)
Sources: Y Combinator Public API & Curated Tech Directories
Schema:
  schemaVersion: "1.0"
  recordType: "STARTUP"
  source.name: String
  source.url: String
  content.entityName: String
  content.data.employeeCount: Integer
  collectedAt: Timestamp ISO-8601
"""

import asyncio
import logging
from typing import List, Dict, Any
from src.crawler.base import BaseCrawler
from src.schemas.startup import StartupRecord, StartupContent, StartupContentData, SourceMeta

logger = logging.getLogger(__name__)


class StartupCrawler(BaseCrawler):
    def __init__(self, max_concurrent: int = 15):
        super().__init__(max_concurrent)

    async def fetch_page(self, page_num: int) -> List[StartupRecord]:
        """Fetches a single page of startup records from YC directory API."""
        url = f"https://api.ycombinator.com/v0.1/companies?page={page_num}"
        data = await self.fetch(url, as_json=True)
        if not data or not isinstance(data, dict):
            return []

        companies = data.get("companies", [])
        records = []
        for comp in companies:
            name = (comp.get("name") or "").strip()
            if not name:
                continue

            website = comp.get("website") or comp.get("url") or f"https://www.ycombinator.com/companies/{comp.get('slug', '')}"
            yc_url = comp.get("url") or website
            team_size = comp.get("teamSize")
            employee_count = int(team_size) if team_size is not None and str(team_size).isdigit() else None
            industry = ", ".join(comp.get("industries", [])) or ", ".join(comp.get("tags", []))
            description = comp.get("oneLiner") or comp.get("longDescription")

            record = StartupRecord(
                schemaVersion="1.0",
                recordType="STARTUP",
                source=SourceMeta(
                    name="Y Combinator",
                    url=yc_url
                ),
                content=StartupContent(
                    entityName=name,
                    data=StartupContentData(
                        employeeCount=employee_count,
                        industry=industry,
                        description=description
                    )
                )
            )
            records.append(record)

        return records

    async def scrape_target_count(self, target_count: int = 1000) -> List[StartupRecord]:
        """Concurrently scrapes at least target_count unique startup records."""
        logger.info(f"Initiating bulk startup extraction (Target: {target_count})...")
        collected: Dict[str, StartupRecord] = {}
        pages_needed = (target_count // 25) + 5
        batch_size = 10

        for batch_start in range(1, pages_needed + 1, batch_size):
            tasks = [
                self.fetch_page(p)
                for p in range(batch_start, min(batch_start + batch_size, pages_needed + 1))
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, list):
                    for record in res:
                        key = record.content.entityName.lower()
                        if key not in collected:
                            collected[key] = record

            logger.info(f"Collected {len(collected)}/{target_count} unique startups...")
            if len(collected) >= target_count:
                break
            await asyncio.sleep(0.5)

        records_list = list(collected.values())[:target_count]
        logger.info(f"Successfully scraped {len(records_list)} unique startup records.")
        return records_list
