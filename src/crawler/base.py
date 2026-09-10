"""
Base Asynchronous Crawler with Anti-Bot Resilience and Jittered Exponential Backoff
"""

import asyncio
import logging
import random
import time
from typing import Optional, Dict, Any
import aiohttp
from bs4 import BeautifulSoup
from src.config import USER_AGENTS, REQUEST_TIMEOUT_SECONDS, MAX_RETRIES, BASE_BACKOFF_SECONDS, MAX_BACKOFF_SECONDS

logger = logging.getLogger(__name__)


class BaseCrawler:
    def __init__(self, max_concurrent: int = 15):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
            connector = aiohttp.TCPConnector(limit=50, ssl=False)
            self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self.session

    def _get_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if custom_headers:
            headers.update(custom_headers)
        return headers

    async def fetch(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        as_json: bool = False,
        retries: int = MAX_RETRIES
    ) -> Optional[Any]:
        """
        Fetches a URL with anti-bot headers and Decorrelated Full Jitter backoff for 429 / 5xx.
        """
        session = await self.get_session()
        for attempt in range(retries):
            async with self.semaphore:
                try:
                    req_headers = self._get_headers(headers)
                    async with session.get(url, headers=req_headers) as response:
                        if response.status == 200:
                            if as_json:
                                return await response.json()
                            return await response.text()

                        elif response.status == 429:
                            # 429 Too Many Requests - Exponential backoff with jitter
                            retry_after = response.headers.get("Retry-After")
                            if retry_after and retry_after.isdigit():
                                backoff = float(retry_after)
                            else:
                                # Decorrelated Jitter: uniform(0.5, 1.5) * min(max_backoff, base * 2^attempt)
                                backoff = random.uniform(0.5, 1.5) * min(
                                    MAX_BACKOFF_SECONDS, BASE_BACKOFF_SECONDS * (2 ** attempt)
                                )
                            logger.warning(
                                f"[429 Rate Limit] {url}. Backing off {backoff:.2f}s (attempt {attempt + 1}/{retries})"
                            )
                            await asyncio.sleep(backoff)

                        elif response.status in (500, 502, 503, 504):
                            backoff = random.uniform(0.5, 1.5) * min(
                                MAX_BACKOFF_SECONDS, BASE_BACKOFF_SECONDS * (2 ** attempt)
                            )
                            logger.warning(
                                f"[HTTP {response.status}] {url}. Retrying in {backoff:.2f}s (attempt {attempt + 1}/{retries})"
                            )
                            await asyncio.sleep(backoff)

                        elif response.status in (403, 401):
                            logger.warning(f"[Access Denied HTTP {response.status}] {url}")
                            return None
                        else:
                            logger.warning(f"[HTTP {response.status}] Unexpected status for {url}")
                            return None

                except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                    backoff = random.uniform(0.5, 1.5) * min(
                        MAX_BACKOFF_SECONDS, BASE_BACKOFF_SECONDS * (2 ** attempt)
                    )
                    logger.debug(f"Network error {exc} on {url}. Retrying in {backoff:.2f}s")
                    await asyncio.sleep(backoff)
                except Exception as exc:
                    logger.error(f"Unexpected error fetching {url}: {exc}")
                    return None

        logger.error(f"Exhausted {retries} retries for {url}")
        return None

    @staticmethod
    def clean_html(html_content: str) -> str:
        """Strips scripts, styles, navigation, footer and extracts dense semantic text."""
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return " ".join(text.split())

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
