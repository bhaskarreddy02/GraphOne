"""
Product Crawler (Phase I: Massive One-Time Data Acquisition)
Acquires 1,000+ real AI products and tools across curated registries and directories.
Schema:
  schemaVersion: "1.0"
  recordType: "PRODUCT"
  source.name: String
  source.url: String
  content.startupName: String
  content.pricingModel: Enum (FREE, FREEMIUM, PAID, ENTERPRISE)
  collectedAt: Timestamp ISO-8601
"""

import asyncio
import logging
import re
from typing import List, Dict, Optional
from src.crawler.base import BaseCrawler
from src.schemas.product import ProductRecord, ProductContent
from src.schemas.startup import SourceMeta, PricingModel
from src.config import GITHUB_TOKEN

logger = logging.getLogger(__name__)


class ProductCrawler(BaseCrawler):
    def __init__(self, max_concurrent: int = 15):
        super().__init__(max_concurrent)

    @staticmethod
    def infer_pricing_model(text: str, is_open_source: bool = False) -> PricingModel:
        """Infers pricing tier based on keywords and source characteristics."""
        if not text:
            return PricingModel.FREE if is_open_source else PricingModel.FREEMIUM
        lower = text.lower()
        if "enterprise" in lower or "custom contract" in lower or "b2b platform" in lower:
            return PricingModel.ENTERPRISE
        if "free tier" in lower or "freemium" in lower or "credits" in lower or "trial" in lower:
            return PricingModel.FREEMIUM
        if "paid" in lower or "subscription" in lower or "$/mo" in lower or "per month" in lower:
            return PricingModel.PAID
        if is_open_source or "free" in lower or "open source" in lower or "open-source" in lower or "github" in lower:
            return PricingModel.FREE
        return PricingModel.FREEMIUM

    async def fetch_awesome_ai_tools(self) -> List[ProductRecord]:
        """Scrapes curated products from the verified awesome-ai-tools catalog."""
        url = "https://raw.githubusercontent.com/mahseema/awesome-ai-tools/main/README.md"
        content = await self.fetch(url)
        if not content:
            return []

        records = []
        matches = re.findall(r"-\s+\[([^\]]+)\]\((https?://[^\)]+)\)\s*[-:]*\s*(.*)", content)
        for name, link, desc in matches:
            name = name.strip()
            if name.lower() in ("awesome", "license", "contributing", "table of contents", "readme", "sponsor"):
                continue
            if not link.startswith("http") or "github.com/mahseema" in link:
                continue

            pricing = self.infer_pricing_model(desc, is_open_source="github.com" in link)
            startup_name = name.split(" - ")[0].split(" / ")[0].strip()

            records.append(
                ProductRecord(
                    schemaVersion="1.0",
                    recordType="PRODUCT",
                    source=SourceMeta(
                        name="Awesome AI Tools Registry",
                        url=link
                    ),
                    content=ProductContent(
                        name=name,
                        startupName=startup_name,
                        pricingModel=pricing,
                        description=desc.strip() or f"AI Product: {name}",
                        category="Artificial Intelligence Tool"
                    )
                )
            )
        return records

    async def fetch_awesome_generative_ai(self) -> List[ProductRecord]:
        """Scrapes curated generative AI applications from awesome-generative-ai."""
        url = "https://raw.githubusercontent.com/steven2358/awesome-generative-ai/main/README.md"
        content = await self.fetch(url)
        if not content:
            return []

        records = []
        matches = re.findall(r"-\s+\[([^\]]+)\]\((https?://[^\)]+)\)\s*[-:]*\s*(.*)", content)
        for name, link, desc in matches:
            name = name.strip()
            if not link.startswith("http") or any(skip in link.lower() for skip in ["arxiv.org", "nytimes.com", "wsj.com", "wired.com"]):
                continue

            pricing = self.infer_pricing_model(desc, is_open_source="github.com" in link)
            startup_name = name.split(" - ")[0].split(" / ")[0].strip()

            records.append(
                ProductRecord(
                    schemaVersion="1.0",
                    recordType="PRODUCT",
                    source=SourceMeta(
                        name="Awesome Generative AI Directory",
                        url=link
                    ),
                    content=ProductContent(
                        name=name,
                        startupName=startup_name,
                        pricingModel=pricing,
                        description=desc.strip() or f"Generative AI Tool: {name}",
                        category="Generative AI Application"
                    )
                )
            )
        return records

    async def fetch_yc_products(self, target_needed: int) -> List[ProductRecord]:
        """Extracts products built by Y Combinator AI & tech startups."""
        records = []
        pages_needed = (target_needed // 25) + 5

        for page in range(1, pages_needed + 1):
            if len(records) >= target_needed:
                break
            url = f"https://api.ycombinator.com/v0.1/companies?page={page}"
            data = await self.fetch(url, as_json=True)
            if not data or not isinstance(data, dict):
                continue
            companies = data.get("companies", [])
            for c in companies:
                name = (c.get("name") or "").strip()
                website = c.get("website") or c.get("url") or ""
                one_liner = c.get("oneLiner") or c.get("longDescription") or f"Product by {name}"
                industries = c.get("industries", [])
                pricing = self.infer_pricing_model(one_liner, is_open_source=False)

                records.append(
                    ProductRecord(
                        schemaVersion="1.0",
                        recordType="PRODUCT",
                        source=SourceMeta(
                            name="Y Combinator Product Directory",
                            url=website
                        ),
                        content=ProductContent(
                            name=f"{name} Platform",
                            startupName=name,
                            pricingModel=pricing,
                            description=one_liner,
                            category=", ".join(industries) if industries else "Enterprise Software"
                        )
                    )
                )
                if len(records) >= target_needed:
                    break

        return records

    async def scrape_target_count(self, target_count: int = 1000) -> List[ProductRecord]:
        """Collects at least target_count unique product records."""
        logger.info(f"Initiating bulk product extraction (Target: {target_count})...")
        collected: Dict[str, ProductRecord] = {}

        # 1. First ingest curated commercial & freemium AI tools
        logger.info("Ingesting from Awesome AI Tools...")
        tools1 = await self.fetch_awesome_ai_tools()
        for p in tools1:
            key = p.source.url.lower()
            if key not in collected:
                collected[key] = p
        logger.info(f"Collected {len(collected)} unique products...")

        # 2. Ingest from Awesome Generative AI
        logger.info("Ingesting from Awesome Generative AI...")
        tools2 = await self.fetch_awesome_generative_ai()
        for p in tools2:
            key = p.source.url.lower()
            if key not in collected:
                collected[key] = p
        logger.info(f"Collected {len(collected)} unique products...")

        # 3. Ingest products from YC startup companies to guarantee >= 1,000
        needed = target_count - len(collected)
        if needed > 0:
            logger.info(f"Ingesting {needed} products from YC Directory...")
            yc_products = await self.fetch_yc_products(target_needed=needed + 50)
            for p in yc_products:
                key = p.source.url.lower()
                if key not in collected:
                    collected[key] = p

        results = list(collected.values())[:target_count]
        logger.info(f"Successfully scraped {len(results)} unique product records.")
        return results
