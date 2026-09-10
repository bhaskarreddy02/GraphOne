"""
AI Job Signal Crawler (Phase II: High-Fidelity Signal Ingestion)
Monitors 5 distinct AI/tech job boards with strict 24-hour freshness verification.
Sources:
  1. RemoteOK (AI & Engineering)
  2. Remotive (Software & AI)
  3. WeWorkRemotely (Programming / AI)
  4. Jobicy (Tech Job Feed)
  5. Hacker News Jobs (Real-time hiring signals)
"""

import asyncio
import logging
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from datetime import datetime, timezone
from src.crawler.base import BaseCrawler
from src.crawler.date_normalizer import DateNormalizer
from src.schemas.job import JobRecord, JobContent
from src.schemas.startup import SourceMeta

logger = logging.getLogger(__name__)


class JobCrawler(BaseCrawler):
    def __init__(self, max_concurrent: int = 10):
        super().__init__(max_concurrent)

    @staticmethod
    def infer_role_family(title: str, tags: List[str]) -> str:
        """Categorizes job title into functional role families."""
        combined = (title + " " + " ".join(tags)).lower()
        if any(w in combined for w in ["ai", "machine learning", "deep learning", "nlp", "llm", "cv", "vision", "data science"]):
            return "AI / Machine Learning"
        if any(w in combined for w in ["engineer", "developer", "backend", "frontend", "fullstack", "software"]):
            return "Engineering"
        if any(w in combined for w in ["product", "pm"]):
            return "Product Management"
        if any(w in combined for w in ["design", "ui", "ux"]):
            return "Design"
        return "Engineering"

    async def fetch_remoteok(self, enforce_24h: bool = True) -> List[JobRecord]:
        """Fetches jobs from RemoteOK API."""
        url = "https://remoteok.com/api"
        data = await self.fetch(url, as_json=True)
        if not data or not isinstance(data, list):
            return []

        records = []
        for item in data[1:]:  # First item is legal info
            if not isinstance(item, dict):
                continue

            company = item.get("company", "").strip()
            title = item.get("position", "").strip()
            date_str = item.get("date", "")
            job_url = item.get("url") or f"https://remoteok.com/remote-jobs/{item.get('id', '')}"
            tags = item.get("tags", [])

            iso_date, is_fresh = DateNormalizer.normalize_to_iso(date_str)
            if enforce_24h and not is_fresh:
                continue
            if not iso_date or not company:
                continue

            records.append(
                JobRecord(
                    schemaVersion="1.0",
                    recordType="JOB",
                    source=SourceMeta(
                        name="RemoteOK",
                        url=job_url
                    ),
                    content=JobContent(
                        title=title,
                        company=company,
                        date=iso_date,
                        is_remote=True,
                        role_family=self.infer_role_family(title, tags),
                        location=item.get("location") or "Remote",
                        job_url=job_url
                    )
                )
            )
        return records

    async def fetch_remotive(self, enforce_24h: bool = True) -> List[JobRecord]:
        """Fetches jobs from Remotive API."""
        url = "https://remotive.com/api/remote-jobs?limit=50"
        data = await self.fetch(url, as_json=True)
        if not data or not isinstance(data, dict):
            return []

        jobs = data.get("jobs", [])
        records = []
        for item in jobs:
            company = item.get("company_name", "").strip()
            title = item.get("title", "").strip()
            date_str = item.get("publication_date", "")
            job_url = item.get("url", "")
            tags = item.get("tags", [])
            category = item.get("category", "")

            iso_date, is_fresh = DateNormalizer.normalize_to_iso(date_str)
            if enforce_24h and not is_fresh:
                continue
            if not iso_date or not company:
                continue

            records.append(
                JobRecord(
                    schemaVersion="1.0",
                    recordType="JOB",
                    source=SourceMeta(
                        name="Remotive",
                        url=job_url
                    ),
                    content=JobContent(
                        title=title,
                        company=company,
                        date=iso_date,
                        is_remote=True,
                        role_family=self.infer_role_family(title + " " + category, tags),
                        location=item.get("candidate_required_location") or "Remote",
                        job_url=job_url
                    )
                )
            )
        return records

    async def fetch_rss_jobs(self, source_name: str, feed_url: str, enforce_24h: bool = True) -> List[JobRecord]:
        """Generic RSS job parser for WeWorkRemotely, Jobicy, and HNRSS."""
        xml_data = await self.fetch(feed_url)
        if not xml_data:
            return []

        records = []
        try:
            root = ET.fromstring(xml_data)
            items = root.findall(".//item")
            for item in items:
                title_elem = item.find("title")
                raw_title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""

                link_elem = item.find("link")
                job_url = link_elem.text.strip() if link_elem is not None and link_elem.text else ""

                pub_elem = item.find("pubDate")
                raw_pub_date = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else ""

                iso_date, is_fresh = DateNormalizer.normalize_to_iso(raw_pub_date)
                if enforce_24h and not is_fresh:
                    continue
                if not iso_date or not raw_title:
                    continue

                # Parse Company from Title (e.g. "Company: Position" or "Position at Company")
                company = "Tech Company"
                title = raw_title
                if ":" in raw_title:
                    parts = raw_title.split(":", 1)
                    company = parts[0].strip()
                    title = parts[1].strip()
                elif " at " in raw_title:
                    parts = raw_title.split(" at ", 1)
                    title = parts[0].strip()
                    company = parts[1].strip()
                elif " is hiring " in raw_title:
                    parts = raw_title.split(" is hiring ", 1)
                    company = parts[0].strip()
                    title = parts[1].strip()

                records.append(
                    JobRecord(
                        schemaVersion="1.0",
                        recordType="JOB",
                        source=SourceMeta(
                            name=source_name,
                            url=job_url
                        ),
                        content=JobContent(
                            title=title,
                            company=company,
                            date=iso_date,
                            is_remote=True,
                            role_family=self.infer_role_family(title, []),
                            job_url=job_url
                        )
                    )
                )
        except Exception as e:
            logger.error(f"Error parsing job feed {source_name}: {e}")

        return records

    async def scrape_all_fresh_jobs(self) -> List[JobRecord]:
        """Gathers all jobs from the 5 job boards published strictly within the last 24 hours."""
        logger.info("Initiating 24-hr fresh AI job crawler across 5 job boards...")
        tasks = [
            self.fetch_remoteok(enforce_24h=True),
            self.fetch_remotive(enforce_24h=True),
            self.fetch_rss_jobs("WeWorkRemotely", "https://weworkremotely.com/categories/remote-programming-jobs.rss", enforce_24h=True),
            self.fetch_rss_jobs("Jobicy", "https://jobicy.com/?feed=job_feed", enforce_24h=True),
            self.fetch_rss_jobs("Hacker News Jobs", "https://hnrss.org/jobs", enforce_24h=True),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_jobs = []
        for res in results:
            if isinstance(res, list):
                all_jobs.extend(res)

        logger.info(f"Collected {len(all_jobs)} jobs published within last 24h across 5 sources.")
        return all_jobs
