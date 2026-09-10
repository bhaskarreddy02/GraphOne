"""
Date Normalization Engine (Phase II: Freshness Challenge)
Parses ISO-8601, RFC 2822, relative dates ('2 hours ago'), and validates 24-hour freshness.
"""

import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)


class DateNormalizer:
    @staticmethod
    def parse_date(raw_date_str: str) -> Optional[datetime]:
        """Parses various date formats into a UTC datetime object."""
        if not raw_date_str or not isinstance(raw_date_str, str):
            return None

        clean_str = raw_date_str.strip()
        now = datetime.now(timezone.utc)

        # 1. Check relative date formats (e.g., "2 hours ago", "45 mins ago", "1 day ago")
        rel_match = re.search(
            r"(\d+)\s*(sec|second|min|minute|hour|hr|day)s?\s*ago",
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
            elif unit.startswith("hour") or unit == "hr":
                return now - timedelta(hours=amount)
            elif unit.startswith("day"):
                return now - timedelta(days=amount)

        if re.search(r"\b(just now|moments ago)\b", clean_str, re.IGNORECASE):
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
            "%B %d, %Y",
            "%b %d, %Y",
        ]

        # Handle 'Z' suffix
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
        Returns (iso_string, is_fresh_within_24h).
        If date cannot be parsed, returns (None, False).
        """
        dt = cls.parse_date(raw_date_str)
        if not dt:
            return None, False
        is_fresh = cls.is_within_24_hours(dt)
        return dt.isoformat(), is_fresh
