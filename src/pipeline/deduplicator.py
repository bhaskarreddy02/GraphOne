"""
Deduplication Logic for Continuous Monitoring Pipeline
Normalizes URLs to canonical form and computes deterministic SHA-256 hashes
BEFORE expensive full-text extraction or LLM calls.
"""

import hashlib
import re
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from typing import Optional


# Tracking query parameters to strip for canonical URL resolution
STRIP_QUERY_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "fbclid", "gclid", "msclkid", "mc_cid", "mc_eid", "source",
    "_hsenc", "_hsmi", "yclid", "token"
}


class ContentDeduplicator:
    @staticmethod
    def canonicalize_url(raw_url: str) -> str:
        """
        Strips tracking query parameters, fragments, trailing slashes,
        and standardizes protocol and domain for consistent hashing.
        """
        if not raw_url or not isinstance(raw_url, str):
            return ""

        url = raw_url.strip()
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return url

        # Normalize scheme to lower
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # Remove default ports
        if ":80" in netloc and scheme == "http":
            netloc = netloc.replace(":80", "")
        elif ":443" in netloc and scheme == "https":
            netloc = netloc.replace(":443", "")

        # Strip trailing slash from path unless it is root
        path = parsed.path
        if path.endswith("/") and len(path) > 1:
            path = path.rstrip("/")

        # Filter out tracking query params
        query_params = []
        if parsed.query:
            for k, v in parse_qsl(parsed.query, keep_blank_values=True):
                if k.lower() not in STRIP_QUERY_PARAMS:
                    query_params.append((k, v))
            query_params.sort()  # Sort for deterministic URL ordering

        cleaned_query = urlencode(query_params)

        # Discard fragments
        canonical = urlunparse((scheme, netloc, path, parsed.params, cleaned_query, ""))
        return canonical

    @classmethod
    def compute_item_hash(
        cls,
        source_name: str,
        url: str,
        title: str,
        rough_date: Optional[str] = None
    ) -> str:
        """
        Computes a stable deterministic identifier:
        1. Prefers canonical URL if valid.
        2. Falls back to hash(source_name + title + rough_date).
        """
        canonical_url = cls.canonicalize_url(url)
        if canonical_url and len(canonical_url) > 8:
            # Hash canonical URL
            return hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()

        # Fallback: normalize title and combine with source and date
        clean_title = re.sub(r"\s+", " ", (title or "").strip().lower())
        clean_source = (source_name or "").strip().lower()
        clean_date = (rough_date or "").strip()[:10]  # Date portion (YYYY-MM-DD)

        fallback_key = f"{clean_source}::{clean_title}::{clean_date}"
        return hashlib.sha256(fallback_key.encode("utf-8")).hexdigest()
