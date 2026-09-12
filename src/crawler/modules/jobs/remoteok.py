"""
RemoteOK Job Board Crawler Module
"""

from typing import List
from bs4 import BeautifulSoup
from src.crawler.modules.base_module import BaseSourceCrawler, CandidateItem


class RemoteOKCrawler(BaseSourceCrawler):
    source_name = "RemoteOK"
    source_type = "JOB"
    api_url = "https://remoteok.com/api"

    async def fetch_listing(self) -> List[CandidateItem]:
        data = await self.client.fetch(self.api_url, as_json=True)
        if not data or not isinstance(data, list):
            return []

        candidates = []
        for item in data[1:]:  # Skip terms object at index 0
            if not isinstance(item, dict):
                continue

            company = item.get("company", "").strip()
            position = item.get("position", "").strip()
            date_str = item.get("date", "")
            url = item.get("url") or f"https://remoteok.com/remote-jobs/{item.get('id', '')}"
            tags = item.get("tags", [])
            desc_html = item.get("description", "")
            snippet = BeautifulSoup(desc_html, "html.parser").get_text(separator=" ", strip=True)[:300] if desc_html else ""

            if position and url:
                candidates.append(
                    CandidateItem(
                        source_name=self.source_name,
                        source_type=self.source_type,
                        url=url,
                        title=f"{company}: {position}" if company else position,
                        raw_date_str=date_str,
                        raw_snippet=snippet,
                        metadata={
                            "company": company,
                            "position": position,
                            "tags": tags,
                            "location": item.get("location") or "Remote",
                            "is_remote": True,
                            "salary_min": item.get("salary_min"),
                            "salary_max": item.get("salary_max"),
                            "raw_description": snippet
                        }
                    )
                )
        return candidates

    async def fetch_full_text(self, url: str) -> str:
        html = await self.client.fetch(url)
        return self.extract_clean_article_text(html, max_words=600)
