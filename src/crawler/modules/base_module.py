"""
Base Source Crawler Interface for Modular Pipeline
Defines CandidateItem and BaseSourceCrawler with isolated error boundaries and polite rate-limiting.
"""

import abc
import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from src.crawler.base import BaseCrawler

logger = logging.getLogger(__name__)


@dataclass
class CandidateItem:
    """Represents an item discovered during the listing phase prior to full extraction."""
    source_name: str
    source_type: str  # "NEWS" or "JOB"
    url: str
    title: str
    raw_date_str: Optional[str] = None
    raw_snippet: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    item_hash: Optional[str] = None


class BaseSourceCrawler(abc.ABC):
    """
    Independent source crawler module interface.
    Each crawler is self-contained, rates-limits itself, and never crashes other sources.
    """
    source_name: str = "Unknown"
    source_type: str = "NEWS"  # "NEWS" or "JOB"
    rate_limit_delay_range: tuple = (0.3, 1.2)  # Seconds of polite jittered delay

    def __init__(self, crawler_client: Optional[BaseCrawler] = None):
        self.client = crawler_client or BaseCrawler(max_concurrent=5)

    async def polite_delay(self):
        """Applies randomized polite backoff between individual requests."""
        delay = random.uniform(*self.rate_limit_delay_range)
        await asyncio.sleep(delay)

    @abc.abstractmethod
    async def fetch_listing(self) -> List[CandidateItem]:
        """
        Discovers current candidate URLs and brief snippets from the source listing or feed.
        Must return lightweight CandidateItems WITHOUT heavy full-page extraction.
        """
        pass

    @abc.abstractmethod
    async def fetch_full_text(self, url: str) -> str:
        """
        Fetches full-text content / details for an individual URL.
        Only called if the item passes the deduplication filter.
        """
        pass

    async def safe_fetch_listing(self) -> List[CandidateItem]:
        """
        Wrapper around fetch_listing with try/except error boundary.
        Ensures a single failing source does not terminate the pipeline run.
        """
        try:
            logger.info(f"[{self.source_name}] Fetching candidate listing...")
            await self.polite_delay()
            items = await self.fetch_listing()
            logger.info(f"[{self.source_name}] Discovered {len(items)} candidates.")
            return items
        except Exception as exc:
            logger.error(f"[{self.source_name}] Listing fetch failed: {exc}", exc_info=True)
            return []

    async def safe_fetch_full_text(self, url: str) -> str:
        """
        Wrapper around fetch_full_text with try/except error boundary.
        """
        try:
            await self.polite_delay()
            return await self.fetch_full_text(url)
        except Exception as exc:
            logger.warning(f"[{self.source_name}] Failed to fetch full text from {url}: {exc}")
            return ""

    @staticmethod
    def extract_clean_article_text(html: str, max_words: int = 400) -> str:
        """Utility for parsing main article text from HTML body."""
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside", "form"]):
            tag.decompose()

        article = soup.find("article") or soup.find("main") or soup.find(class_=lambda c: c and "content" in c)
        if article:
            paras = [p.get_text().strip() for p in article.find_all("p") if len(p.get_text().strip()) > 30]
            if paras:
                return " ".join(paras[:10])

        text = soup.get_text(separator=" ", strip=True)
        return " ".join(text.split()[:max_words])

    async def close(self):
        """Cleanly closes underlying network sessions."""
        if self.client and hasattr(self.client, "close"):
            await self.client.close()

