"""
AI News Signal Crawler (Phase II: High-Fidelity Signal Ingestion)
Monitors 5 distinct AI news sources with strict 24-hour freshness verification.
Sources:
  1. TechCrunch AI
  2. MIT Technology Review AI
  3. Artificial Intelligence News (AI News)
  4. Wired AI
  5. Ars Technica AI
  6. Hacker News AI
"""

import asyncio
import logging
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from src.crawler.base import BaseCrawler
from src.crawler.date_normalizer import DateNormalizer
from src.schemas.news import NewsRecord, NewsContent
from src.schemas.startup import SourceMeta

logger = logging.getLogger(__name__)

NEWS_SOURCES = {
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "MIT Technology Review": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
    "Artificial Intelligence News": "https://www.artificialintelligence-news.com/feed/",
    "Wired AI": "https://www.wired.com/feed/tag/ai/latest/rss",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "Hacker News AI": "https://hnrss.org/newest?q=AI+OR+LLM"
}


def find_elem(parent, *tags) -> Optional[ET.Element]:
    """Helper to safely find an XML element without relying on truthiness of empty Element."""
    for tag in tags:
        el = parent.find(tag)
        if el is not None:
            return el
    return None


class NewsCrawler(BaseCrawler):
    def __init__(self, max_concurrent: int = 10):
        super().__init__(max_concurrent)

    async def fetch_full_text(self, article_url: str) -> str:
        """Navigates to article URL and extracts clean full-text body content."""
        html = await self.fetch(article_url)
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside", "form"]):
            tag.decompose()

        article_elem = soup.find("article") or soup.find("main") or soup.find(class_=lambda c: c and "content" in c)
        if article_elem:
            paragraphs = [p.get_text().strip() for p in article_elem.find_all("p") if len(p.get_text().strip()) > 30]
            if paragraphs:
                return " ".join(paragraphs[:8])

        text = soup.get_text(separator=" ", strip=True)
        return " ".join(text.split()[:300])

    async def scrape_feed(self, source_name: str, feed_url: str, enforce_24h: bool = True) -> List[NewsRecord]:
        """Parses RSS/Atom feed and extracts articles guaranteed published within the last 24h."""
        xml_data = await self.fetch(feed_url)
        if not xml_data:
            return []

        records = []
        try:
            root = ET.fromstring(xml_data)
            items = root.findall(".//item")
            if not items:
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                items = root.findall(".//atom:entry", ns)

            for item in items:
                title_elem = find_elem(item, "title", "{http://www.w3.org/2005/Atom}title")
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""

                link_elem = find_elem(item, "link", "{http://www.w3.org/2005/Atom}link")
                if link_elem is not None:
                    article_url = link_elem.get("href") or link_elem.text or ""
                else:
                    article_url = ""

                pub_elem = find_elem(
                    item,
                    "pubDate",
                    "{http://www.w3.org/2005/Atom}published",
                    "{http://www.w3.org/2005/Atom}updated"
                )
                raw_pub_date = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else ""

                iso_date, is_fresh = DateNormalizer.normalize_to_iso(raw_pub_date)
                if enforce_24h and not is_fresh:
                    continue

                if not iso_date:
                    continue

                desc_elem = find_elem(item, "description", "{http://www.w3.org/2005/Atom}summary")
                desc_html = desc_elem.text if desc_elem is not None and desc_elem.text else ""
                summary_text = self.clean_html(desc_html)[:350]

                record = NewsRecord(
                    schemaVersion="1.0",
                    recordType="NEWS",
                    source=SourceMeta(
                        name=source_name,
                        url=article_url or feed_url
                    ),
                    content=NewsContent(
                        title=title,
                        published_date=iso_date,
                        summary=summary_text,
                        category="Artificial Intelligence",
                        url=article_url or feed_url
                    )
                )
                records.append(record)

        except Exception as exc:
            logger.error(f"Error parsing news feed {source_name}: {exc}")

        return records

    async def scrape_all_fresh_news(self) -> List[NewsRecord]:
        """Monitors all 5 news sources and retrieves all 24-hr fresh AI news articles."""
        logger.info("Initiating 24-hr fresh AI news signal crawler...")
        tasks = [
            self.scrape_feed(name, url, enforce_24h=True)
            for name, url in NEWS_SOURCES.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_news = []
        for res in results:
            if isinstance(res, list):
                all_news.extend(res)

        logger.info(f"Collected {len(all_news)} articles published within last 24h across 5 sources.")
        return all_news
