"""
Remotive Job Board Crawler Module
"""

from typing import List
from bs4 import BeautifulSoup
from src.crawler.modules.base_module import BaseSourceCrawler, CandidateItem


class RemotiveCrawler(BaseSourceCrawler):
    source_name = "Remotive"
    source_type = "JOB"
    api_url = "https://remotive.com/api/remote-jobs?limit=50"

    async def fetch_listing(self) -> List[CandidateItem]:
        data = await self.client.fetch(self.api_url, as_json=True)
        if not data or not isinstance(data, dict):
            return []

        jobs = data.get("jobs", [])
        candidates = []
        for item in jobs:
            company = item.get("company_name", "").strip()
            title = item.get("title", "").strip()
            date_str = item.get("publication_date", "")
            url = item.get("url", "")
            tags = item.get("tags", [])
            desc_html = item.get("description", "")
            snippet = BeautifulSoup(desc_html, "html.parser").get_text(separator=" ", strip=True)[:300] if desc_html else ""

            if title and url:
                candidates.append(
                    CandidateItem(
                        source_name=self.source_name,
                        source_type=self.source_type,
                        url=url,
                        title=f"{company}: {title}" if company else title,
                        raw_date_str=date_str,
                        raw_snippet=snippet,
                        metadata={
                            "company": company,
                            "position": title,
                            "tags": tags,
                            "category": item.get("category", ""),
                            "location": item.get("candidate_required_location") or "Remote",
                            "is_remote": True,
                            "salary": item.get("salary", ""),
                            "raw_description": snippet
                        }
                    )
                )
        return candidates

    async def fetch_full_text(self, url: str) -> str:
        html = await self.client.fetch(url)
        return self.extract_clean_article_text(html, max_words=600)
