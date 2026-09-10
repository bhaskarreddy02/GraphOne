"""
Research Paper Crawler (Phase I: Massive One-Time Data Acquisition)
Sources: ArXiv API, Papers with Code API, GitHub API / Repository Metrics
"""

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
from src.crawler.base import BaseCrawler
from src.schemas.paper import ResearchPaperRecord, PaperContent
from src.config import GITHUB_TOKEN

logger = logging.getLogger(__name__)


class PaperCrawler(BaseCrawler):
    def __init__(self, max_concurrent: int = 15):
        super().__init__(max_concurrent)
        self.github_cache: Dict[str, int] = {}

    async def fetch_github_stars(self, github_url: str) -> int:
        """Dynamically retrieves current GitHub star count for a repository."""
        if not github_url or "github.com" not in github_url:
            return 0

        # Clean URL
        match = re.search(r"github\.com/([^/]+)/([^/#?]+)", github_url)
        if not match:
            return 0
        owner, repo = match.group(1), match.group(2)
        repo_key = f"{owner}/{repo}".lower().rstrip(".git")

        if repo_key in self.github_cache:
            return self.github_cache[repo_key]

        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"

        try:
            data = await self.fetch(api_url, headers=headers, as_json=True)
            if isinstance(data, dict) and "stargazers_count" in data:
                stars = int(data.get("stargazers_count", 0))
                self.github_cache[repo_key] = stars
                return stars
        except Exception as e:
            logger.debug(f"GitHub API error for {repo_key}: {e}")

        # Fallback to scraping repository HTML if API is rate-limited without token
        try:
            html = await self.fetch(f"https://github.com/{owner}/{repo}")
            if html:
                star_match = re.search(r'id="repo-stars-counter-star"[^>]*title="([\d,]+)"', html)
                if not star_match:
                    star_match = re.search(r'aria-label="([\d,]+) users? starred this repository"', html)
                if star_match:
                    stars = int(star_match.group(1).replace(",", ""))
                    self.github_cache[repo_key] = stars
                    return stars
        except Exception as e:
            logger.debug(f"HTML star scrape fallback error for {repo_key}: {e}")

        return 0

    async def fetch_arxiv_batch(self, start: int, max_results: int) -> List[ResearchPaperRecord]:
        """Fetches a batch of papers from ArXiv API across AI categories."""
        url = (
            f"http://export.arxiv.org/api/query?"
            f"search_query=cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL+OR+cat:stat.ML"
            f"&start={start}&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
        )
        xml_data = await self.fetch(url)
        if not xml_data:
            return []

        records = []
        try:
            root = ET.fromstring(xml_data)
            # Atom namespace
            ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

            for entry in root.findall("atom:entry", ns):
                title_elem = entry.find("atom:title", ns)
                title = " ".join(title_elem.text.split()) if title_elem is not None and title_elem.text else ""

                authors = []
                for author in entry.findall("atom:author", ns):
                    name_elem = author.find("atom:name", ns)
                    if name_elem is not None and name_elem.text:
                        authors.append(name_elem.text.strip())

                id_elem = entry.find("atom:id", ns)
                paper_url = id_elem.text.strip() if id_elem is not None and id_elem.text else ""

                published_elem = entry.find("atom:published", ns)
                published_date = published_elem.text.strip() if published_elem is not None and published_elem.text else ""

                summary_elem = entry.find("atom:summary", ns)
                summary_text = summary_elem.text if summary_elem is not None and summary_elem.text else ""

                # Look for GitHub URLs in abstract or comments
                github_url = None
                gh_match = re.search(r"https?://github\.com/[\w\-]+/[\w\.-]+", summary_text)
                if gh_match:
                    github_url = gh_match.group(0).rstrip(".,)")

                # If no github in summary, check PapersWithCode heuristic or common repo naming
                if not github_url:
                    # Clean title for fallback search
                    arxiv_id = paper_url.split("/abs/")[-1] if "/abs/" in paper_url else ""
                    if arxiv_id:
                        pwc_candidate = f"https://github.com/paperswithcode/paper-{arxiv_id}"
                        # Check if paperswithcode has it
                        # Will be enriched later if found
                        pass

                record = ResearchPaperRecord(
                    schemaVersion="1.0",
                    recordType="RESEARCH_PAPER",
                    content=PaperContent(
                        title=title,
                        authors=authors,
                        paper_url=paper_url,
                        github_url=github_url,
                        github_stars=0,
                        published_date=published_date,
                    )
                )
                records.append(record)

        except Exception as e:
            logger.error(f"Error parsing ArXiv XML batch at start {start}: {e}")

        return records

    async def fetch_papers_with_code_batch(self, page: int, page_size: int = 50) -> List[ResearchPaperRecord]:
        """Fetches papers directly from Papers with Code API."""
        url = f"https://paperswithcode.com/api/v1/papers/?page={page}&items_per_page={page_size}"
        data = await self.fetch(url, as_json=True)
        if not data or not isinstance(data, dict):
            return []

        results = data.get("results", [])
        records = []
        for item in results:
            title = item.get("title", "").strip()
            authors = item.get("authors", [])
            paper_url = item.get("url_abs") or item.get("url_pdf") or f"https://paperswithcode.com/paper/{item.get('id', '')}"
            pub_date = item.get("published") or ""

            # Check for repo
            repo_url = None
            stars = 0
            repos = item.get("repositories", [])
            if repos and isinstance(repos, list):
                first_repo = repos[0]
                if isinstance(first_repo, dict):
                    repo_url = first_repo.get("url")
                    stars = first_repo.get("stars", 0)

            records.append(
                ResearchPaperRecord(
                    schemaVersion="1.0",
                    recordType="RESEARCH_PAPER",
                    content=PaperContent(
                        title=title,
                        authors=authors,
                        paper_url=paper_url,
                        github_url=repo_url,
                        github_stars=stars,
                        published_date=pub_date,
                    )
                )
            )
        return records

    async def scrape_target_count(self, target_count: int = 1000) -> List[ResearchPaperRecord]:
        """Scrapes at least target_count unique research papers with GitHub metrics."""
        collected: Dict[str, ResearchPaperRecord] = {}
        batch_size = 200
        start = 0

        logger.info(f"Initiating bulk research paper extraction (Target: {target_count})...")

        # 1. Fetch batches from ArXiv
        while len(collected) < target_count and start < 2000:
            logger.info(f"Fetching ArXiv batch from offset {start}...")
            batch = await self.fetch_arxiv_batch(start=start, max_results=batch_size)
            if not batch:
                break
            for paper in batch:
                key = paper.content.paper_url or paper.content.title.lower()
                if key not in collected:
                    collected[key] = paper
            start += batch_size
            await asyncio.sleep(1.0)  # Gentle spacing for ArXiv API terms of use

        # 2. If additional papers needed, fetch from Papers With Code
        if len(collected) < target_count:
            logger.info("Complementing with Papers with Code API...")
            page = 1
            while len(collected) < target_count and page <= 25:
                batch = await self.fetch_papers_with_code_batch(page=page, page_size=50)
                if not batch:
                    break
                for paper in batch:
                    key = paper.content.paper_url or paper.content.title.lower()
                    if key not in collected:
                        collected[key] = paper
                page += 1
                await asyncio.sleep(0.5)

        papers_list = list(collected.values())[:target_count]

        # 3. Enrich GitHub stars dynamically for papers with GitHub repositories
        logger.info("Enriching live GitHub star metrics...")
        tasks = []
        for paper in papers_list:
            if paper.content.github_url and paper.content.github_stars == 0:
                tasks.append(self._enrich_stars(paper))

        if tasks:
            # Run star enrichment concurrently in batches of 20
            batch_chunk_size = 20
            for i in range(0, len(tasks), batch_chunk_size):
                await asyncio.gather(*tasks[i:i + batch_chunk_size], return_exceptions=True)
                await asyncio.sleep(0.5)

        logger.info(f"Successfully collected {len(papers_list)} unique research papers.")
        return papers_list

    async def _enrich_stars(self, paper: ResearchPaperRecord):
        try:
            stars = await self.fetch_github_stars(paper.content.github_url)
            paper.content.github_stars = stars
        except Exception as e:
            logger.debug(f"Failed to enrich stars for {paper.content.github_url}: {e}")
