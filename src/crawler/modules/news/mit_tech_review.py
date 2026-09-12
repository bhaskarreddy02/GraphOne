"""
MIT Technology Review AI Crawler Module
"""

import xml.etree.ElementTree as ET
from typing import List
from bs4 import BeautifulSoup
from src.crawler.modules.base_module import BaseSourceCrawler, CandidateItem


class MITTechReviewCrawler(BaseSourceCrawler):
    source_name = "MIT Technology Review"
    source_type = "NEWS"
    feed_url = "https://www.technologyreview.com/topic/artificial-intelligence/feed"

    async def fetch_listing(self) -> List[CandidateItem]:
        xml_data = await self.client.fetch(self.feed_url)
        if not xml_data:
            return []

        candidates = []
        try:
            root = ET.fromstring(xml_data)
            for item in root.findall(".//item"):
                title_elem = item.find("title")
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""

                link_elem = item.find("link")
                url = link_elem.text.strip() if link_elem is not None and link_elem.text else ""

                pub_elem = item.find("pubDate")
                raw_date = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else None

                desc_elem = item.find("description")
                desc_text = ""
                if desc_elem is not None and desc_elem.text:
                    desc_text = BeautifulSoup(desc_elem.text, "html.parser").get_text(strip=True)[:300]

                if url and title:
                    candidates.append(
                        CandidateItem(
                            source_name=self.source_name,
                            source_type=self.source_type,
                            url=url,
                            title=title,
                            raw_date_str=raw_date,
                            raw_snippet=desc_text,
                            metadata={"category": "AI Research & Industry"}
                        )
                    )
        except Exception:
            pass
        return candidates

    async def fetch_full_text(self, url: str) -> str:
        html = await self.client.fetch(url)
        return self.extract_clean_article_text(html)
