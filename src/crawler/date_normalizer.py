"""
Date Normalization Engine (Phase II: Freshness Challenge)
Parses structured tags (<time>, JSON-LD, meta), RFC 2822, relative dates ('2 hours ago'),
and implements the seen-set fallback heuristic when no date signal exists.
"""

import re
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Set
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class DateNormalizer:
    @staticmethod
    def extract_structured_date(html_content: str) -> Optional[str]:
        """
        Extracts publication date from structured HTML elements:
        1. <time datetime="..."> or <time pubdate="...">
        2. JSON-LD ("datePublished", "dateCreated", "dateModified")
        3. <meta property="article:published_time"> or <meta property="og:published_time">
        """
        if not html_content or not isinstance(html_content, str):
            return None

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # 1. <time datetime="...">
            time_elem = soup.find("time", attrs={"datetime": True})
            if time_elem and time_elem.get("datetime"):
                return time_elem["datetime"].strip()

            time_elem = soup.find("time", attrs={"pubdate": True})
            if time_elem and time_elem.get_text():
                return time_elem.get_text().strip()

            # 2. JSON-LD scripts
            for script in soup.find_all("script", type="application/ld+json"):
                if script.string:
                    try:
                        data = json.loads(script.string)
                        # Could be a list or single dict
                        items = data if isinstance(data, list) else [data]
                        for obj in items:
                            if isinstance(obj, dict):
                                date_str = obj.get("datePublished") or obj.get("dateCreated")
                                if date_str and isinstance(date_str, str):
                                    return date_str.strip()
                    except Exception:
                        pass

            # 3. Meta tags
            meta_properties = [
                "article:published_time",
                "og:published_time",
                "published_time",
                "parsely-pub-date",
                "sailthru.date",
                "pubdate"
            ]
            for prop in meta_properties:
                meta = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
                if meta and meta.get("content"):
                    return meta["content"].strip()

        except Exception as e:
            logger.debug(f"Error extracting structured date: {e}")

        return None

    @staticmethod
    def parse_date(raw_date_str: str) -> Optional[datetime]:
        """Parses various date formats into a UTC datetime object."""
        if not raw_date_str or not isinstance(raw_date_str, str):
            return None

        clean_str = raw_date_str.strip()
        now = datetime.now(timezone.utc)

        # 1. Check relative date formats (e.g., "2 hours ago", "45 mins ago", "1 day ago", "3d ago")
        rel_match = re.search(
            r"(\d+)\s*(sec|second|min|minute|hour|hr|h|day|d)s?\s*ago",
            clean_str,
            re.IGNORECASE
        )
        if rel_match:
            amount = int(rel_match.group(1))
            unit = rel_match.group(2).lower()
            if unit.startswith("sec"):
                return now - timedelta(seconds=amount)
            elif unit.startswith("min"):
                return now - timedelta(minutes=amount)
            elif unit.startswith("hour") or unit in ("hr", "h"):
                return now - timedelta(hours=amount)
            elif unit.startswith("day") or unit == "d":
                return now - timedelta(days=amount)

        if re.search(r"\b(just now|moments ago|seconds ago)\b", clean_str, re.IGNORECASE):
            return now

        if re.search(r"\byesterday\b", clean_str, re.IGNORECASE):
            return now - timedelta(days=1)

        # 2. Try RFC 2822 / email date format (standard RSS pubDate)
        try:
            dt = parsedate_to_datetime(clean_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except Exception:
            pass

        # 3. Try ISO-8601 and common datetime strings
        iso_formats = [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d %b %Y %H:%M:%S %Z",
            "%d %b %Y %H:%M:%S",
            "%B %d, %Y",
            "%b %d, %Y",
        ]

        normalized_str = clean_str.replace("Z", "+00:00")

        for fmt in iso_formats:
            try:
                dt = datetime.strptime(normalized_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                return dt
            except ValueError:
                continue

        # 4. Extract YYYY-MM-DD or regex timestamp pattern
        date_pattern = re.search(r"(\d{4})-(\d{2})-(\d{2})", clean_str)
        if date_pattern:
            try:
                y, m, d = int(date_pattern.group(1)), int(date_pattern.group(2)), int(date_pattern.group(3))
                return datetime(y, m, d, 0, 0, 0, tzinfo=timezone.utc)
            except ValueError:
                pass

        return None

    @classmethod
    def is_within_24_hours(cls, date_obj: Optional[datetime]) -> bool:
        """Verifies if the publication datetime is strictly within the last 24 hours."""
        if not date_obj:
            return False
        now = datetime.now(timezone.utc)
        # Allow slight future drift (up to 1 hour for timezone skew) and max 24 hours in the past
        diff = now - date_obj
        return timedelta(hours=-1) <= diff <= timedelta(hours=24)

    @classmethod
    def normalize_to_iso(cls, raw_date_str: str) -> Tuple[Optional[str], bool]:
        """
        Standard parser: returns (iso_string, is_fresh_within_24h).
        If date cannot be parsed, returns (None, False).
        """
        dt = cls.parse_date(raw_date_str)
        if not dt:
            return None, False
        is_fresh = cls.is_within_24_hours(dt)
        return dt.isoformat(), is_fresh

    @classmethod
    def resolve_date_with_fallback(
        cls,
        raw_date_str: Optional[str] = None,
        html_content: Optional[str] = None,
        item_hash: Optional[str] = None,
        last_run_timestamp: Optional[datetime] = None,
        seen_hashes: Optional[Set[str]] = None
    ) -> Tuple[Optional[datetime], bool, bool]:
        """
        Multi-tier date resolver implementing:
        1. Explicit raw_date_str parsing (RSS pubDate, API date)
        2. Structured HTML / JSON-LD / meta extraction if html_content provided
        3. Fallback heuristic: If no date signal exists at all, check if item's dedup-hash
           was NOT in the seen-set as of last_run_timestamp. If so, treat as new-since-last-run
           and assign now as freshness proxy.

        Returns: (resolved_datetime, is_fresh_24h, heuristic_used)
        """
        now = datetime.now(timezone.utc)

        # 1. Try raw date string
        if raw_date_str:
            dt = cls.parse_date(raw_date_str)
            if dt:
                return dt, cls.is_within_24_hours(dt), False

        # 2. Try structured HTML extraction
        if html_content:
            structured_str = cls.extract_structured_date(html_content)
            if structured_str:
                dt = cls.parse_date(structured_str)
                if dt:
                    return dt, cls.is_within_24_hours(dt), False

        # 3. Fallback Heuristic
        # "if this item's dedup-hash was NOT in the seen-set as of last_run_timestamp,
        # treat it as new-since-last-run — this is your fallback freshness proxy when the source gives you nothing"
        if item_hash and seen_hashes is not None:
            if item_hash not in seen_hashes:
                logger.info(f"Applying fallback freshness heuristic for unseen item {item_hash[:10]}...")
                return now, True, True

        return None, False, False

