"""
Jobicy Job Board Crawler Module
"""

import xml.etree.ElementTree as ET
from typing import List
from bs4 import BeautifulSoup
from src.crawler.modules.base_module import BaseSourceCrawler, CandidateItem


class JobicyCrawler(BaseSourceCrawler):
    source_name = "Jobicy"
    source_type = "JOB"
    feed_url = "https://jobicy.com/?feed=job_feed"

    async def fetch_listing(self) -> List[CandidateItem]:
        xml_data = await self.client.fetch(self.feed_url)
        if not xml_data:
            return []

        candidates = []
        try:
            root = ET.fromstring(xml_data)
            for item in root.findall(".//item"):
                title_elem = item.find("title")
                raw_title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""

                link_elem = item.find("link")
                url = link_elem.text.strip() if link_elem is not None and link_elem.text else ""

                pub_elem = item.find("pubDate")
                raw_date = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else None

                desc_elem = item.find("description")
                snippet = ""
                if desc_elem is not None and desc_elem.text:
                    snippet = BeautifulSoup(desc_elem.text, "html.parser").get_text(separator=" ", strip=True)[:300]

                company = ""
                position = raw_title
                if " at " in raw_title:
                    parts = raw_title.split(" at ", 1)
                    position = parts[0].strip()
                    company = parts[1].strip()
                elif ":" in raw_title:
                    parts = raw_title.split(":", 1)
                    company = parts[0].strip()
                    position = parts[1].strip()

                if url and raw_title:
                    candidates.append(
                        CandidateItem(
                            source_name=self.source_name,
                            source_type=self.source_type,
                            url=url,
                            title=raw_title,
                            raw_date_str=raw_date,
                            raw_snippet=snippet,
                            metadata={
                                "company": company,
                                "position": position,
                                "location": "Remote",
                                "is_remote": True,
                                "raw_description": snippet
                            }
                        )
                    )
        except Exception:
            pass
        return candidates

    async def fetch_full_text(self, url: str) -> str:
        html = await self.client.fetch(url)
        return self.extract_clean_article_text(html, max_words=600)
